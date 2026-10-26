"""Explicit read-only diagnostics. Never repairs ownership, geometry or storage."""
import os
from pathlib import Path
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, models
from django.core.exceptions import ObjectDoesNotExist
from django.db.migrations.executor import MigrationExecutor
from api.access import scoped, PATHS, profile_for
from api.models import (Paciente, AcquisitionProfile, Calibration, AcquisitionSeries,
                        SicamUserProfile, LifecycleEvent)
from api.services.lifecycle import active_queryset, is_operationally_active


def diagnose(user, *, institution=None, check_files=False):
    results = []

    def add(code, status='OK', count=0, issues=None, **extra):
        results.append(dict(code=code, status=status, count=count, issues=(issues or [])[:100], **extra))

    def visible(model):
        qs = scoped(model.objects.all(), user)
        if institution and model._meta.model_name in PATHS:
            qs = qs.filter(**{PATHS[model._meta.model_name]: institution})
        return qs

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        add('DATABASE_CONNECTIVITY')
        executor = MigrationExecutor(connection)
        pending = [migration.name for migration, _ in executor.migration_plan(executor.loader.graph.leaf_nodes())]
        add('MIGRATIONS', 'WARNING' if pending else 'OK', len(pending), migrations=pending)
    except Exception:
        add('DATABASE_CONNECTIVITY', 'ERROR')
        return {'status': 'ERROR', 'checks': results}

    accessible = Path(settings.MEDIA_ROOT).is_dir() and os.access(settings.MEDIA_ROOT, os.R_OK | os.X_OK)
    add('MEDIA_ROOT_ACCESSIBLE', 'OK' if accessible else 'ERROR')
    legacy = []
    # NULL ownership cannot be attributed to a tenant: only the platform may enumerate it.
    if user.is_superuser and institution is None:
        for model in apps.get_app_config('api').get_models():
            ownership = PATHS.get(model._meta.model_name)
            if not ownership or model._meta.model_name in ('institution', 'sicamuserprofile'):
                continue
            legacy.extend({'resource_type': model._meta.model_name, 'id': pk} for pk in
                          active_queryset(model.objects.filter(**{ownership+'__isnull': True})).values_list('pk', flat=True))
        add('LEGACY_INSTITUTION_OWNERSHIP', 'WARNING' if legacy else 'OK', len(legacy), legacy)
    else:
        add('LEGACY_INSTITUTION_OWNERSHIP', 'PLATFORM_ONLY')

    incomplete = []
    if user.is_superuser and institution is None:
        incomplete.extend({'resource_type': 'user', 'id': pk} for pk in get_user_model().objects.filter(
            is_active=True, is_superuser=False, sicam_profile__isnull=True).values_list('pk', flat=True))
    for p in visible(SicamUserProfile).select_related('user', 'institution'):
        if p.role not in ('ADMIN', 'OPERATOR', 'REVIEWER'):
            incomplete.append({'resource_type': 'user', 'id': p.user_id})
    add('USER_PROFILES', 'WARNING' if incomplete else 'OK', len(incomplete), incomplete)

    authors, lifecycle, missing, dangling, calibration, series = [], [], [], [], [], []
    for model in apps.get_app_config('api').get_models():
        # Unmapped models are intentionally invisible through scoped().
        qs = visible(model)
        file_fields = [f for f in model._meta.fields if isinstance(f, models.FileField)]
        for obj in qs.iterator():
            if hasattr(obj, 'created_by_id') and obj.created_by_id:
                try:
                    author = obj.created_by
                except ObjectDoesNotExist:
                    author = None
                p = profile_for(author)
                path = PATHS.get(model._meta.model_name)
                own = model.objects.filter(pk=obj.pk).values_list(path, flat=True).first() if path else None
                if not path and model._meta.model_name in ('revisionsegmentacion', 'resultadocaracterizacion'):
                    # Derived authorship follows the same source as the tenant resolver.
                    source = model.objects.filter(pk=obj.pk)
                    own = source.values_list('resultado_segmentacion__muestra__analisis__id_paciente_fk__institution_id', flat=True).first()
                    if own is None:
                        own = source.values_list('resultado_segmentacion__muestra_sangre__analisis__id_paciente_fk__institution_id', flat=True).first()
                if own and author and not author.is_superuser and (not p or p.institution_id != own):
                    authors.append({'resource_type': model._meta.model_name, 'id': obj.pk})
            if hasattr(obj, 'archived_at') and obj.archived_at and not obj.archive_reason.strip():
                lifecycle.append({'resource_type': model._meta.model_name, 'id': obj.pk, 'issue': 'ARCHIVE_REASON_MISSING'})
            # Identify broken domain FK references without loading or logging their contents.
            for field in model._meta.fields:
                if isinstance(field, models.ForeignKey) and getattr(obj, field.attname) is not None:
                    if not field.remote_field.model.objects.filter(pk=getattr(obj, field.attname)).exists():
                        dangling.append({'resource_type': model._meta.model_name, 'id': obj.pk, 'field': field.name})
            if check_files:
                for field in file_fields:
                    value = getattr(obj, field.name)
                    if value:
                        try:
                            exists = value.storage.exists(value.name)
                        except Exception:
                            exists = False
                        if not exists:
                            missing.append({'resource_type': model._meta.model_name, 'id': obj.pk, 'field': field.name})
    for c in visible(Calibration).select_related('acquisition_profile'):
        p = c.acquisition_profile
        if (c.source_width_px, c.source_height_px) != (p.image_width_px, p.image_height_px) or c.scale_x_um_per_px <= 0 or c.scale_y_um_per_px <= 0:
            calibration.append({'resource_type': 'calibration', 'id': c.pk})
    for s in visible(AcquisitionSeries).select_related('patient', 'acquisition_profile', 'calibration'):
        if s.patient.institution_id != s.acquisition_profile.institution_id or (s.calibration and s.calibration.acquisition_profile_id != s.acquisition_profile_id):
            series.append({'resource_type': 'acquisitionseries', 'id': s.pk})
    event_qs = LifecycleEvent.objects.all()
    if not user.is_superuser or institution:
        event_qs = event_qs.filter(institution_id=institution or user.sicam_profile.institution_id)
    for event in event_qs.iterator():
        cleanup = event.metadata.get('media_cleanup', []) if isinstance(event.metadata, dict) else []
        if isinstance(cleanup, list) and any(isinstance(item, dict) and item.get('status') in ('PENDING_DELETE', 'MEDIA_DELETE_FAILED') for item in cleanup):
            lifecycle.append({'resource_type': 'lifecycleevent', 'id': event.pk, 'issue': 'MEDIA_CLEANUP_REQUIRES_REVIEW'})
    for code, items in [('AUTHORSHIP_CONSISTENCY', authors), ('LIFECYCLE_CONSISTENCY', lifecycle),
                        ('ORPHAN_REFERENCES', dangling), ('CALIBRATION_PROFILE_CONSISTENCY', calibration),
                        ('SERIES_PATIENT_INSTITUTION_CONSISTENCY', series)]:
        add(code, 'WARNING' if items else 'OK', len(items), items)
    add('MEDIA_REFERENCES', 'WARNING' if missing else ('OK' if check_files else 'NOT_CHECKED'), len(missing), missing)
    add('ORPHAN_MEDIA_CLEANUP', 'PENDING_ADMIN_ACTION', scanned=False)
    add('PRODUCTION_MEDIA_ACCESS_CONTROL', 'DEPLOYMENT_ACTION_REQUIRED')
    # These checks do not certify the installed proxy, HTTPS or dependency support.
    return {'status': 'ERROR' if any(c['status'] == 'ERROR' for c in results) else
            'WARNING' if any(c['status'] in ('WARNING', 'DEPLOYMENT_ACTION_REQUIRED') for c in results) else 'OK',
            'checks': results, 'scope': 'GLOBAL' if user.is_superuser and institution is None else 'INSTITUTION',
            'files_checked': check_files, 'issue_limit': 100}
