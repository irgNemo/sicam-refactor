import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { parse } from '@vue/compiler-sfc';
import { compile, createRenderer, createSSRApp, h, nextTick } from 'vue';
import { renderToString } from '@vue/server-renderer';

// Use the installed Vue/Vite toolchain and Node runner; no test dependencies.
const server = await createServer({
  root: fileURLToPath(new URL('../', import.meta.url)),
  configFile: false,
  plugins: [vuePlugin()],
  optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false, ws: false, watch: null },
  appType: 'custom',
});
// Vite/esbuild use unref'ed handles in middleware mode. Keep async module
// compilation alive until the Node test runner has completed every assertion.
const keepAlive = setInterval(() => {}, 1000);
after(async () => { clearInterval(keepAlive); await server.close(); });
const load = path => server.ssrLoadModule(`/src/${path}`);
const { SALIVA_STRATEGIES: S, segmentationStrategyLabel: label } = await load('domain/segmentationStrategies.js');
const { SAMPLE_TYPES: T } = await load('domain/segmentationTypes.js');
const { default: api } = await load('services/apiClient.js');
const { segmentarMuestra } = await load('services/segmentationService.js');
const { default: Panel } = await load('components/segmentation/SegmentationResultPanel.vue');
const { default: Control } = await load('components/segmentation/SalivaSegmentationControl.vue');
const { default: Main } = await load('components/MainContent.vue');
const { useSegmentationRevision } = await load('composables/useSegmentationRevision.js');
const { useSegmentationEditor } = await load('composables/useSegmentationEditor.js');
const viewport = await load('composables/useSegmentationViewport.js');
const presentation = await load('domain/characterizationPresentation.js');
const { default: Characterization } = await load('components/characterization/CharacterizationResultPanel.vue');

const response = (config, data) => ({ config, status: 200, statusText: 'OK', headers: {}, data });
const result = (id, strategy) => ({ id, segmentation_strategy: strategy, estado: 'COMPLETADO', tipo_muestra: T.SALIVA });
const panelProps = {
  segmentacionLoading: false, segmentacionObjetosCount: 0,
  activeSampleType: T.SALIVA, activeSampleTypeDisplayName: 'Saliva', isBloodSampleType: false,
  effectiveSegmentationLoading: false, showPendingDraftNotice: false,
  showValidatedRevisionNotice: false, isEditMode: false,
  historialSegmentacion: [], historialLoading: false, ultimoHistorialObjetosCount: 0,
  completedSegmentationResults: [],
};
const renderPanel = props => renderToString(createSSRApp(Panel, { ...panelProps, ...props }));

test('labels: CURRENT, ALT, unexpected null/missing/unknown SALIVA and deliberate BLOOD null', () => {
  assert.equal(label(T.SALIVA, S.CURRENT), 'Modelo SICAM');
  assert.equal(label(T.SALIVA, S.ALT), 'Cellpose-SAM alternativo');
  for (const value of [null, undefined, 'future-strategy']) assert.equal(label(T.SALIVA, value), 'Método no disponible');
  for (const value of [null, S.ALT]) assert.equal(label(T.BLOOD, value), null);
});

test('requests: explicit SALIVA default/CURRENT/ALT; BLOOD remains bodyless even with a SALIVA argument', async () => {
  const calls = [];
  api.defaults.adapter = async config => { calls.push(config); return response(config, {}); };
  await segmentarMuestra(1);
  await segmentarMuestra(1, T.SALIVA, S.CURRENT);
  await segmentarMuestra(1, T.SALIVA, S.ALT);
  await segmentarMuestra(2, T.BLOOD);
  await segmentarMuestra(2, T.BLOOD, S.ALT);
  assert.deepEqual(calls.slice(0, 3).map(c => JSON.parse(c.data)), [S.CURRENT, S.CURRENT, S.ALT].map(segmentation_strategy => ({ segmentation_strategy })));
  for (const call of calls.slice(0, 3)) assert.equal(call.url, '/api/muestras/1/segmentar/');
  for (const call of calls.slice(3)) {
    assert.equal(call.url, '/api/muestras-sangre/2/segmentar/');
    assert.equal(call.data, undefined);
  }
  assert.ok(calls.every(c => c.timeout === 0 && !c.signal), 'No frontend deadline/abort introduced');
});

// A minimal Vue host exercises reactive radio events without pretending to be a browser.
function hostNode(type, text = '') {
  return { type, text, children: [], props: {}, listeners: {},
    addEventListener(event, handler) { this.listeners[event] = handler; },
  };
}
const renderer = createRenderer({
  createElement: hostNode, createText: text => hostNode('#text', text),
  createComment: text => hostNode('#comment', text),
  setText: (node, text) => { node.text = text; },
  setElementText: (node, text) => { node.text = text; node.children = []; },
  parentNode: node => node.parent,
  nextSibling: node => node.parent?.children[node.parent.children.indexOf(node) + 1] || null,
  patchProp(node, key, oldValue, value) { node.props[key] = value; if (key === 'value') node.value = value; },
  insert(node, parent, anchor = null) {
    if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1);
    node.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    parent.children.splice(index < 0 ? parent.children.length : index, 0, node);
  },
  remove(node) { node.parent.children.splice(node.parent.children.indexOf(node), 1); },
});
const controlSource = await readFile(new URL('../src/components/segmentation/SalivaSegmentationControl.vue', import.meta.url), 'utf8');
// The Vite SSR wrapper's setup only registers CSS modules in SSR context.
// This Options API component has no source setup; omit that wrapper for the host render.
const ClientControl = { ...Control, setup: undefined, ssrRender: undefined,
  render: compile(parse(controlSource).descriptor.template.content) };
function findAll(node, type) {
  return [...(node.type === type ? [node] : []), ...node.children.flatMap(child => findAll(child, type))];
}

test('radio interaction CURRENT→ALT, execution lock, duplicate submission guard and sample reset', async () => {
  const root = hostNode('root');
  const calls = [];
  const mount = (key, loading = false) => renderer.render(h(ClientControl, {
    key, loading, buttonText: 'Segmentar', onRunSegmentation: value => calls.push(value),
  }), root);
  mount('SALIVA-1');
  let inputs = findAll(root, 'input');
  assert.equal(inputs.length, 2);
  assert.equal(inputs[0].checked, true);
  assert.equal(inputs[1].checked, false);
  const submit = () => findAll(root, 'form')[0].props.onSubmit({ preventDefault() {} });
  submit();
  inputs[1].listeners.change();
  await nextTick();
  assert.equal(inputs[1].checked, true);
  submit();
  assert.deepEqual(calls, [S.CURRENT, S.ALT]);
  mount('SALIVA-1', true);
  assert.equal(findAll(root, 'fieldset')[0].props.disabled, true);
  assert.equal(findAll(root, 'button')[0].props.disabled, true);
  submit();
  assert.equal(calls.length, 2);
  mount('SALIVA-2');
  inputs = findAll(root, 'input');
  assert.equal(inputs[0].checked, true);
  submit();
  assert.equal(calls[2], S.CURRENT);
  renderer.render(null, root);
});

test('SALIVA history keeps different strategies and backend provenance wins over selection default', async () => {
  const current = result(1, S.CURRENT), alt = result(2, S.ALT);
  const html = await renderPanel({
    completedSegmentationResults: [alt, current], historialSegmentacion: [alt, current],
    ultimoResultadoSegmentacion: alt, segmentacionMetadata: alt,
  });
  assert.match(html, /Resultado #2 · Cellpose-SAM alternativo/);
  assert.match(html, /Resultado #1 · Modelo SICAM/);
  assert.match(html, /<span[^>]*>Método<\/span><strong[^>]*>Cellpose-SAM alternativo<\/strong>/);
  assert.match(html, /Método: Cellpose-SAM alternativo/);
  assert.match(html, /<input checked[^>]*value="CURRENT_CUSTOM_V1"/);
  assert.equal((html.match(/type="radio"/g) || []).length, 2);
});

test('one historical result and unexpected null/unknown provenance render without technical placeholders', async () => {
  for (const strategy of [S.CURRENT, null, 'future-strategy']) {
    const item = result(1, strategy);
    const html = await renderPanel({ completedSegmentationResults: [item], ultimoResultadoSegmentacion: item });
    assert.ok(html.includes(`Método: ${label(T.SALIVA, strategy)}`));
    assert.doesNotMatch(html, /undefined|UNKNOWN|Método: null/);
  }
});

for (const source of ['AUTOMATICO', 'VALIDADA']) {
  for (const strategy of [S.CURRENT, S.ALT]) {
    test(`effective ${source} + ${strategy}, including an independent pending draft`, async () => {
      const effective = { fuente: source, segmentation_strategy: strategy, revision: source === 'VALIDADA' ? { numero_revision: 1 } : null };
      const display = Main.computed.effectiveSegmentationDisplay.call({ effectiveSegmentation: effective });
      const html = await renderPanel({ effectiveSegmentation: effective, effectiveSegmentationDisplay: display,
        showPendingDraftNotice: true, pendingDraftRevision: { numero_revision: 2, estado: 'BORRADOR' } });
      assert.ok(html.includes(`Método de segmentación: ${label(T.SALIVA, strategy)}`));
      assert.ok(html.includes(source === 'VALIDADA' ? 'Revisión #1 validada' : 'Automático'));
      assert.match(html, /Cambios guardados, aún no validados/);
      assert.doesNotMatch(html, /ALT validado|estrategia validada/);
    });
  }
}

test('BLOOD has no selector, method labels or strategy state; original long-running notice remains', async () => {
  const item = { ...result(3, null), tipo_muestra: T.BLOOD };
  const html = await renderPanel({ activeSampleType: T.BLOOD, activeSampleTypeDisplayName: 'Sangre', isBloodSampleType: true,
    segmentacionLoading: true, segmentacionMetadata: item, completedSegmentationResults: [item],
    ultimoResultadoSegmentacion: item, effectiveSegmentation: { segmentation_strategy: null }, effectiveSegmentationDisplay: 'Automático' });
  assert.doesNotMatch(html, /type="radio"|Método|Modelo SICAM|Cellpose-SAM|saliva-segmentation-control/);
  assert.match(html, /Segmentando muestra de sangre/);
  assert.equal(Panel.data, undefined);
});

function mainContext() {
  return {
    imagenSeleccionada: { id_muestra: 1 }, activeSampleType: T.SALIVA, caseId: 1,
    segmentacionLoading: false, segmentacionResultado: null, segmentacionError: '',
    isCurrentSample: () => true, syncOverlayLabelVisibility() {},
    async cargarHistorialSegmentacion() {}, emitSegmentationResultSelected() {},
    async loadEffectiveSegmentation() {}, async loadRevisionState() {}, $emit() {},
  };
}

test('Main execution keeps loading until completion, blocks duplicate POST and trusts response provenance', async () => {
  let release;
  const calls = [];
  api.defaults.adapter = config => {
    calls.push(config);
    return new Promise(resolve => { release = () => resolve(response(config, { resultado_segmentacion: result(5, S.CURRENT) })); });
  };
  const context = mainContext();
  const task = Main.methods.ejecutarSegmentacion.call(context, S.ALT);
  assert.equal(context.segmentacionLoading, true);
  await Main.methods.ejecutarSegmentacion.call(context, S.CURRENT);
  assert.equal(calls.length, 1);
  assert.equal(JSON.parse(calls[0].data).segmentation_strategy, S.ALT);
  release();
  await task;
  assert.equal(context.segmentacionLoading, false);
  assert.equal(context.segmentacionResultado.resultado_segmentacion.segmentation_strategy, S.CURRENT);
});

for (const status of [400, 502, 503, 504]) {
  test(`ALT error ${status} uses existing error path and never retries CURRENT`, async t => {
    const calls = [];
    api.defaults.adapter = async config => { calls.push(config); throw { response: { status, data: { error: `ALT error ${status}` } } }; };
    t.mock.method(console, 'error', () => {});
    const context = mainContext();
    await Main.methods.ejecutarSegmentacion.call(context, S.ALT);
    assert.equal(context.segmentacionError, `ALT error ${status}`);
    assert.equal(context.segmentacionLoading, false);
    assert.equal(context.segmentacionResultado, null);
    assert.equal(calls.length, 1);
    assert.equal(JSON.parse(calls[0].data).segmentation_strategy, S.ALT);
  });
}

test('revision loader retains parent ALT, ignores pending draft as effective, and rejects stale responses', async () => {
  const revision = useSegmentationRevision();
  const effective = { resultado_segmentacion_id: 2, fuente: 'VALIDADA', segmentation_strategy: S.ALT, revision: { numero_revision: 1 }, resultado: { objects: [] } };
  api.defaults.adapter = async config => response(config, config.url.endsWith('/efectivo/') ? effective : [
    { estado: 'BORRADOR', numero_revision: 2 }, { estado: 'VALIDADA', numero_revision: 1 },
  ]);
  await revision.loadEffectiveSegmentation(2);
  await revision.loadRevisionState(2);
  assert.deepEqual(revision.effectiveSegmentation.value, effective);
  assert.equal(revision.pendingDraftRevision.value.estado, 'BORRADOR');
  let release;
  api.defaults.adapter = config => new Promise(resolve => { release = () => resolve(response(config, effective)); });
  const task = revision.loadEffectiveSegmentation(2);
  revision.resetRevisionState();
  release();
  assert.equal(await task, null);
  assert.equal(revision.effectiveSegmentation.value, null);
});

test('editor regression: polygon load/selection, vertex move undo/redo, drawing, validation guard', () => {
  const editor = useSegmentationEditor();
  const object = { id: 1, label: 'membrana', geometry: { type: 'polygon', points: [[0, 0], [10, 0], [10, 10]] } };
  editor.loadRevisionSnapshot({ resultado_editado: { objects: [object] } });
  editor.selectObject('revision-1');
  assert.equal(editor.selectedObject.value.id, 1);
  assert.equal(editor.hasPendingDraftWork.value, false);
  editor.beginVertexDrag({ objectId: 1, vertexIndex: 0 }, {});
  editor.updateVertexDrag([1, 1]);
  editor.finishVertexDrag();
  assert.equal(editor.hasPendingDraftWork.value, true);
  editor.undoRevisionEdit();
  assert.deepEqual(editor.workingObjects.value[0].geometry.points[0], [0, 0]);
  editor.redoRevisionEdit();
  assert.deepEqual(editor.workingObjects.value[0].geometry.points[0], [1, 1]);
  editor.appendDraftPoint([20, 20]);
  editor.appendDraftPoint([30, 20]);
  assert.equal(editor.finishDraftPolygonEdit(), null);
  editor.appendDraftPoint([30, 30]);
  const drawn = editor.finishDraftPolygonEdit();
  assert.equal(drawn.provenance.origin, 'manual');
  assert.equal(editor.workingObjects.value.length, 2);
  editor.undoRevisionEdit();
  assert.equal(editor.workingObjects.value.length, 1);
  editor.redoRevisionEdit();
  assert.equal(editor.workingObjects.value.length, 2);
  assert.deepEqual(object.geometry.points[0], [0, 0], 'Source snapshot unchanged');
});

test('viewport pan/zoom/projection and strict SALIVA v2 vs legacy Characterization regression', () => {
  assert.deepEqual(viewport.calculateImagePanLimits({ width: 100, height: 50 }, 1, 0), { maxX: 0, maxY: 0 });
  assert.deepEqual(viewport.calculateImagePanLimits({ width: 100, height: 50 }, 2, 0), { maxX: 50, maxY: 25 });
  const containment = viewport.calculateOverlayContainment({ width: 100, height: 50 }, { width: 200, height: 200 });
  assert.deepEqual(viewport.scalePointToOverlay([10, 10], containment), [20, 70]);
  assert.equal(presentation.isSalivaMorphometricV2({ sample_type: T.SALIVA, schema_version: '2.0' }), true);
  for (const payload of [{ sample_type: T.SALIVA, schema_version: '1.0' }, { sample_type: T.BLOOD, schema_version: '1.0' }, null]) {
    assert.equal(presentation.isSalivaMorphometricV2(payload), false);
  }
});

test('revision validation reloads effective parent provenance and never sends strategy on editorial requests', async () => {
  const revision = useSegmentationRevision();
  const draft = { id_revision_segmentacion: 4, resultado_segmentacion: 2, numero_revision: 1, estado: 'BORRADOR' };
  const validated = { ...draft, estado: 'VALIDADA' };
  revision.setActiveRevision(draft);
  const calls = [];
  api.defaults.adapter = async config => {
    calls.push(config);
    const data = config.url.endsWith('/validar/') ? validated
      : config.url.endsWith('/efectivo/') ? { fuente: 'VALIDADA', revision: validated, segmentation_strategy: S.ALT }
      : [validated];
    return response(config, data);
  };
  await revision.validateActiveRevision(2);
  assert.equal(revision.activeRevision.value.estado, 'VALIDADA');
  assert.equal(revision.pendingDraftRevision.value, null);
  assert.equal(revision.effectiveSegmentation.value.segmentation_strategy, S.ALT);
  assert.equal(calls.filter(c => c.method === 'post').length, 1);
  assert.equal(calls[0].data, undefined);
  const editable = { activeRevision: draft, isDraftDirty: false, draftPolygonPoints: [],
    noEditorialInteractionInProgress: true, isValidatingRevision: false };
  assert.equal(Main.computed.validateRevisionBlockReason.call(editable), '');
  assert.match(Main.computed.validateRevisionBlockReason.call({ ...editable, isDraftDirty: true }), /Guarda los cambios/);
  assert.match(Main.computed.validateRevisionBlockReason.call({ ...editable, draftPolygonPoints: [[1, 1]] }), /máscara en construcción/);
});

test('Characterization renders SALIVA v1/v2 and BLOOD v1 independently of the parent strategy', async () => {
  for (const [sampleType, version] of [[T.SALIVA, '1.0'], [T.SALIVA, '2.0'], [T.BLOOD, '1.0']]) {
    const props = { sampleType, selectedSegmentationResult: result(1, S.CURRENT),
      currentCharacterization: { algorithm_version: version, resultado_json: {
        sample_type: sampleType, schema_version: version,
        counts: { membrana: 1, nucleo: 1, micronucleo: 0 }, cells: [],
      } }, characterizations: [] };
    const current = await renderToString(createSSRApp(Characterization, props));
    const alt = await renderToString(createSSRApp(Characterization, { ...props, selectedSegmentationResult: result(1, S.ALT) }));
    assert.equal(alt, current, 'Strategy does not branch Characterization presentation');
    assert.match(current, /Caracterizar/);
    assert.ok(current.includes(version));
    if (version === '1.0') assert.match(current, /Conteos/);
  }
});
