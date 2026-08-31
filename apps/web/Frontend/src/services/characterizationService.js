import apiClient from "./apiClient";

export function obtenerCaracterizaciones(resultadoSegmentacionId) {
  return apiClient.get(
    `/api/resultados-segmentacion/${resultadoSegmentacionId}/caracterizaciones/`
  );
}

export function caracterizarResultado(resultadoSegmentacionId) {
  return apiClient.post(
    `/api/resultados-segmentacion/${resultadoSegmentacionId}/caracterizar/`
  );
}
