import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { parse } from '@vue/compiler-sfc';
import { compile, createRenderer, createSSRApp, h, nextTick, reactive, useId } from 'vue';
import { renderToString } from '@vue/server-renderer';
import { saliva21Fixture, effective21Fixture } from './fixtures/saliva21.mjs';

const server = await createServer({
  root: fileURLToPath(new URL('../', import.meta.url)), configFile: false,
  plugins: [vuePlugin()], optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false, ws: false, watch: null }, appType: 'custom',
});
const keepAlive = setInterval(() => {}, 1000);
after(async () => { clearInterval(keepAlive); await server.close(); });
const load = path => server.ssrLoadModule(`/src/${path}`);
const P = await load('domain/characterizationPresentation.js');
const { default: Panel } = await load('components/characterization/CharacterizationResultPanel.vue');
const { default: Morph } = await load('components/characterization/SalivaMorphometricResult.vue');
const { default: Metrics } = await load('components/characterization/SalivaObjectMetrics.vue');
const { default: Overlay } = await load('components/characterization/CharacterizationEffectiveOverlay.vue');
const historical = JSON.parse(await readFile(new URL('../../Backend/api/test_data/characterization_saliva_2_0.json', import.meta.url), 'utf8'));
const propsFor = (json, strategy = 'CURRENT_CUSTOM_V1') => ({
  sampleType: json.sample_type,
  selectedSegmentationResult: { id: 7, segmentation_strategy: strategy, estado: 'COMPLETADO' },
  currentCharacterization: { algorithm_version: json.version, resultado_json: json },
});
const render = json => renderToString(createSSRApp(Panel, propsFor(json)));

for (const [key, input, expected] of [
  ['eccentricity', .654321, '0.6543'], ['std_gray_intensity', .125, '0.1250'],
  ['contrast', 0, '0.0000'], ['homogeneity', 1, '1.0000'], ['energy', 1, '1.0000'],
  ['correlation', null, '—'], ['entropy', .00004, '0.0000'],
  ['valid_angles', 4, '4'], ['valid_pairs', 123, '123'], ['valid_pairs', 0, '0'],
  ['area_px2', 12.3456, '12.35 px²'], ['perimeter_px', 12.3456, '12.35 px'],
  ['centroid_px', [1.2345, 2], '(1.23, 2.00) px'],
  ['distance_to_nucleus_px', 2, '2.00 px'],
]) {
  test(`formatter ${key}: ${JSON.stringify(input)} → ${expected}`, () => {
    assert.equal(P.formatMetric(key, input), expected);
    assert.ok(P.METRIC_LABELS[key]);
  });
}

test('missing/nonfinite metrics use dash; zero and small values remain numbers; no input mutation', () => {
  for (const value of [null, undefined, NaN, Infinity, -Infinity, '', false, {}]) {
    assert.equal(P.formatMetric('eccentricity', value), '—');
  }
  assert.equal(P.formatMetric('eccentricity', 0), '0.0000');
  assert.equal(P.formatMetric('eccentricity', .00001), '0.0000');
  assert.equal(P.formatMetric('valid_pairs', 1.5), '—');
  assert.equal(P.formatCentroid([null, 0]), '—');
  const metrics = Object.freeze(saliva21Fixture().cells[0].metrics);
  const before = structuredClone(metrics);
  P.objectMetricGroups(metrics, true, true);
  assert.deepEqual(metrics, before);
});

test('texture zero/one/null values, quality metadata and all Spanish labels render', async () => {
  const metrics = saliva21Fixture().cells[0].metrics;
  const html = await renderToString(createSSRApp(Metrics, { metrics, extended: true }));
  for (const [label, value] of [['Contraste', '0.0000'], ['Homogeneidad', '1.0000'],
    ['Energía', '1.0000'], ['Correlación', '—'], ['Entropía', '0.0000'],
    ['Ángulos válidos', '4'], ['Pares válidos', '123']]) {
    assert.match(html, new RegExp(`<dt[^>]*>${label}</dt><dd[^>]*>${value}</dd>`));
  }
  assert.match(html, /Computabilidad/);
  assert.doesNotMatch(html, /µm|NaN|undefined|>null<|Infinity/);
});

test('methodology uses payload values, handles false/missing and does not infer defaults', async () => {
  const json = saliva21Fixture();
  const first = await render(json);
  for (const text of ['GLCM', '32', '1 px', '0°, 45°, 90°, 135°', 'Promedio de ángulos válidos']) assert.ok(first.includes(text));
  assert.equal((first.match(/Metodología de textura/g) || []).length, 1);
  Object.assign(json.methodology.texture, { gray_levels: 16, distance_px: 2, angles_deg: [30, 60], symmetric: false, normalized: false });
  const rows = P.textureMethodologyRows(json.methodology.texture);
  const values = Object.fromEntries(rows.map(row => [row.key, row.value]));
  assert.equal(values.gray_levels, '16');
  assert.equal(values.distance_px, '2 px');
  assert.equal(values.angles_deg, '30°, 60°');
  assert.equal(values.symmetric, 'No');
  assert.equal(values.normalized, 'No');
  const html = await render(json);
  assert.match(html, /16<\/dd>/);
  assert.match(html, /2 px/);
  assert.doesNotMatch(html, /0°, 45°/);
  assert.ok(P.textureMethodologyRows({}).every(row => row.value === '—'));
  delete json.methodology;
  assert.match(await render(json), /Metodología no disponible/);
});

test('warnings preserve human labels, IDs, backend explanation and unknown escaped fallback', async () => {
  const json = saliva21Fixture();
  json.warnings.push({ code: '<future>', object_id: 0, message: '<script>alert(1)</script>' });
  const html = await render(json);
  for (const code of ['ECCENTRICITY_NOT_COMPUTABLE', 'TEXTURE_INSUFFICIENT_PAIRS', 'TEXTURE_CORRELATION_UNDEFINED']) {
    assert.ok(html.includes(P.warningLabel(code)));
    assert.ok(!html.includes(`>${code}<`));
  }
  assert.match(html, /Objeto: 0/);
  assert.match(html, /Objeto: 9/);
  assert.match(html, /Aviso futuro preservado/);
  assert.match(html, /Advertencia: FUTURE_WARNING/);
  assert.equal(P.warningLabel('constructor'), 'Advertencia: constructor');
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});

test('2.1 cells: one nucleus/MN, multinucleated, no MN, null distance and special groups', async () => {
  const json = saliva21Fixture();
  const before = structuredClone(json);
  const html = await render(json);
  for (const text of ['Región celular 1', 'Nucleo 2', 'Nucleo 5', 'Nucleo 6',
    'Binucleada', 'Sin micronucleos asociados.', 'Nucleo asociado: 2',
    'Distancia al núcleo', 'Fracción de área respecto al núcleo', 'Fracción de intensidad respecto al núcleo',
    'Nucleo 9', 'Micronucleo 10', 'Membranas candidatas: 1, 4']) assert.ok(html.includes(text), text);
  assert.match(html, /Distancia al núcleo<\/dt><dd[^>]*>—/);
  assert.match(html, /Fracción de intensidad respecto al núcleo<\/dt><dd[^>]*>0.0000/);
  assert.match(html, /50.00 %/); // Existing persisted summary display.
  assert.equal((html.match(/Textura GLCM/g) || []).length, 8);
  assert.deepEqual(json, before);
});

test('2.0 historical and legacy/BLOOD/unknown-schema fallbacks have no 2.1 sections', async () => {
  const oldHtml = await render(historical);
  assert.match(oldHtml, /100.00 px²/);
  assert.match(oldHtml, /morphometric-result/);
  assert.doesNotMatch(oldHtml, /Excentricidad|Textura GLCM|Desv. estándar|Metodología de textura/);
  for (const [sample_type, version] of [['SALIVA', '1.0'], ['SANGRE', '1.0'], ['SALIVA', '9.0']]) {
    const html = await render({ sample_type, version, schema_version: version,
      counts: { membrana: 2, nucleo: 1, micronucleo: 0 }, indices: {} });
    assert.match(html, /Conteos/);
    assert.doesNotMatch(html, /morphometric-result|Excentricidad|Textura GLCM|Desv. estándar/);
  }
});

test('full 2.1 rendering is independent of CURRENT/ALT provenance', async () => {
  const json = saliva21Fixture();
  const current = await renderToString(createSSRApp(Panel, propsFor(json)));
  const alt = await renderToString(createSSRApp(Panel, propsFor(json, 'ALT_CPSAM_MORPHOLOGICAL_V1')));
  assert.equal(alt, current);
});

// Real Vue reactive component wiring with a minimal host, not a browser/layout test.
function node(type, text = '') {
  return { type, text, children: [], props: {}, style: {}, dataset: {}, clientTop: 0,
    clientHeight: 500, scrollTop: 0, scrolls: [],
    addEventListener() {}, removeEventListener() {},
    getBoundingClientRect() { return { top: 0, bottom: 500, height: 500 }; },
    querySelectorAll() { return []; }, querySelector() { return null; },
    scrollTo(options) { this.scrolls.push(options); },
  };
}
const renderer = createRenderer({
  createElement: node, createText: text => node('#text', text), createComment: text => node('#comment', text),
  setText: (n, text) => { n.text = text; }, setElementText: (n, text) => { n.text = text; n.children = []; },
  parentNode: n => n.parent, nextSibling: n => n.parent?.children[n.parent.children.indexOf(n) + 1] || null,
  patchProp(n, key, old, value) { n.props[key] = value; if (key === 'data-membrane-id') n.dataset.membraneId = String(value); },
  insert(n, parent, anchor = null) {
    if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1);
    n.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    parent.children.splice(index < 0 ? parent.children.length : index, 0, n);
  },
  remove(n) { n.parent.children.splice(n.parent.children.indexOf(n), 1); },
});
function all(n, type) { return [...(n.type === type ? [n] : []), ...n.children.flatMap(child => all(child, type))]; }
function textOf(n) { return n.text + n.children.map(textOf).join(''); }
async function client(component) {
  const source = await readFile(new URL(`../src/components/characterization/${component.name}.vue`, import.meta.url), 'utf8');
  return { ...component, setup: component.name === 'SalivaMorphometricResult' ? () => ({ disclosureId: useId() }) : undefined,
    ssrRender: undefined, render: compile(parse(source).descriptor.template.content) };
}
const ClientMetrics = await client(Metrics), ClientOverlay = await client(Overlay), ClientMorph = await client(Morph);
ClientMorph.components = { SalivaObjectMetrics: ClientMetrics };
const ClientPanel = await client(Panel);
ClientPanel.components = { SalivaMorphometricResult: ClientMorph, CharacterizationEffectiveOverlay: ClientOverlay };
function componentIn(vnode, name) {
  if (vnode?.component?.type.name === name) return vnode.component.proxy;
  if (vnode?.component) return componentIn(vnode.component.subTree, name);
  for (const child of Array.isArray(vnode?.children) ? vnode.children : []) {
    const found = componentIn(child, name); if (found) return found;
  }
}

test('overlay ↔ cell selection, local scroll, disclosures and adding metrics preserve IDs/highlight', async t => {
  const previousWindow = globalThis.window;
  globalThis.window = { addEventListener() {}, removeEventListener() {} };
  const root = node('root');
  const json = reactive(saliva21Fixture());
  const vnode = h(ClientPanel, { ...propsFor(json), imageSrc: 'synthetic.png', effectiveSegmentation: effective21Fixture() });
  renderer.render(vnode, root);
  t.after(() => {
    renderer.render(null, root);
    if (previousWindow === undefined) delete globalThis.window; else globalThis.window = previousWindow;
  });
  const panel = vnode.component.proxy;
  const morph = panel.$refs.morphometricResult;
  const overlay = componentIn(vnode, 'CharacterizationEffectiveOverlay');
  overlay.naturalSize = { width: 100, height: 100 };
  overlay.renderedSize = { width: 100, height: 100 };
  await nextTick();
  const tableScroll = morph.$refs.cellsScroll;
  tableScroll.querySelectorAll = () => [{ dataset: { membraneId: '1' }, getBoundingClientRect: () => ({ top: 600, bottom: 640 }) }];
  const click = { stopPropagation() {}, preventDefault() {} };
  all(root, 'polygon').find(n => n.props['aria-label'] === 'Célula 1').props.onClick(click);
  await nextTick(); await nextTick();
  assert.equal(panel.selectedCellId, 1);
  assert.deepEqual(overlay.overlayPolygons.filter(p => p.selected).map(p => p.key), ['membrana-1-0', 'nucleo-2-1', 'micronucleo-3-2']);
  assert.equal(tableScroll.scrolls.length, 1);
  assert.equal(tableScroll.scrolls[0].top, 140);
  const row = all(root, 'tr').find(n => n.props['data-membrane-id'] === 4);
  row.props.onClick(click); await nextTick();
  assert.equal(panel.selectedCellId, 4);
  assert.deepEqual(overlay.overlayPolygons.filter(p => p.selected).map(p => p.key), ['membrana-4-3']);
  const buttons = all(root, 'button');
  const disclosure = buttons.find(n => textOf(n) === 'Consultar');
  assert.equal(disclosure.props.type, 'button');
  assert.equal(disclosure.props['aria-expanded'], false);
  disclosure.props.onClick(click); await nextTick();
  assert.equal(disclosure.props['aria-expanded'], true);
  assert.notEqual(all(root, 'tr').find(n => n.props.class === 'cell-detail-row').style.display, 'none');
  assert.ok(all(root, 'div').some(n => n.props.id === disclosure.props['aria-controls']));
  assert.equal(panel.selectedCellId, 4);
  panel.currentCharacterization.resultado_json.cells[1].metrics.texture.contrast = 45;
  await nextTick();
  assert.equal(panel.selectedCellId, 4);
  assert.ok(textOf(root).includes('45.0000'));
  assert.equal(overlay.overlayPolygons.find(p => p.key === 'membrana-4-3').selected, true);
  const method = all(root, 'button').find(n => textOf(n).trim() === 'Metodología de textura');
  method.props.onClick(click); await nextTick();
  assert.equal(method.props['aria-expanded'], true);
  assert.ok(all(root, 'div').some(n => n.props.id === method.props['aria-controls']));
  assert.ok(all(root, 'th').every(n => n.props.scope === 'col'));
  const cellButton = all(root, 'button').find(n => n.props['aria-pressed'] === true);
  cellButton.props.onClick(click); await nextTick();
  assert.equal(panel.selectedCellId, null);
});
