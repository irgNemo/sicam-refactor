import apiClient from "./apiClient";

export function segmentarMuestra(muestraId) {
  return apiClient.post(`/api/muestras/${muestraId}/segmentar/`);
}
