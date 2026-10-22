import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { createSSRApp } from 'vue';
import { renderToString } from '@vue/server-renderer';
import { saliva21Fixture } from './fixtures/saliva21.mjs';
const server = await createServer({
  root: fileURLToPath(new URL('../', import.meta.url)), configFile: false,
  plugins: [vuePlugin()], optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false, ws: false, watch: null }, appType: 'custom',
});
const keepAlive = setInterval(() => {}, 1000);
after(async () => { clearInterval(keepAlive); await server.close(); });
const P = await server.ssrLoadModule('/src/domain/characterizationPresentation.js');
const { default: Panel } = await server.ssrLoadModule('/src/components/characterization/CharacterizationResultPanel.vue');
function fixture() {
  const result = saliva21Fixture();
  Object.assign(result, {
    schema_version: '2.2', version: '2.2', physical_units_available: true,
    physical_status: 'COMPATIBLE_PROVISIONAL', physical_unavailable_reason: null,
    physical_measurements_status: 'PROVISIONAL_CALIBRATION',
    calibration: { label: 'CAL-SYNTHETIC', status: 'PROVISIONAL', scale_x_um_per_px: '0.055233934048', scale_y_um_per_px: '0.055010060892' },
    image_dimensions_px: { width: 4928, height: 4928 },
  });
  // Arbitrary persisted measures: the UI must never compute these from scales.
  Object.assign(result.cells[0].metrics, { area_um2: 65.42123, perimeter_um: 31.27123, centroid_um: [1.23456, 2.98765] });
  Object.assign(result.cells[0].nuclei[0].metrics, { area_um2: 11.12345 });
  Object.assign(result.cells[0].micronuclei[0].metrics, { distance_to_nucleus_um: 3.12345 });
  result.summary.mean_nucleus_area_um2 = 17.12345;
  return result;
}
const render = resultJson => renderToString(createSSRApp(Panel, {
  sampleType: 'SALIVA', selectedSegmentationResult: { id: 1, estado: 'COMPLETADO' },
  currentCharacterization: { algorithm_version: resultJson.version, resultado_json: resultJson },
}));
test('2.2 physical primary, px secondary for every dimensional type and summary; immutable input', async () => {
  const json = fixture(); const before = structuredClone(json); const html = await render(json);
  for (const value of ['65.421 µm²', '31.271 µm', '(1.235, 2.988) µm', '11.123 µm²', '3.123 µm', '17.123 µm²']) assert.ok(html.includes(value), value);
  assert.match(html, /pixel-secondary[^>]*>[^<]*px/);
  const row = P.metricPresentation('area_px2', json.cells[0].metrics, true);
  assert.equal(row.value, '65.421 µm²');
  assert.equal(row.secondary, P.formatMetric('area_px2', json.cells[0].metrics.area_px2));
  assert.deepEqual(json, before);
});
test('provisional snapshot, resolution and separate sx/sy visible in context', async () => {
  const html = await render(fixture());
  for (const value of ['CAL-SYNTHETIC', 'Provisional', 'Las medidas físicas utilizan una calibración provisional.',
    '0.055234 µm/px', '0.055010 µm/px', '4928 × 4928 px', 'no del portaobjetos', 'momento de la caracterización']) assert.ok(html.includes(value), value);
  assert.doesNotMatch(html, /0\.0551219974698993/);
});
test('validated calibration: same representation without provisional warning', async () => {
  const json = fixture(); json.calibration.status = 'VALIDATED'; json.physical_status = 'COMPATIBLE';
  const html = await render(json); assert.match(html, /Validada/); assert.match(html, /65.421 µm²/);
  assert.doesNotMatch(html, /Provisional|calibración provisional/);
});
for (const [reason, expected] of [
  ['NO_ACQUISITION_SERIES', 'Sin serie de adquisición.'], ['NO_CALIBRATION', 'Sin calibración.'],
  ['RESOLUTION_MISMATCH', 'Resolución incompatible.'], ['CALIBRATION_RETIRED', 'La calibración está retirada.'],
  ['PROFILE_MISMATCH', 'El perfil de adquisición no coincide.'], ['PATIENT_MISMATCH', 'La serie no corresponde al paciente.'],
  ['IMAGE_MODE_MISMATCH', 'El modo de imagen no coincide con el perfil.'],
  ['INVALID_IMAGE', 'No se pudo leer la imagen original.'], ['INVALID_CALIBRATION', 'La calibración no es válida.'],
]) {
  test(`${reason}: pixels and human explanation, no stale physical fields`, async () => {
    const json = fixture(); json.physical_units_available = false; json.physical_unavailable_reason = reason;
    const html = await render(json); assert.ok(html.includes(expected)); assert.match(html, /Medidas físicas no disponibles/);
    assert.match(html, /px²/); assert.doesNotMatch(html, /µm|CAL-SYNTHETIC/);
  });
}
test('dimensionless, intensity, GLCM unchanged and unconverted', async () => {
  const json = fixture(); const before = saliva21Fixture();
  for (const group of P.objectMetricGroups(json.cells[0].metrics, true, true, true)) {
    for (const row of group.rows) {
      if (['area_px2', 'perimeter_px', 'centroid_px', 'distance_to_nucleus_px'].includes(row.key)) continue;
      const old = P.objectMetricGroups(before.cells[0].metrics, true, true).find(g => g.key === group.key).rows.find(r => r.key === row.key);
      assert.equal(row.value, old.value); assert.equal(row.secondary, null); assert.doesNotMatch(row.value, /µm/);
    }
  }
  const html = await render(json);
  for (const text of ['Excentricidad', 'Intensidad media', 'Desv. estándar', 'Textura GLCM', '32', '1 px', 'no está normalizada a una distancia física']) assert.ok(html.includes(text), text);
});
test('null physical falls back to pixels; zero valid; no derived measures', async () => {
  const json = fixture(); json.cells[0].metrics.area_um2 = null;
  let html = await render(json); assert.doesNotMatch(html, /65.421 µm²|NaN|Infinity|undefined/);
  const row = P.metricPresentation('area_px2', json.cells[0].metrics, true);
  assert.equal(row.secondary, null); assert.match(row.value, /px²/);
  json.cells[0].metrics.area_um2 = 0; html = await render(json); assert.match(html, /0.000 µm²/);
});
test('historical 2.1 has no new physical context or reinterpretation', async () => {
  const html = await render(saliva21Fixture()); assert.doesNotMatch(html, /µm|Calibración:|Medidas físicas no disponibles/);
  assert.match(html, /px²/); assert.equal(P.isSalivaMorphometricV2(fixture()), true);
  assert.equal(P.isSalivaMorphometricV2({ ...fixture(), sample_type: 'SANGRE' }), false);
});
