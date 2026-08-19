FUENTE_AUTOMATICO = 'AUTOMATICO'
FUENTE_VALIDADA = 'VALIDADA'


def get_latest_validated_revision(resultado_segmentacion):
    prefetched = getattr(
        resultado_segmentacion,
        'validated_revisions_for_effective',
        None
    )
    if prefetched is not None:
        return prefetched[0] if prefetched else None

    return resultado_segmentacion.revisiones.filter(
        estado='VALIDADA'
    ).order_by('-numero_revision').first()


def resolve_effective_segmentation(resultado_segmentacion):
    latest_validated = get_latest_validated_revision(resultado_segmentacion)

    if latest_validated:
        return {
            'resultado_segmentacion_id': (
                resultado_segmentacion.id_resultado_segmentacion
            ),
            'fuente': FUENTE_VALIDADA,
            'revision': {
                'id_revision_segmentacion': (
                    latest_validated.id_revision_segmentacion
                ),
                'numero_revision': latest_validated.numero_revision,
                'estado': latest_validated.estado,
                'validado_en': latest_validated.validado_en,
            },
            'resultado': latest_validated.resultado_editado,
            'resumen': latest_validated.resumen,
        }

    automatic_result = resultado_segmentacion.resultado_normalizado
    automatic_summary = None
    if isinstance(automatic_result, dict):
        automatic_summary = automatic_result.get('summary')

    return {
        'resultado_segmentacion_id': (
            resultado_segmentacion.id_resultado_segmentacion
        ),
        'fuente': FUENTE_AUTOMATICO,
        'revision': None,
        'resultado': automatic_result,
        'resumen': automatic_summary,
    }
