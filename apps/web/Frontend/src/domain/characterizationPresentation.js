export function isSalivaMorphometricV2(resultJson) {
  return Boolean(
    resultJson &&
    typeof resultJson === "object" &&
    resultJson.sample_type === "SALIVA" &&
    ["2.0", "2.1", "2.2", "2.3"].includes(resultJson.schema_version)
  );
}

export function formatNumber(value, digits = 2, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";

  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return "—";

  return `${numberValue.toFixed(digits)}${suffix}`;
}

export function formatGenotoxicityPercentage(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "—";

  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return "—";

  return `${(numberValue * 100).toFixed(digits)} %`;
}

export function displayValue(value) {
  return value === null || value === undefined || value === ""
    ? "—"
    : value;
}

// Presentation only: values and associations always come from the snapshot.
export const METRIC_LABELS = Object.freeze({
  area_px2: "Área",
  perimeter_px: "Perímetro",
  centroid_px: "Centroide",
  circularity: "Circularidad",
  eccentricity: "Excentricidad",
  mean_gray_intensity: "Intensidad media",
  std_gray_intensity: "Desv. estándar de intensidad",
  contrast: "Contraste",
  homogeneity: "Homogeneidad",
  energy: "Energía",
  correlation: "Correlación",
  entropy: "Entropía",
  valid_angles: "Ángulos válidos",
  valid_pairs: "Pares válidos",
  distance_to_nucleus_px: "Distancia al núcleo",
  area_fraction_to_nucleus: "Fracción de área respecto al núcleo",
  intensity_fraction_to_nucleus: "Fracción de intensidad respecto al núcleo",
  // Sprint 18U-C1 — Characterization 2.3 metrics
  elongation_index: "Índice de elongación",
  convex_solidity: "Solidez convexa",
  mn_nucleus_perimeter_ratio_px: "Razón de perímetros MN/núcleo",
  mn_nucleus_perimeter_ratio_physical: "Razón de perímetros MN/núcleo (física)",
  mn_nucleus_min_distance_px: "Separación mínima MN–núcleo",
  mn_nucleus_min_distance_um: "Separación mínima MN–núcleo (µm)",
});

export function formatCentroid(value) {
  if (!Array.isArray(value) || value.length !== 2 || !value.every(Number.isFinite)) return "—";
  return `(${formatNumber(value[0])}, ${formatNumber(value[1])}) px`;
}

export function formatMetric(key, value) {
  if (key === "centroid_px") return formatCentroid(value);
  if (!Number.isFinite(value)) return "—";
  if (["valid_angles", "valid_pairs"].includes(key)) {
    return Number.isInteger(value) ? formatNumber(value, 0) : "—";
  }
  if (key === "area_px2") return formatNumber(value, 2, " px²");
  if (["perimeter_px", "distance_to_nucleus_px"].includes(key)) return formatNumber(value, 2, " px");
  return formatNumber(value, 4);
}

export function objectMetricGroups(metrics, extended = false, includeDependencyMetrics = false, physical = false, schema = null) {
  const values = metrics && typeof metrics === "object" ? metrics : {};
  const rows = (keys, source = values) => keys.map(key => metricPresentation(key, source, physical));
  const morphology = ["area_px2", "perimeter_px", "centroid_px", "circularity"];
  const intensity = ["mean_gray_intensity"];
  if (extended) {
    morphology.push("eccentricity");
    intensity.push("std_gray_intensity");
  }
  // 2.3 object-level metrics
  const is23 = schema === "2.3";
  if (is23) {
    morphology.push("elongation_index", "convex_solidity");
  }
  const groups = [
    { key: "morphology", label: "Morfometría", rows: rows(morphology) },
    { key: "intensity", label: "Intensidad", rows: rows(intensity) },
  ];
  if (extended) {
    groups.push({
      key: "texture", label: "Textura GLCM",
      rows: rows(["contrast", "homogeneity", "energy", "correlation", "entropy"], values.texture),
      quality: rows(["valid_angles", "valid_pairs"], values.texture),
    });
  }
  if (includeDependencyMetrics) {
    const relMetrics = ["distance_to_nucleus_px", "area_fraction_to_nucleus", "intensity_fraction_to_nucleus"];
    if (is23) {
      relMetrics.push("mn_nucleus_perimeter_ratio_px", "mn_nucleus_min_distance_px");
    }
    groups.push({ key: "relative", label: "Relación con el núcleo asociado", rows: rows(relMetrics) });
  }
  return groups;
}

export function textureMethodologyRows(texture) {
  if (!texture || typeof texture !== "object") return [];
  const boolean = value => value === true ? "Sí" : value === false ? "No" : "—";
  const text = value => typeof value === "string" && value.trim() ? value : "—";
  return [
    ["method", "Método", text(texture.method)],
    ["gray_levels", "Niveles de gris", formatMetric("valid_pairs", texture.gray_levels)],
    ["distance_px", "Distancia", Number.isFinite(texture.distance_px) ? `${texture.distance_px} px` : "—"],
    ["angles_deg", "Ángulos", Array.isArray(texture.angles_deg) && texture.angles_deg.length
      ? texture.angles_deg.map(value => Number.isFinite(value) ? `${value}°` : "—").join(", ") : "—"],
    ["symmetric", "Matriz simétrica", boolean(texture.symmetric)],
    ["normalized", "Matriz normalizada", boolean(texture.normalized)],
    ["aggregation", "Agregación", texture.aggregation === "mean_over_valid_angles"
      ? "Promedio de ángulos válidos" : text(texture.aggregation).replaceAll("_", " ")],
  ].map(([key, label, value]) => ({ key, label, value }));
}

const WARNING_LABELS = Object.freeze({
  ECCENTRICITY_NOT_COMPUTABLE: "No fue posible calcular la excentricidad.",
  TEXTURE_INSUFFICIENT_PAIRS: "No hay suficientes pares de píxeles para calcular la textura.",
  TEXTURE_CORRELATION_UNDEFINED: "No fue posible calcular la correlación GLCM para este objeto.",
  SELF_INTERSECTING_POLYGON: "Polígono con autointersecciones.",
  INVALID_POINTS: "El objeto no contiene un polígono válido.",
  DEGENERATE_POLYGON: "Polígono de área nula.",
  IMAGE_UNAVAILABLE: "Imagen original no disponible.",
  COORDINATE_SPACE_MISMATCH: "Coordenadas incompatibles con la imagen original.",
  INVALID_CIRCULARITY: "Circularidad no calculable.",
  UNASSOCIATED_NUCLEUS: "Núcleo no asociado a una región celular.",
  UNASSOCIATED_MICRONUCLEUS: "Micronúcleo no asociado a una región celular.",
  POINT_ON_BOUNDARY: "Centroide sobre el borde de una región celular.",
  AMBIGUOUS_MEMBRANE_ASSOCIATION: "Asociación ambigua a regiones celulares.",
});

export function warningLabel(code) {
  if (Object.prototype.hasOwnProperty.call(WARNING_LABELS, code)) return WARNING_LABELS[code];
  return typeof code === "string" && code ? `Advertencia: ${code}` : "Advertencia";
}

// Backend values only. Never derive physical measures from calibration in Vue.
const PHYSICAL_METRICS = Object.freeze({
  area_px2: ["area_um2", " µm²"], perimeter_px: ["perimeter_um", " µm"],
  centroid_px: ["centroid_um", " µm"], distance_to_nucleus_px: ["distance_to_nucleus_um", " µm"],
  mean_nucleus_area_px2: ["mean_nucleus_area_um2", " µm²"],
  // 2.3 metrics with physical variants
  mn_nucleus_min_distance_px: ["mn_nucleus_min_distance_um", " µm"],
  mn_nucleus_perimeter_ratio_px: ["mn_nucleus_perimeter_ratio_physical", ""],
});
export function metricPresentation(key, metrics, physical = false) {
  const pixel = key === "mean_nucleus_area_px2"
    ? formatMetric("area_px2", metrics?.[key]) : formatMetric(key, metrics?.[key]);
  const mapping = PHYSICAL_METRICS[key];
  const value = mapping ? metrics?.[mapping[0]] : null;
  const coordinate = key === "centroid_px";
  const valid = coordinate
    ? Array.isArray(value) && value.length === 2 && value.every(Number.isFinite)
    : Number.isFinite(value);
  return {
    key, label: METRIC_LABELS[key],
    value: physical && mapping && valid
      ? coordinate ? `(${formatNumber(value[0], 3)}, ${formatNumber(value[1], 3)}) µm`
        : formatNumber(value, 3, mapping[1]) : pixel,
    secondary: physical && mapping && valid ? pixel : null,
  };
}

const PHYSICAL_REASONS = Object.freeze({
  NO_ACQUISITION_SERIES: "Sin serie de adquisición.",
  NO_CALIBRATION: "Sin calibración.", CALIBRATION_RETIRED: "La calibración está retirada.",
  PROFILE_MISMATCH: "El perfil de adquisición no coincide.",
  RESOLUTION_MISMATCH: "Resolución incompatible.", PATIENT_MISMATCH: "La serie no corresponde al paciente.",
  IMAGE_MODE_MISMATCH: "El modo de imagen no coincide con el perfil.",
  INVALID_IMAGE: "No se pudo leer la imagen original.",
  INVALID_CALIBRATION: "La calibración no es válida.",
});
export function physicalUnavailableReason(reason) {
  return Object.hasOwn(PHYSICAL_REASONS, reason) ? PHYSICAL_REASONS[reason]
    : "Compatibilidad física no disponible para este resultado.";
}
