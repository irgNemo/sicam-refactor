import { SAMPLE_TYPES } from "./segmentationTypes";

export const SALIVA_STRATEGIES = Object.freeze({
  CURRENT: "CURRENT_CUSTOM_V1",
  ALT: "ALT_CPSAM_MORPHOLOGICAL_V1",
});

export const SALIVA_STRATEGY_OPTIONS = Object.freeze([
  {
    value: SALIVA_STRATEGIES.CURRENT,
    label: "Modelo SICAM",
    description: "Modelo de segmentación utilizado actualmente por SICAM.",
  },
  {
    value: SALIVA_STRATEGIES.ALT,
    label: "Cellpose-SAM alternativo",
    description: "Método alternativo disponible para imágenes de saliva.",
  },
]);

// Missing provenance is not evidence that CURRENT produced a result.
export function segmentationStrategyLabel(sampleType, strategy) {
  if (sampleType !== SAMPLE_TYPES.SALIVA) return null;
  return SALIVA_STRATEGY_OPTIONS.find(option => option.value === strategy)?.label
    || "Método no disponible";
}
