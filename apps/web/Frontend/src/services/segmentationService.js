import apiClient from "./apiClient";

export function segmentarMuestra(muestraId) {
  return apiClient.post(`/api/muestras/${muestraId}/segmentar/`);
}

export function obtenerResultadosSegmentacion(muestraId) {
  return apiClient.get(`/api/muestras/${muestraId}/resultados-segmentacion/`);
}
