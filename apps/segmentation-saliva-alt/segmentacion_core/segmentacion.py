"""Adapt label masks to the existing SICAM polygon contract."""
from segmentacion_core.poligonos import obtener_poligonos_desde_mascara


def convertir_resultado(resultado):
    objetos = []
    for key, tipo in (
        ("membranas", "membrana"),
        ("nucleos", "nucleo"),
        ("micronucleos", "micronucleo"),
    ):
        objetos.extend(obtener_poligonos_desde_mascara(resultado[key], tipo))
    return {"objetos": objetos}
