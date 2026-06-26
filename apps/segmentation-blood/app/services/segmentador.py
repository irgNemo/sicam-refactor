from segmentacion_core.sicam_master import segmentar_desde_bytes


def segmentar_pipeline(file_bytes: bytes):
    return segmentar_desde_bytes(file_bytes)