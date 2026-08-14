import apiClient from "./apiClient";

export function getSegmentationRevisions(resultadoId) {
  return apiClient.get(`/api/resultados-segmentacion/${resultadoId}/revisiones/`);
}

export function getOrCreateSegmentationDraft(resultadoId) {
  return apiClient.post(`/api/resultados-segmentacion/${resultadoId}/revisiones/`);
}

export function getSegmentationRevision(revisionId) {
  return apiClient.get(`/api/revisiones-segmentacion/${revisionId}/`);
}
