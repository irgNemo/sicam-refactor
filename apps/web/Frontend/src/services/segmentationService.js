import apiClient from "./apiClient";
import { SAMPLE_TYPES } from "../domain/segmentationTypes";

const SAMPLE_ENDPOINTS = {
  [SAMPLE_TYPES.SALIVA]: "/api/muestras",
  [SAMPLE_TYPES.BLOOD]: "/api/muestras-sangre",
};

function getSampleEndpoint(sampleType = SAMPLE_TYPES.SALIVA) {
  return SAMPLE_ENDPOINTS[sampleType] || SAMPLE_ENDPOINTS[SAMPLE_TYPES.SALIVA];
}

export function listarMuestras(sampleType = SAMPLE_TYPES.SALIVA) {
  return apiClient.get(`${getSampleEndpoint(sampleType)}/`);
}

export function segmentarMuestra(muestraId, sampleType = SAMPLE_TYPES.SALIVA) {
  return apiClient.post(`${getSampleEndpoint(sampleType)}/${muestraId}/segmentar/`);
}

export function obtenerResultadosSegmentacion(
  muestraId,
  sampleType = SAMPLE_TYPES.SALIVA
) {
  return apiClient.get(
    `${getSampleEndpoint(sampleType)}/${muestraId}/resultados-segmentacion/`
  );
}

export function obtenerResumenSegmentacionCaso(casoId) {
  return apiClient.get(`/api/casos/${casoId}/resumen-segmentacion/`);
}
