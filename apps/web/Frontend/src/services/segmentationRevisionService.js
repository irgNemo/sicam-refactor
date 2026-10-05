import apiClient from "./apiClient";

export function getSegmentationRevisions(resultadoId) {
  return apiClient.get(`/api/resultados-segmentacion/${resultadoId}/revisiones/`);
}

export function getEffectiveSegmentation(resultadoId) {
  return apiClient.get(`/api/resultados-segmentacion/${resultadoId}/efectivo/`);
}

export function getOrCreateSegmentationDraft(resultadoId) {
  return apiClient.post(`/api/resultados-segmentacion/${resultadoId}/revisiones/`);
}

export function getSegmentationRevision(revisionId) {
  return apiClient.get(`/api/revisiones-segmentacion/${revisionId}/`);
}

export function updateSegmentationDraft(revisionId, resultadoEditado, expectedUpdatedAt) {
  return apiClient.patch(`/api/revisiones-segmentacion/${revisionId}/`, {
    resultado_editado: resultadoEditado,
    ...(expectedUpdatedAt ? { expected_updated_at: expectedUpdatedAt } : {}),
  });
}

export function validateRevision(revisionId, expectedUpdatedAt) {
  return apiClient.post(`/api/revisiones-segmentacion/${revisionId}/validar/`,
    expectedUpdatedAt ? { expected_updated_at: expectedUpdatedAt } : undefined);
}
