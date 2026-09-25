import apiClient from "./apiClient";
import { SAMPLE_TYPES } from "../domain/segmentationTypes";
import { SALIVA_STRATEGIES } from "../domain/segmentationStrategies";

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

export function segmentarMuestra(
  muestraId,
  sampleType = SAMPLE_TYPES.SALIVA,
  strategy = SALIVA_STRATEGIES.CURRENT
) {
  const url = `${getSampleEndpoint(sampleType)}/${muestraId}/segmentar/`;
  if (sampleType === SAMPLE_TYPES.SALIVA) {
    return apiClient.post(url, { segmentation_strategy: strategy });
  }
  return apiClient.post(url);
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
