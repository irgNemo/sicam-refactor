"""Lifecycle policy and mutations. No scientific algorithm or global manager filtering."""
import hashlib
from functools import partial
from pathlib import PurePosixPath

from django.apps import apps
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError, NotFound

RESOURCE_MODELS = {
    'pacientes': 'Paciente', 'casos': 'Caso', 'analisis': 'AnalisisPred',
    'muestras': 'MuestraSaliva', 'muestras-sangre': 'MuestraSangre',
    'acquisition-series': 'AcquisitionSeries', 'acquisition-profiles': 'AcquisitionProfile',
    'calibrations': 'Calibration', 'calibration-references': 'CalibrationReference',
    'resultados-segmentacion': 'ResultadoSegmentacion', 'revisiones-segmentacion': 'RevisionSegmentacion',
    'characterizations': 'ResultadoCaracterizacion', 'institutions': 'Institution', 'users': 'User',
}
# A profile/series archive prevents *new bindings*, not historical scientific reads.
PARENTS = {
    'caso': ('paciente',), 'analisispred': ('id_paciente_fk', 'id_caso_fk'),
    'muestrasaliva': ('analisis',), 'muestrasangre': ('analisis',),
    'acquisitionseries': ('patient',), 'calibration': ('acquisition_profile',),
    'calibrationreference': ('calibration',),
    'resultadosegmentacion': ('muestra', 'muestra_sangre'),
    'revisionsegmentacion': ('resultado_segmentacion',),
    'resultadocaracterizacion': ('resultado_segmentacion',),
    'resultadoanalisis': ('muestra',), 'analisismascara': ('resultado',),
    'imagejimportrecord': ('muestra',), 'segmentationexecution': ('resultado_segmentacion',),
}
SCIENTIFIC = {'ResultadoSegmentacion', 'RevisionSegmentacion', 'ResultadoCaracterizacion',
              'ResultadoAnalisis', 'AnalisisMascara', 'ImageJImportRecord', 'SegmentationExecution',
              'Calibration', 'CalibrationReference'}


class LifecycleConflict(APIException):
    status_code = 409
    default_code = 'lifecycle_conflict'


def conflict(code, **details):
    raise LifecycleConflict({'code': code, **details})


def is_admin(user):
    from api.access import profile_for
    p = profile_for(user)
    return user.is_superuser or bool(p and p.role == 'ADMIN')


def model_for(resource):
    name = RESOURCE_MODELS.get(resource)
    if not name:
        raise NotFound()
    return apps.get_model('auth' if name == 'User' else 'api', name)


def parent_objects(obj):
    return [parent for field in PARENTS.get(obj._meta.model_name, ())
            if (parent := getattr(obj, field, None)) is not None]


def inactive_ancestor(obj):
    for parent in parent_objects(obj):
        if getattr(parent, 'archived_at', None):
            return parent
        inactive = inactive_ancestor(parent)
        if inactive:
            return inactive
    return None


def is_operationally_active(obj):
    return not getattr(obj, 'archived_at', None) and inactive_ancestor(obj) is None


def active_query(model, prefix=''):
    q = Q()
    if any(f.name == 'archived_at' for f in model._meta.fields):
        q &= Q(**{prefix + 'archived_at__isnull': True})
    for field in PARENTS.get(model._meta.model_name, ()):
        parent = model._meta.get_field(field)
        child = active_query(parent.related_model, prefix + field + '__')
        q &= (Q(**{prefix + field + '__isnull': True}) | child) if parent.null else child
    return q


def active_queryset(qs):
    return qs.filter(active_query(qs.model))


def request_queryset(qs, request):
    # History is explicit, read-only, institution scoped, and ADMIN-only.
    if request.method in ('GET', 'HEAD', 'OPTIONS') and request.query_params.get('include_archived') == 'true' and is_admin(request.user):
        return qs
    return active_queryset(qs)


def lock_operational(obj):
    """Locks shared ancestors so API creation/writes serialize with lifecycle changes."""
    for parent in parent_objects(obj):
        lock_operational(parent)
    current = type(obj).objects.select_for_update().get(pk=obj.pk)
    if not is_operationally_active(current):
        conflict('RESOURCE_ARCHIVED')
    return current


def validate_binding(obj):
    current = lock_operational(obj)
    name = current._meta.model_name
    if name == 'acquisitionprofile' and not current.active:
        conflict('PROFILE_UNAVAILABLE')
    if name == 'calibration' and current.status == 'RETIRED':
        conflict('CALIBRATION_RETIRED')
    if name == 'acquisitionseries':
        validate_binding(current.acquisition_profile)
        if current.calibration_id:
            validate_binding(current.calibration)
    return current


def dependencies(obj):
    """Walk the actual reverse FK graph, deduplicate paths; never use Collector.delete."""
    domain = list(apps.get_app_config('api').get_models())
    found = {type(obj): {obj.pk}}
    frontier = [(type(obj), {obj.pk})]
    while frontier:
        parent, ids = frontier.pop()
        for child in domain:
            for f in child._meta.fields:
                if f.is_relation and f.related_model is parent and f.name not in ('actor', 'created_by', 'updated_by', 'archived_by'):
                    values = set(child.objects.filter(**{f.attname + '__in': ids}).values_list('pk', flat=True))
                    new = values - found.get(child, set())
                    if new:
                        found.setdefault(child, set()).update(new)
                        frontier.append((child, new))
    found[type(obj)].discard(obj.pk)
    Sample = apps.get_model('api', 'MuestraSaliva')
    Execution = apps.get_model('api', 'SegmentationExecution')
    sample_ids = found.get(Sample, set()) | ({obj.pk} if type(obj) is Sample else set())
    if sample_ids:
        unbound = set(Execution.objects.filter(resultado_segmentacion__isnull=True,
            request_metadata__sample_id__in=list(sample_ids)).values_list('pk', flat=True))
        if unbound:
            found.setdefault(Execution, set()).update(unbound)
    counts = {m.__name__: len(ids) for m, ids in found.items() if ids}
    if found.get(Execution):
        pending = Execution.objects.filter(pk__in=found[Execution], status='PENDING').count()
        if pending:
            counts['PendingSegmentationExecution'] = pending
    # Physical-unit snapshots are durable JSON references, not database FKs.
    name = obj._meta.model_name
    if name in ('calibration', 'acquisitionprofile'):
        key = 'calibration_id' if name == 'calibration' else 'acquisition_profile_id'
        model = apps.get_model('api', 'ResultadoCaracterizacion')
        ids = set(model.objects.filter(**{'resultado_json__calibration__' + key: obj.pk}).values_list('pk', flat=True))
        ids |= found.get(model, set())
        if ids:
            counts[model.__name__] = len(ids)
    return counts


def media_fields(obj):
    return [getattr(obj, f.name) for f in obj._meta.fields if isinstance(f, models.FileField) and getattr(obj, f.name)]


def shared_file(name):
    # Conservative across all storages: retaining a possible shared file is safer.
    for model in apps.get_app_config('api').get_models():
        for field in model._meta.fields:
            if isinstance(field, models.FileField) and model.objects.filter(**{field.name: name}).exists():
                return True
    return False


def display(obj):
    # Never persist Patient.__str__ / full patient identity in the audit log.
    return f'{obj._meta.model_name} #{obj.pk}'


def restore_issue(obj):
    parent = inactive_ancestor(obj)
    if parent:
        return {'code': 'PARENT_ARCHIVED', 'parent_type': parent._meta.model_name, 'parent_id': str(parent.pk)}
    if obj._meta.model_name == 'acquisitionseries':
        profile = obj.acquisition_profile
        if profile.archived_at or not profile.active:
            return {'code': 'PROFILE_UNAVAILABLE', 'parent_id': str(profile.pk)}
        if obj.patient.institution_id != profile.institution_id or (obj.calibration_id and obj.calibration.acquisition_profile_id != profile.pk):
            return {'code': 'INSTITUTION_MISMATCH'}
        if obj.calibration_id and obj.calibration.status == 'RETIRED':
            return {'code': 'CALIBRATION_RETIRED'}
    return None


def inspect_lifecycle(obj, user):
    from api.access import operational, profile_for, scoped
    if not operational(user):
        raise PermissionDenied()
    if not scoped(type(obj).objects.filter(pk=obj.pk), user).exists():
        raise NotFound()
    counts = dependencies(obj)
    name = obj._meta.model_name
    archivable = hasattr(obj, 'archived_at')
    admin = is_admin(user)
    p = profile_for(user)
    own = bool(p and p.role == 'OPERATOR' and getattr(obj, 'created_by_id', None) == user.pk)
    low_risk = name in ('muestrasaliva', 'muestrasangre', 'acquisitionseries')
    actions, warnings = [], []
    issue = restore_issue(obj)
    if archivable:
        if obj.archived_at:
            if admin and not issue:
                actions = ['RESTORE']
        elif is_operationally_active(obj):
            if admin:
                actions.append('ARCHIVE')
            if not counts and (admin or (own and low_risk)):
                actions.insert(0, 'HARD_DELETE')
    elif name == 'calibration' and is_operationally_active(obj) and obj.status != 'RETIRED' and admin:
        actions = ['RETIRE']
        # Evidence itself is a dependency: preserve it conservatively.
        if not counts and obj.status == 'PROVISIONAL':
            actions.insert(0, 'HARD_DELETE')
    if counts.get('PendingSegmentationExecution'):
        actions = []
        warnings.append({'code': 'RESOURCE_BUSY'})
    if issue:
        warnings.append(issue)
    if not admin and not actions:
        warnings.append({'code': 'ADMIN_REQUIRED'})
    if name in ('revisionsegmentacion', 'resultadosegmentacion', 'resultadocaracterizacion', 'calibrationreference'):
        warnings.append({'code': 'IMMUTABLE_HISTORY'})
    return {'resource_type': name, 'id': str(obj.pk), 'display': display(obj),
            'allowed_actions': actions, 'recommended_action': actions[0] if actions else None,
            'dependencies': counts, 'scientific_dependencies': bool(SCIENTIFIC.intersection(counts)),
            'archived': bool(getattr(obj, 'archived_at', None)),
            'operationally_active': is_operationally_active(obj),
            'media_files': [{'filename': PurePosixPath(f.name).name} for f in media_fields(obj)],
            'warnings': warnings}


def institution_id(obj):
    from api.access import PATHS
    path = PATHS.get(obj._meta.model_name)
    if path:
        return type(obj).objects.filter(pk=obj.pk).values_list(path, flat=True).get()
    raise ValidationError('Recurso no soportado para mutación lifecycle.')


def cleanup_media(event_id, files):
    """Only after commit. Storage errors are durable, not transaction rollback claims."""
    Event = apps.get_model('api', 'LifecycleEvent')
    outcome = []
    for file, snapshot in files:
        entry = dict(snapshot)
        try:
            if shared_file(file.name):
                entry['status'] = 'SHARED_FILE_RETAINED'
            else:
                file.storage.delete(file.name)
                entry['status'] = 'DELETED'
        except Exception as exc:
            entry.update(status='MEDIA_DELETE_FAILED', error_type=type(exc).__name__)
        outcome.append(entry)
    event = Event.objects.get(pk=event_id)
    event.metadata = {**event.metadata, 'media_cleanup': outcome}
    event.save(update_fields=['metadata'])


@transaction.atomic
def execute_lifecycle(obj, user, action, reason):
    if action not in ('HARD_DELETE', 'ARCHIVE', 'RESTORE', 'RETIRE'):
        raise ValidationError({'action': 'Acción desconocida.'})
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({'reason': 'Indique un motivo de 1 a 2000 caracteres.'})
    # Lock parent first, matching normal API writes. Archived parents need not be active here.
    def lock_tree(target):
        for parent in parent_objects(target):
            lock_tree(parent)
        type(target).objects.select_for_update().get(pk=target.pk)
    lock_tree(obj)
    obj = type(obj).objects.select_for_update().get(pk=obj.pk)
    preview = inspect_lifecycle(obj, user)
    if action not in preview['allowed_actions']:
        if not is_admin(user):
            p = getattr(user, 'sicam_profile', None)
            owned_delete = action == 'HARD_DELETE' and p and p.role == 'OPERATOR' and obj._meta.model_name in ('muestrasaliva','muestrasangre','acquisitionseries') and getattr(obj,'created_by_id',None) == user.pk
            if not owned_delete:
                raise PermissionDenied('Requiere ADMIN o ser creador de un recurso operativo seguro.')
        issue = restore_issue(obj) if action == 'RESTORE' else None
        code = issue['code'] if issue else ('SCIENTIFIC_DEPENDENCIES_EXIST' if action == 'HARD_DELETE' and preview['dependencies'] else 'ACTION_NOT_AVAILABLE')
        conflict(code, recommended_action=preview['recommended_action'], dependencies=preview['dependencies'], warnings=preview['warnings'])
    Event = apps.get_model('api', 'LifecycleEvent')
    metadata = {'dependencies': preview['dependencies'], 'created_by_id': getattr(obj, 'created_by_id', None)}
    if obj._meta.model_name == 'paciente':
        metadata['identity_mode'] = obj.identity_mode
    files = []
    if action == 'HARD_DELETE':
        for file in media_fields(obj):
            entry = {'path': file.name, 'filename': PurePosixPath(file.name).name, 'status': 'PENDING_DELETE'}
            try:
                hasher = hashlib.sha256()
                with file.storage.open(file.name, 'rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        hasher.update(block)
                entry['sha256'] = hasher.hexdigest()
            except FileNotFoundError:
                entry.update(status='MISSING_BEFORE_DELETE', missing_before_delete=True, sha256=None)
            except Exception:
                conflict('MEDIA_INSPECTION_FAILED')
            files.append((file, entry))
        metadata['media_cleanup'] = [entry for _, entry in files]
    event = Event.objects.create(institution_id=institution_id(obj), actor=user, action=action,
        target_type=obj._meta.model_name, target_id=str(obj.pk), target_display=display(obj),
        reason=reason.strip(), metadata=metadata)
    if action == 'HARD_DELETE':
        # No cascaded scientific delete: dependencies were re-read under the target lock.
        obj.delete()
        if files:
            transaction.on_commit(partial(cleanup_media, event.pk, files))
    elif action == 'ARCHIVE':
        type(obj).objects.filter(pk=obj.pk).update(archived_at=timezone.now(), archived_by=user, archive_reason=reason.strip())
    elif action == 'RESTORE':
        type(obj).objects.filter(pk=obj.pk).update(archived_at=None)
        # Keep last archive actor/reason; the RESTORE event preserves full history.
    else:
        obj.status = 'RETIRED'
        obj.updated_by = user
        obj.save(update_fields=['status', 'updated_by', 'updated_at'])
    return {'action': action, 'event_id': event.pk, 'target_id': event.target_id}
