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

export function updateSegmentationDraft(revisionId, resultadoEditado) {
  return apiClient.patch(`/api/revisiones-segmentacion/${revisionId}/`, {
    resultado_editado: resultadoEditado,
  });
}

export function validateRevision(revisionId) {
  return apiClient.post(`/api/revisiones-segmentacion/${revisionId}/validar/`);
}
