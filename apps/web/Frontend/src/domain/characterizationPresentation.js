export function isSalivaMorphometricV2(resultJson) {
  return Boolean(
    resultJson &&
    typeof resultJson === "object" &&
    resultJson.sample_type === "SALIVA" &&
    ["2.0", "2.1"].includes(resultJson.schema_version)
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

export function objectMetricGroups(metrics, extended = false, includeDependencyMetrics = false) {
  const values = metrics && typeof metrics === "object" ? metrics : {};
  const rows = (keys, source = values) => keys.map(key => ({
    key, label: METRIC_LABELS[key], value: formatMetric(key, source?.[key]),
  }));
  const morphology = ["area_px2", "perimeter_px", "centroid_px", "circularity"];
  const intensity = ["mean_gray_intensity"];
  if (extended) {
    morphology.push("eccentricity");
    intensity.push("std_gray_intensity");
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
    groups.push({ key: "relative", label: "Relación con el núcleo asociado", rows: rows([
      "distance_to_nucleus_px", "area_fraction_to_nucleus", "intensity_fraction_to_nucleus",
    ]) });
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
