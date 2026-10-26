"""Read-only administrative projections over the existing lifecycle/domain models."""
import re
from datetime import datetime, time, timedelta
from pathlib import PurePosixPath

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models import OuterRef, Subquery, CharField
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, serializers, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import operational, profile_for, scoped
from .models import LifecycleEvent
from .services.lifecycle import RESOURCE_MODELS, model_for

TARGET_NAMES = {name.lower(): name for name in RESOURCE_MODELS.values()}

ARCHIVE_TYPES = ('pacientes', 'casos', 'analisis', 'muestras', 'muestras-sangre',
                 'acquisition-series', 'acquisition-profiles', 'calibrations')


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return operational(request.user) and (request.user.is_superuser or profile_for(request.user).role == 'ADMIN')


class AdminPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def integer(params, key):
    if not params.get(key):
        return None
    try:
        value = int(params[key])
        if value > 0:
            return value
    except (ValueError, TypeError):
        pass
    raise ValidationError({key: 'Use un ID entero positivo.'})


def tenant(request):
    selected = integer(request.query_params, 'institution')
    if not request.user.is_superuser:
        own = request.user.sicam_profile.institution_id
        if selected and selected != own:
            raise NotFound()
        return own
    return selected


def date_filter(queryset, params, field):
    dates = {}
    for key in ('date_from', 'date_to'):
        if params.get(key):
            try:
                dates[key] = parse_date(params[key])
            except ValueError:
                dates[key] = None
            if not dates[key] or dates[key].year >= 9999:
                raise ValidationError({key: 'Use YYYY-MM-DD.'})
    if len(dates) == 2 and dates['date_from'] > dates['date_to']:
        raise ValidationError('El inicio no puede ser posterior al final.')
    if 'date_from' in dates:
        queryset = queryset.filter(**{field+'__gte': timezone.make_aware(datetime.combine(dates['date_from'], time.min))})
    if 'date_to' in dates:
        queryset = queryset.filter(**{field+'__lt': timezone.make_aware(datetime.combine(dates['date_to']+timedelta(days=1), time.min))})
    return queryset


def event_target(event):
    # No fallback to __str__: patient names must never become audit descriptions.
    if event.target_type not in TARGET_NAMES:
        return None
    model = get_user_model() if event.target_type == 'user' else apps.get_model('api', event.target_type)
    return model.objects.filter(pk=event.target_id).first() if str(event.target_id).isdigit() else None


def safe_metadata(metadata):
    """Explicit projection, never return arbitrary stored payloads or file paths."""
    if not isinstance(metadata, dict):
        return {'dependencies': {}, 'media_cleanup': []}
    dependencies = metadata.get('dependencies')
    dependencies = dependencies if isinstance(dependencies, dict) else {}
    result = {'dependencies': {k: v for k, v in dependencies.items()
                              if k in {m.__name__ for m in apps.get_app_config('api').get_models()} | {'PendingSegmentationExecution'}
                              and isinstance(v, int) and not isinstance(v, bool) and v >= 0}}
    files = []
    cleanup = metadata.get('media_cleanup')
    for item in cleanup if isinstance(cleanup, list) else []:
        if not isinstance(item, dict):
            continue
        entry = {}
        if item.get('status') in ('PENDING_DELETE', 'DELETED', 'SHARED_FILE_RETAINED', 'MEDIA_DELETE_FAILED', 'MISSING_BEFORE_DELETE'):
            entry['status'] = item['status']
        if isinstance(item.get('missing_before_delete'), bool):
            entry['missing_before_delete'] = item['missing_before_delete']
        if isinstance(item.get('filename'), str):
            entry['filename'] = PurePosixPath(item['filename']).name
        if re.fullmatch('[a-f0-9]{64}', str(item.get('sha256', ''))):
            entry['sha256'] = item['sha256']
        files.append(entry)
    result['media_cleanup'] = files
    return result


def test_evidence(obj):
    if obj is None:
        return False
    return any(str(getattr(obj, field, '')).startswith('TEST_LIFECYCLE_')
               for field in ('nombre', 'titulo', 'observaciones', 'name', 'label'))


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LifecycleEvent
        fields = ('id', 'action', 'target_type', 'target_id', 'reason', 'created_at')
        read_only_fields = fields

    def to_representation(self, obj):
        data = super().to_representation(obj)
        actor = obj.actor
        profile = profile_for(actor)
        target = event_target(obj)
        metadata = safe_metadata(obj.metadata)
        is_test = test_evidence(target) or any(f.get('filename', '').startswith('TEST_LIFECYCLE_') for f in metadata['media_cleanup'])
        data.update(actor={'id': actor.pk, 'username': actor.username, 'current_role': profile.role if profile else ('SUPERUSER' if actor.is_superuser else None)} if actor else None,
                    institution={'id': obj.institution_id, 'code': obj.institution.code} if obj.institution else None,
                    description=f'{obj.target_type} #{obj.target_id}',
                    target_deleted=obj.action == 'HARD_DELETE' or (target is None and obj.target_type in TARGET_NAMES),
                    is_test=is_test, metadata=metadata)
        return data


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AdminPermission]
    serializer_class = EventSerializer
    pagination_class = AdminPagination

    def get_queryset(self):
        qs = LifecycleEvent.objects.select_related('actor__sicam_profile', 'institution').order_by('-created_at', '-pk')
        institution = tenant(self.request)
        if institution:
            qs = qs.filter(institution_id=institution)
        params = self.request.query_params
        if integer(params, 'actor'):
            qs = qs.filter(actor_id=integer(params, 'actor'))
        for key, values in [('action', {v for v, _ in LifecycleEvent._meta.get_field('action').choices}),
                            ('target_type', set(TARGET_NAMES))]:
            if params.get(key):
                if params[key] not in values:
                    raise ValidationError({key: 'Filtro no válido.'})
                qs = qs.filter(**{key: params[key]})
        return date_filter(qs, params, 'created_at')


class AuditOptionsView(APIView):
    permission_classes = [AdminPermission]

    def get(self, request):
        institution = tenant(request)
        qs = LifecycleEvent.objects.all()
        if institution:
            qs = qs.filter(institution_id=institution)
        users = scoped(get_user_model().objects.all(), request.user)
        if institution:
            users = users.filter(sicam_profile__institution_id=institution)
        return Response({'actions': sorted(qs.order_by().values_list('action', flat=True).distinct()),
                         'target_types': sorted(qs.order_by().values_list('target_type', flat=True).distinct()),
                         'actors': list(users.order_by('pk').values('id', 'username')),
                         'archive_types': ARCHIVE_TYPES})


class ArchivedView(APIView):
    permission_classes = [AdminPermission]

    def get(self, request):
        kind = request.query_params.get('type', 'pacientes')
        if kind not in ARCHIVE_TYPES:
            raise ValidationError({'type': 'Tipo no válido.'})
        model = model_for(kind)
        qs = scoped(model.objects.all(), request.user)
        institution = tenant(request)
        if institution:
            from .access import PATHS
            qs = qs.filter(**{PATHS[model._meta.model_name]: institution})
        retired = kind == 'calibrations'
        if retired:
            retirement = LifecycleEvent.objects.filter(action='RETIRE', target_type='calibration',
                target_id=Cast(OuterRef('pk'), CharField())).order_by('-created_at', '-pk')
            qs = qs.annotate(retired_at=Subquery(retirement.values('created_at')[:1]),
                             retired_by=Subquery(retirement.values('actor_id')[:1]))
        field = 'retired_at' if retired else 'archived_at'
        qs = qs.filter(status='RETIRED') if retired else qs.filter(archived_at__isnull=False)
        actor = integer(request.query_params, 'archived_by')
        if actor:
            qs = qs.filter(**{'retired_by' if retired else 'archived_by_id': actor})
        search = request.query_params.get('search', '').strip()
        if search:
            # Safe search is technical ID/type only; never patient names or identifiers.
            if search.isdigit():
                qs = qs.filter(pk=int(search))
            elif search.lower() not in (kind.lower(), model._meta.model_name):
                qs = qs.none()
        qs = date_filter(qs, request.query_params, field).order_by('-'+field, '-pk')
        pager = AdminPagination()
        page = pager.paginate_queryset(qs, request)
        data = [{'id': obj.pk, 'resource': kind, 'description': f'{obj._meta.model_name} #{obj.pk}',
                 'institution_id': self.institution(obj), 'archived_at': getattr(obj, field),
                 'archived_by': getattr(obj, 'retired_by' if retired else 'archived_by_id'),
                 'status': 'RETIRED' if retired else 'ARCHIVED', 'is_test': test_evidence(obj)} for obj in page]
        return pager.get_paginated_response(data)

    @staticmethod
    def institution(obj):
        from .services.lifecycle import institution_id
        return institution_id(obj)


class OperationalHealthView(APIView):
    permission_classes = [AdminPermission]

    def get(self, request):
        from .services.operational_health import diagnose
        return Response(diagnose(request.user, institution=tenant(request), check_files=request.query_params.get('check_files') == 'true'))
