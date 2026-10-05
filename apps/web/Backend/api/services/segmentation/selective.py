"""SALIVA editorial replacement. HTTP runs outside all service transactions."""
from copy import deepcopy
import hashlib
import json

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from api.models import ResultadoSegmentacion, RevisionSegmentacion, SegmentationExecution
from .normalizers import normalize_segmentation_result, validate_normalized_segmentation_result
from .revisions import build_revision_snapshot_from_normalized, calculate_revision_summary
from .exceptions import SegmentationTimeoutError, SegmentationConnectionError

TARGETS = ('ALL', 'MEMBRANES', 'NUCLEI_AND_MICRONUCLEI')
LABELS = {'MEMBRANES': {'membrana'}, 'NUCLEI_AND_MICRONUCLEI': {'nucleo', 'micronucleo'}}


class SelectiveError(Exception):
    def __init__(self, code, message, status=409):
        super().__init__(message)
        self.code, self.status = code, status


def lock_result(result_id):
    """First statement must be a write: SQLite has no SELECT FOR UPDATE locks.

    All editorial writers use this short parent lock, including save/validate.
    It also serializes on row-locking databases; never held across HTTP.
    """
    ResultadoSegmentacion.objects.filter(pk=result_id).update(next_editorial_id=F('next_editorial_id'))
    return ResultadoSegmentacion.objects.select_for_update().get(pk=result_id)


def source_state(result):
    revisions = list(result.revisiones.order_by('numero_revision'))
    draft = next((r for r in revisions if r.estado == 'BORRADOR'), None)
    validated = next((r for r in reversed(revisions) if r.estado == 'VALIDADA'), None)
    source = draft or validated
    snapshot = deepcopy(source.resultado_editado) if source else build_revision_snapshot_from_normalized(result)
    # Include all revision identities, timestamps and contents to detect source switches,
    # validation, saves of identical JSON and changes to base/VALIDADA during computation.
    fingerprint = {
        'base': [result.pk, result.base_origin, result.segmentation_strategy,
                 result.estado, result.actualizado_en.isoformat(), result.resultado_normalizado],
        'revisions': [[r.pk, r.numero_revision, r.estado, r.actualizado_en.isoformat(),
                       r.resultado_editado, r.resumen] for r in revisions],
    }
    token = hashlib.sha256(json.dumps(fingerprint, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    summary = calculate_revision_summary(snapshot, sample_type=result.tipo_muestra)
    return {'snapshot': snapshot, 'source_token': token, 'draft': draft, 'source': source,
            'source_kind': 'BORRADOR' if draft else 'VALIDADA' if validated else result.base_origin,
            'summary': summary}


def require_saliva_base(result):
    if result.tipo_muestra != 'SALIVA' or result.estado != 'COMPLETADO':
        raise SelectiveError('INVALID_SELECTIVE_BASE', 'Seleccione un resultado SALIVA completado.', 400)


def context_for(result):
    from rest_framework.serializers import DateTimeField
    require_saliva_base(result)
    state = source_state(result)
    return {'resultado_segmentacion_id': result.pk, 'source_token': state['source_token'],
            'source_kind': state['source_kind'], 'revision_id': state['source'].pk if state['source'] else None,
            'revision_updated_at': DateTimeField().to_representation(state['source'].actualizado_en) if state['source'] else None,
            'summary': state['summary']}


def advance_allocator(result, *snapshots):
    """Defensive bootstrap also covers legacy writers/fixtures and historical revisions."""
    snapshots = [result.resultado_normalizado, *snapshots,
                 *result.revisiones.values_list('resultado_editado', flat=True)]
    high = result.next_editorial_id
    for snapshot in snapshots:
        for obj in (snapshot or {}).get('objects', []):
            value = obj.get('id')
            if isinstance(value, int) and not isinstance(value, bool):
                high = max(high, value + 1)
    result.next_editorial_id = high


def reserve_ids(result, count):
    advance_allocator(result)
    start = result.next_editorial_id
    result.next_editorial_id += count
    result.save(update_fields=['next_editorial_id'])
    return list(range(start, start + count))


def fail_execution(execution, code, cancelled=False):
    SegmentationExecution.objects.filter(pk=execution.pk).update(
        status='CANCELLED' if cancelled else 'FAILED', error=code, completed_at=timezone.now(),
    )


def perform_partial(*, sample, result_id, strategy, target, source_token,
                    confirm_replacement, read_image, segment):
    with transaction.atomic():
        try:
            result = lock_result(result_id)
        except ResultadoSegmentacion.DoesNotExist:
            raise SelectiveError('INVALID_SELECTIVE_BASE', 'Resultado no disponible.', 400)
        require_saliva_base(result)
        if result.muestra_id != sample.pk:
            raise SelectiveError('INVALID_SELECTIVE_BASE', 'El resultado no pertenece a la muestra.', 400)
        state = source_state(result)
        if state['source_token'] != source_token:
            raise SelectiveError('SEGMENTATION_SOURCE_CHANGED', 'La anotación cambió. Recargue antes de continuar.')
        selected_exists = any(o['label'] in LABELS[target] for o in state['snapshot']['objects'])
        if (state['draft'] or selected_exists) and not confirm_replacement:
            raise SelectiveError('REPLACEMENT_CONFIRMATION_REQUIRED', 'Confirme el reemplazo de las categorías seleccionadas.')
        execution = SegmentationExecution.objects.create(
            resultado_segmentacion=result, revision=state['draft'], strategy=strategy, target=target,
            source_token=source_token,
            request_metadata={'sample_id': sample.pk, 'confirm_replacement': confirm_replacement,
                              'source_kind': state['source_kind']},
            checkpoint={'snapshot': state['snapshot'], 'source_token': source_token,
                        'revision_id': state['source'].pk if state['source'] else None,
                        'revision_number': state['source'].numero_revision if state['source'] else None,
                        'summary': state['summary']},
        )

    try:
        raw = segment('SALIVA', read_image(sample), filename=sample.imagen.name,
                      segmentation_strategy=strategy)
        normalized = normalize_segmentation_result(raw, sample_type='SALIVA')
        validate_normalized_segmentation_result(normalized, sample_type='SALIVA')
    except Exception as exc:
        code, status = 'SEGMENTATION_SERVICE_FAILED', 502
        if isinstance(exc, SegmentationTimeoutError):
            code, status = 'SEGMENTATION_TIMEOUT', 504
        elif isinstance(exc, SegmentationConnectionError):
            code, status = 'SEGMENTATION_UNAVAILABLE', 503
        fail_execution(execution, code)
        raise SelectiveError(code, 'No se pudo completar la segmentación; la anotación no cambió.', status) from exc

    try:
        # Keep the completed calculation for audit even if a later version conflict
        # cancels application, or the editorial transaction rolls back.
        SegmentationExecution.objects.filter(pk=execution.pk).update(
            normalized_response=normalized, counts=normalized['summary'],
        )
        with transaction.atomic():
            result = lock_result(result_id)
            current = source_state(result)
            if current['source_token'] != source_token:
                raise SelectiveError('SEGMENTATION_SOURCE_CHANGED', 'La anotación cambió durante el cálculo. No se aplicó el resultado.')
            snapshot = deepcopy(current['snapshot'])
            # Preserve complete untouched objects and their relative order without normalization.
            preserved = [obj for obj in snapshot['objects'] if obj['label'] not in LABELS[target]]
            replacements = [deepcopy(obj) for obj in normalized['objects'] if obj['label'] in LABELS[target]]
            for obj, editorial_id in zip(replacements, reserve_ids(result, len(replacements))):
                execution_object_id = obj['id']
                obj['id'] = editorial_id
                obj['provenance'] = {'origin': 'automatic', 'base_object_id': None,
                                     'strategy': strategy, 'segmentation_execution_id': str(execution.pk),
                                     'execution_object_id': execution_object_id}
            snapshot['objects'] = preserved + replacements
            summary = calculate_revision_summary(snapshot)
            draft = current['draft']
            if draft:
                draft.resultado_editado, draft.resumen = snapshot, summary
                draft.save(update_fields=['resultado_editado', 'resumen', 'actualizado_en'])
            else:
                last = result.revisiones.order_by('-numero_revision').first()
                draft = RevisionSegmentacion.objects.create(
                    resultado_segmentacion=result, numero_revision=(last.numero_revision + 1 if last else 1),
                    resultado_editado=snapshot, resumen=summary,
                )
            execution.revision = draft
            execution.normalized_response = normalized
            execution.counts = normalized['summary']
            execution.status = 'COMPLETED'
            execution.completed_at = timezone.now()
            execution.save(update_fields=['revision', 'status', 'completed_at'])
            return result, draft, execution
    except Exception as exc:
        code = exc.code if isinstance(exc, SelectiveError) else 'SEGMENTATION_PERSISTENCE_FAILED'
        fail_execution(execution, code, cancelled=code == 'SEGMENTATION_SOURCE_CHANGED')
        if isinstance(exc, SelectiveError):
            raise
        raise SelectiveError(code, 'No se aplicaron cambios a la anotación.', 500) from exc
