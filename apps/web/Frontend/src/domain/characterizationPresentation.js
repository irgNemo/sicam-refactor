export function isSalivaMorphometricV2(resultJson) {
  return Boolean(
    resultJson &&
    typeof resultJson === "object" &&
    resultJson.sample_type === "SALIVA" &&
    resultJson.schema_version === "2.0"
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
