import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { parse } from '@vue/compiler-sfc';
import { compile, createRenderer, createSSRApp, h, nextTick, reactive } from 'vue';
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
const { replacementWarning, SALIVA_TARGET_OPTIONS, segmentationLoadingText } = await load('domain/segmentationTargets.js');
const { SAMPLE_TYPES: T } = await load('domain/segmentationTypes.js');
const { default: api } = await load('services/apiClient.js');
const { segmentarMuestra } = await load('services/segmentationService.js');
const { default: Panel } = await load('components/segmentation/SegmentationResultPanel.vue');
const { default: Control } = await load('components/segmentation/SalivaSegmentationControl.vue');
const { default: Main } = await load('components/MainContent.vue');
const { default: App } = await server.ssrLoadModule('/src/App.vue');
const { default: TopBar } = await load('components/TopBar.vue');
const { default: SideBar } = await load('components/SideBar.vue');
const { default: Layers } = await load('components/segmentation/OverlayLayersCard.vue');
const { patientDisplayName, patientInitials } = await load('domain/patientPresentation.js');
const { useSegmentationRevision } = await load('composables/useSegmentationRevision.js');
const { useSegmentationEditor } = await load('composables/useSegmentationEditor.js');
const viewport = await load('composables/useSegmentationViewport.js');
const presentation = await load('domain/characterizationPresentation.js');
const { default: Characterization } = await load('components/characterization/CharacterizationResultPanel.vue');

const { default: EditorToolbar } = await load('components/segmentation/SegmentationEditorToolbar.vue');
const toolbarSource = await readFile(new URL('../src/components/segmentation/SegmentationEditorToolbar.vue', import.meta.url), 'utf8');
const mainSource = await readFile(new URL('../src/components/MainContent.vue', import.meta.url), 'utf8');
const ClientToolbar = { ...EditorToolbar, setup: undefined, ssrRender: undefined,
  render: compile(parse(toolbarSource).descriptor.template.content) };
const workflowTemplate = mainSource.slice(mainSource.indexOf('<section\n                v-if="showRevisionActions"'), mainSource.indexOf('<SegmentationResultPanel'));


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
    get options() { return this.children.filter(child => child.type === 'option'); },
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
  assert.deepEqual(calls, [S.CURRENT, S.ALT].map(segmentation_strategy => ({ segmentation_strategy, target: 'ALL' })));
  mount('SALIVA-1', true);
  assert.equal(findAll(root, 'fieldset')[0].props.disabled, true);
  assert.equal(findAll(root, 'button')[0].props.disabled, true);
  submit();
  assert.equal(calls.length, 2);
  mount('SALIVA-2');
  inputs = findAll(root, 'input');
  assert.equal(inputs[0].checked, true);
  submit();
  assert.deepEqual(calls[2], { segmentation_strategy: S.CURRENT, target: 'ALL' });
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
  assert.match(html, /aria-label="Resultado actual"[\s\S]*?Método: Cellpose-SAM alternativo[\s\S]*?<\/section>/);
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

test('viewport pan/zoom/projection and SALIVA 2.0/2.1 vs legacy Characterization regression', () => {
  assert.deepEqual(viewport.calculateImagePanLimits({ width: 100, height: 50 }, 1, 0), { maxX: 0, maxY: 0 });
  assert.deepEqual(viewport.calculateImagePanLimits({ width: 100, height: 50 }, 2, 0), { maxX: 50, maxY: 25 });
  const containment = viewport.calculateOverlayContainment({ width: 100, height: 50 }, { width: 200, height: 200 });
  assert.deepEqual(viewport.scalePointToOverlay([10, 10], containment), [20, 70]);
  assert.equal(presentation.isSalivaMorphometricV2({ sample_type: T.SALIVA, schema_version: '2.0' }), true);
  assert.equal(presentation.isSalivaMorphometricV2({ sample_type: T.SALIVA, schema_version: '2.1' }), true);
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
  for (const [sampleType, version] of [[T.SALIVA, '1.0'], [T.SALIVA, '2.0'], [T.SALIVA, '2.1'], [T.BLOOD, '1.0']]) {
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
    else assert.match(current, /morphometric-result/);
  }
});

// A frozen pre-18D service result must still render after the additive upgrade.
test('historical 2.0 retains common fields while 2.1 adds presentation', async () => {
  const historical = JSON.parse(await readFile(new URL('../../Backend/api/test_data/characterization_saliva_2_0.json', import.meta.url), 'utf8'));
  const upgraded = structuredClone(historical);
  upgraded.version = upgraded.schema_version = '2.1';
  upgraded.cells[0].metrics.eccentricity = 0;
  upgraded.cells[0].metrics.std_gray_intensity = 0.2;
  upgraded.cells[0].metrics.texture = { contrast: 42, valid_angles: 4, valid_pairs: 20 };
  const render = json => renderToString(createSSRApp(Characterization, {
    sampleType: T.SALIVA, selectedSegmentationResult: result(1, S.CURRENT),
    currentCharacterization: { algorithm_version: json.version, resultado_json: json },
  }));
  const oldHtml = await render(historical);
  const newHtml = await render(upgraded);
  for (const value of ['100.00 px²', '40.00 px', '(5.00, 5.00) px', '0.7854']) {
    assert.ok(oldHtml.includes(value));
    assert.ok(newHtml.includes(value));
  }
  assert.doesNotMatch(oldHtml, /Excentricidad|Textura GLCM|Desv. estándar/);
  assert.match(newHtml, /Excentricidad/);
  assert.match(newHtml, /Textura GLCM/);
  assert.match(newHtml, /42.0000/);
  assert.doesNotMatch(newHtml, /eccentricity|std_gray_intensity/);
});

test('manual base has null strategy, honest presentation and editable zero membranes', async () => {
  const manual = { ...result(50, null), base_origin: 'MANUAL' };
  assert.equal(label(T.SALIVA, null, 'MANUAL'), 'Anotación manual');
  assert.equal(label(T.BLOOD, null, 'MANUAL'), null);
  const html = await renderPanel({ completedSegmentationResults: [manual], historialSegmentacion: [manual], ultimoResultadoSegmentacion: manual });
  assert.match(html, /Anotación manual/);
  assert.doesNotMatch(html, /Método no disponible/);
  assert.equal(Main.computed.effectiveSegmentationDisplay.call({ effectiveSegmentation: { fuente: 'MANUAL' } }), 'Anotación manual');
  const editor = useSegmentationEditor();
  const objects = ['nucleo', 'micronucleo'].map((label, i) => ({ id: i+1, label, geometry: { type: 'polygon', points: [[2,2],[8,2],[8,8],[2,8]] }, source: { raw_id: 1 }, provenance: { origin: 'manual', base_object_id: null } }));
  const original = JSON.stringify(objects);
  editor.loadRevisionSnapshot({ resultado_editado: { objects } });
  assert.equal(editor.workingSummary.value.counts_by_label.membrana, 0);
  for (const id of [1, 2]) {
    editor.selectObject(`revision-${id}`);
    assert.equal(editor.selectedObject.value.id, id);
    editor.beginVertexDrag({ objectId: id, vertexIndex: 0 }, {});
    editor.updateVertexDrag([3,2]); editor.finishVertexDrag();
    editor.undoRevisionEdit(); editor.redoRevisionEdit();
  }
  editor.clearSelection();
  editor.selectObject('revision-2');
  editor.deleteSelectedObjectEdit();
  assert.equal(editor.workingObjects.value.length, 1);
  editor.undoRevisionEdit(); editor.redoRevisionEdit(); editor.undoRevisionEdit();
  assert.equal(editor.workingObjects.value.length, 2);
  for (const point of [[0,0],[20,0],[20,20],[0,20]]) editor.appendDraftPoint(point);
  assert.equal(editor.finishDraftPolygonEdit().label, 'membrana');
  const snapshot = editor.buildEditableSnapshot({ version: '1.0', base_result_id: 50 });
  assert.equal(snapshot.objects.length, 3);
  assert.equal(snapshot.objects[0].source.raw_id, 1);
  assert.equal(snapshot.objects[0].provenance.origin, 'manual');
  assert.equal(JSON.stringify(objects), original);
});

test('pseudonymized patient initials and identified patient names', async () => {
  assert.equal(patientDisplayName({ identity_mode: 'PSEUDONYMIZED', initials: 'XYZ', nombre: '', apellido: '' }), 'XYZ');
  assert.equal(patientInitials({ identity_mode: 'PSEUDONYMIZED', initials: 'XYZ' }), 'XYZ');
  assert.equal(patientDisplayName({ nombre: 'Synthetic', apellido: 'Patient' }), 'Synthetic Patient');
  assert.equal(patientInitials({ nombre: 'Synthetic', apellido: 'Patient' }), 'SP');
  assert.equal(patientDisplayName(null), '');
});

// Sprint 18I: exercise the real request handler and real editor, with HTTP mocked.
const manualObjects = [
  { id: 8, label: 'nucleo', geometry: { type: 'polygon', points: [[1,1],[5,1],[5,5]] },
    source: { raw_id: 1 }, provenance: { origin: 'manual', base_object_id: null }, metadata: { untouched: true } },
  { id: 9, label: 'micronucleo', geometry: { type: 'polygon', points: [[6,6],[7,6],[7,7]] },
    source: { raw_id: 2 }, provenance: { origin: 'manual', base_object_id: null } },
];
function selectiveContext() {
  const editor = useSegmentationEditor();
  const draft = { id_revision_segmentacion: 10, resultado_segmentacion: 5, estado: 'BORRADOR',
    actualizado_en: '2026-10-03T00:00:00Z', resultado_editado: { objects: structuredClone(manualObjects) } };
  editor.loadRevisionSnapshot(draft);
  const context = { ...mainContext(), activeResultadoSegmentacionId: 5, activeRevision: draft,
    viewerMode: 'EDIT', editorTool: 'SELECT', pendingDraftRevision: draft,
    setActiveRevision(value) { this.activeRevision = value; },
    loadWorkingRevision: editor.loadRevisionSnapshot,
  };
  Object.defineProperty(context, 'hasPendingDraftWork', { get: () => editor.hasPendingDraftWork.value });
  return { context, editor, draft };
}
const sourceContext = { source_token: 'a'.repeat(64), source_kind: 'BORRADOR', revision_id: 10,
  revision_updated_at: '2026-10-03T00:00:00Z', summary: { total_objects: 2, counts_by_label: { nucleo: 1, micronucleo: 1, membrana: 0 } } };

test('18I selector exposes three targets, ALL default and target-specific loading', async () => {
  assert.deepEqual(SALIVA_TARGET_OPTIONS.map(o => o.value), ['MEMBRANES','NUCLEI_AND_MICRONUCLEI','ALL']);
  const root = hostNode('root'); const calls = [];
  renderer.render(h(ClientControl, { loading: false, buttonText: 'Segmentar', onRunSegmentation: value => calls.push(value) }), root);
  const select = findAll(root, 'select')[0];
  assert.equal(select.selectedIndex, 2);
  for (const option of select.options) option.selected = option.value === 'MEMBRANES';
  select.listeners.change(); await nextTick();
  findAll(root, 'form')[0].props.onSubmit({ preventDefault() {} });
  assert.deepEqual(calls, [{ segmentation_strategy: S.CURRENT, target: 'MEMBRANES' }]);
  assert.match(segmentationLoadingText('MEMBRANES'), /membranas/);
  assert.match(segmentationLoadingText('NUCLEI_AND_MICRONUCLEI'), /núcleos y micronúcleos/);
  renderer.render(null, root);
});

test('18I replacement warnings cover empty output, preserved categories and existing drafts', () => {
  assert.equal(replacementWarning('MEMBRANES', sourceContext.summary), '');
  assert.match(replacementWarning('MEMBRANES', sourceContext.summary, true), /BORRADOR actual/);
  const warning = replacementWarning('MEMBRANES', { counts_by_label: { membrana: 1 } });
  assert.match(warning, /reemplazará todas las membranas/); assert.match(warning, /puede ser vacío/);
  assert.match(warning, /núcleos y micronúcleos no se modificarán/);
  assert.match(replacementWarning('NUCLEI_AND_MICRONUCLEI', sourceContext.summary), /membranas no se modificarán/);
  assert.match(replacementWarning('ALL', sourceContext.summary), /todas las categorías/);
});

for (const target of ['MEMBRANES', 'NUCLEI_AND_MICRONUCLEI']) {
  test(`18I ${target} request loads backend draft, preserves returned objects, EDIT and clean undo stack`, async t => {
    t.mock.method(globalThis, 'confirm', () => true); // window shim below
    const { context, editor } = selectiveContext();
    editor.undoStack.value = [{ old: true }]; editor.redoStack.value = [{ old: true }];
    const calls = [];
    // Deliberately return only these objects: the frontend must not combine an automatic response.
    const merged = { ...context.activeRevision, actualizado_en: '2026-10-03T00:01:00Z',
      resultado_editado: { objects: structuredClone(manualObjects) } };
    api.defaults.adapter = async config => {
      calls.push(config);
      return response(config, config.method === 'get' ? sourceContext : {
        target, resultado_segmentacion: { id: 5 }, revision: merged, objetos: [{ tipo: 'membrana', id: 999 }],
      });
    };
    await Main.methods.ejecutarSegmentacion.call(context, { segmentation_strategy: S.ALT, target });
    assert.equal(calls.length, 2);
    assert.deepEqual(JSON.parse(calls[1].data), { segmentation_strategy: S.ALT, target,
      resultado_segmentacion_id: 5, source_token: sourceContext.source_token, confirm_replacement: true });
    assert.equal(context.viewerMode, 'EDIT'); assert.equal(context.editorTool, 'SELECT');
    assert.deepEqual(editor.workingObjects.value, manualObjects);
    assert.deepEqual(editor.undoStack.value, []); assert.deepEqual(editor.redoStack.value, []);
    assert.equal(editor.hasPendingDraftWork.value, false);
    assert.equal(context.activeRevision, merged); assert.equal(context.segmentacionLoading, false);
    assert.equal(context.segmentacionResultado, null);
  });
}

// No browser automation or real data: window.confirm is a local test shim only.
const priorWindow = globalThis.window;
const priorConfirm = globalThis.confirm;
globalThis.confirm = () => true;
globalThis.window = globalThis;
after(() => { globalThis.window = priorWindow; globalThis.confirm = priorConfirm; });

test('18I local unsaved edits and unfinished drawing block before any HTTP', async () => {
  const { context, editor } = selectiveContext();
  let calls = 0; api.defaults.adapter = async config => { calls++; return response(config, {}); };
  editor.isDraftDirty.value = true;
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES', segmentation_strategy: S.ALT });
  assert.equal(calls, 0); assert.match(context.segmentacionError, /Guarda o descarta/);
  editor.isDraftDirty.value = false; editor.appendDraftPoint([1, 1]);
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES', segmentation_strategy: S.ALT });
  assert.equal(calls, 0);
});

test('18I cancelled confirmation never sends POST and retains editor', async t => {
  t.mock.method(globalThis, 'confirm', () => false);
  const { context, editor } = selectiveContext(); const calls = [];
  api.defaults.adapter = async config => { calls.push(config); return response(config, sourceContext); };
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES', segmentation_strategy: S.ALT });
  assert.equal(calls.length, 1); assert.equal(calls[0].method, 'get');
  assert.deepEqual(editor.workingObjects.value, manualObjects); assert.equal(context.segmentacionLoading, false);
});

test('18I missing base and stale visible draft cannot execute', async () => {
  const { context } = selectiveContext(); let calls = 0;
  api.defaults.adapter = async config => { calls++; return response(config, { ...sourceContext, revision_updated_at: 'changed' }); };
  context.activeResultadoSegmentacionId = null;
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES' });
  assert.equal(calls, 0); assert.match(context.segmentacionError, /anotación existente/);
  context.activeResultadoSegmentacionId = 5;
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES' });
  assert.equal(calls, 1); assert.match(context.segmentacionError, /anotación cambió/);
});

test('18I failed/changed-source requests retain objects, undo stack and revision', async () => {
  for (const status of [409, 502, 503, 504]) {
    const { context, editor, draft } = selectiveContext(); editor.undoStack.value = [{ intact: true }];
    api.defaults.adapter = async config => {
      if (config.method === 'get') return response(config, sourceContext);
      throw { response: { status, data: { error: 'No aplicado' } } };
    };
    await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES', segmentation_strategy: S.ALT });
    assert.deepEqual(editor.workingObjects.value, manualObjects); assert.deepEqual(editor.undoStack.value, [{ intact: true }]);
    assert.equal(context.activeRevision, draft); assert.equal(context.segmentacionError, 'No aplicado');
    assert.equal(context.segmentacionLoading, false);
  }
});

test('18I empty selected category from backend remains empty and loading blocks duplicate execution', async () => {
  const { context, editor } = selectiveContext(); let release; let posts = 0;
  api.defaults.adapter = async config => {
    if (config.method === 'get') return response(config, sourceContext);
    posts++; return new Promise(resolve => { release = () => resolve(response(config, {
      resultado_segmentacion: { id: 5 }, revision: { ...context.activeRevision, resultado_editado: { objects: [] } },
    })); });
  };
  const task = Main.methods.ejecutarSegmentacion.call(context, { target: 'NUCLEI_AND_MICRONUCLEI', segmentation_strategy: S.CURRENT });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(context.segmentacionLoading, true);
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES' });
  assert.equal(posts, 1); release(); await task;
  assert.deepEqual(editor.workingObjects.value, []);
});

test('18I BLOOD ignores supplied targets and carries no SALIVA payload', async () => {
  const calls = []; api.defaults.adapter = async config => { calls.push(config); return response(config, {}); };
  await segmentarMuestra(1, T.BLOOD, S.ALT, { target: 'MEMBRANES' });
  assert.equal(calls[0].data, undefined);
  const html = await renderPanel({ activeSampleType: T.BLOOD, isBloodSampleType: true });
  assert.doesNotMatch(html, /Objetos a segmentar|MEMBRANES|NUCLEI_AND_MICRONUCLEI/);
});

test('18I mixed draft has neutral presentation', async () => {
  const html = await renderPanel({ isEditMode: true, effectiveSegmentation: { base_origin: 'MANUAL' },
    effectiveSegmentationDisplay: 'Anotación manual' });
  assert.match(html, /Borrador en edición/); assert.doesNotMatch(html, /Método de segmentación: Anotación manual/);
});

test('18I editor uses server-reserved ID and resets undo when loading merged snapshot', () => {
  const editor = useSegmentationEditor();
  editor.loadRevisionSnapshot({ resultado_editado: { objects: structuredClone(manualObjects) } });
  for (const point of [[2,2],[8,2],[8,8]]) editor.appendDraftPoint(point);
  const object = editor.finishDraftPolygonEdit(999);
  assert.equal(object.id, 999); assert.equal(object.provenance.origin, 'manual');
  editor.undoRevisionEdit(); editor.redoRevisionEdit();
  assert.equal(editor.workingObjects.value.at(-1).id, 999);
});

test('18I base with empty selected category submits without confirmation', async t => {
  let confirmations = 0; t.mock.method(globalThis, 'confirm', () => { confirmations++; return false; });
  const { context, editor } = selectiveContext(); context.activeRevision = null;
  const calls = [];
  api.defaults.adapter = async config => {
    calls.push(config);
    return response(config, config.method === 'get' ? { ...sourceContext, source_kind: 'MANUAL', revision_id: null,
      revision_updated_at: null } : { resultado_segmentacion: { id: 5 }, revision: {
        id_revision_segmentacion: 11, resultado_segmentacion: 5, estado: 'BORRADOR', resultado_editado: { objects: manualObjects },
      } });
  };
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'MEMBRANES', segmentation_strategy: S.ALT });
  assert.equal(confirmations, 0); assert.equal(calls.length, 2);
  assert.equal(JSON.parse(calls[1].data).confirm_replacement, false);
  assert.deepEqual(editor.workingObjects.value, manualObjects);
});

test('18I ALL with annotations requires confirmation before posting', async t => {
  t.mock.method(globalThis, 'confirm', () => false);
  const context = mainContext(); context.effectiveSegmentation = { resumen: sourceContext.summary };
  let requests = 0; api.defaults.adapter = async config => { requests++; return response(config, {}); };
  await Main.methods.ejecutarSegmentacion.call(context, { target: 'ALL', segmentation_strategy: S.CURRENT });
  assert.equal(requests, 0); assert.equal(context.segmentacionLoading, false);
});

test('18I saving a merged draft sends its exact version precondition', async () => {
  const revision = useSegmentationRevision();
  const draft = { id_revision_segmentacion: 10, resultado_segmentacion: 5, estado: 'BORRADOR',
    actualizado_en: sourceContext.revision_updated_at, resultado_editado: { objects: manualObjects } };
  revision.setActiveRevision(draft);
  let request;
  api.defaults.adapter = async config => { request = JSON.parse(config.data); return response(config, draft); };
  await revision.saveActiveDraft(draft.resultado_editado);
  assert.deepEqual(request, { resultado_editado: draft.resultado_editado, expected_updated_at: draft.actualizado_en });
});

test('18I finishing a SALIVA drawing reserves its ID on the backend before adding it', async () => {
  const { context, editor } = selectiveContext();
  for (const point of [[1,1],[2,1],[2,2]]) editor.appendDraftPoint(point);
  Object.defineProperty(context, 'draftPolygonPoints', { get: () => editor.draftPolygonPoints.value });
  context.activeRevisionId = 10; context.cancelDraftPointDrag = () => {};
  context.finishDraftPolygonEdit = editor.finishDraftPolygonEdit; context.showOverlayLabel = () => {};
  const calls = [];
  api.defaults.adapter = async config => { calls.push(config); return response(config, { id: 1001 }); };
  await Main.methods.finishDraftPolygon.call(context);
  assert.equal(calls[0].url, '/api/resultados-segmentacion/5/reserve-object-id/');
  assert.equal(editor.workingObjects.value.at(-1).id, 1001);
  assert.equal(context.reservingObjectId, false);
});

test('18Q layer controls preserve visibility events, colors and accessible labels', async () => {
  const source = await readFile(new URL('../src/components/segmentation/OverlayLayersCard.vue', import.meta.url), 'utf8');
  const ClientLayers = { ...Layers, setup: undefined, ssrRender: undefined,
    render: compile(parse(source).descriptor.template.content) };
  const labels = [
    { label: 'membrana', displayName: 'Membranas', stroke: '#11aa22', visible: true },
    { label: 'nucleo', displayName: 'Núcleos', stroke: '#2233bb', visible: true },
    { label: 'micronucleo', displayName: 'Micronúcleos', stroke: '#dd1122', visible: true },
  ];
  const root = hostNode('root');
  const calls = [];
  const mount = () => renderer.render(h(ClientLayers, {
    labels: labels.map(item => ({ ...item })),
    onChangeVisibility: (label, visible) => calls.push([label, visible]),
  }), root);
  mount();
  assert.equal(findAll(root, 'h3').length, 1);
  assert.equal(findAll(root, 'input').length, 3);
  for (const [index, label] of labels.entries()) {
    const wrapper = findAll(root, 'label')[index];
    assert.equal(findAll(wrapper, 'input')[0].props.type, 'checkbox');
    assert.ok(findAll(wrapper, 'span').some(node => node.text === label.displayName));
    assert.ok(findAll(wrapper, 'span').some(node => node.props.style?.color === label.stroke));
    for (const visible of [false, true]) {
      findAll(root, 'input')[index].props.onChange({ target: { checked: visible } });
      assert.deepEqual(calls.at(-1), [label.label, visible]);
      labels[index].visible = visible;
      mount();
      await nextTick();
      assert.equal(findAll(root, 'input')[index].props.checked, visible);
    }
  }
  renderer.render(h(ClientLayers, { labels: [] }), root);
  assert.equal(findAll(root, 'input').length, 0);
  renderer.render(null, root);
});

test('18Q has one layers card immediately after controls in the image column', async () => {
  const source = await readFile(new URL('../src/components/MainContent.vue', import.meta.url), 'utf8');
  const ast = parse(source).descriptor.template.ast;
  const matches = [];
  function visit(node, parent) {
    if (node.tag === 'OverlayLayersCard') matches.push({ node, parent });
    for (const child of node.children || []) visit(child, node);
  }
  visit(ast, null);
  assert.equal(matches.length, 1);
  const { node, parent } = matches[0];
  assert.ok(parent.props.some(prop => prop.name === 'class' && prop.value?.content === 'image-container'));
  const siblings = parent.children.filter(child => child.type === 1);
  assert.equal(siblings[siblings.indexOf(node) - 1].tag, 'SegmentationImageControls');
  assert.ok(node.props.some(prop => prop.name === 'bind' && prop.arg?.content === 'labels' && prop.exp?.content === 'overlayLabels'));
  assert.ok(node.props.some(prop => prop.name === 'on' && prop.arg?.content === 'change-visibility' && prop.exp?.content === 'setOverlayLabelVisibility'));
});

for (const section of ['analisis', 'unknown', 'segmentacion', 'caracterizacion', 'registro']) {
  test(`18Q-B restores ${section} safely without discarding patient/sample context`, () => {
    const previous = Object.getOwnPropertyDescriptor(globalThis, 'window');
    const stored = { version: 1, activeTab: section, patientId: 7, caseId: 8,
      sampleType: T.SALIVA, sampleId: 41, segmentationResultId: 5 };
    let saved = null;
    Object.defineProperty(globalThis, 'window', { configurable: true, value: {
      sessionStorage: {
        getItem(key) { assert.equal(key, 'sicam.uiContext.v1'); return JSON.stringify(stored); },
        setItem(key, value) { assert.equal(key, 'sicam.uiContext.v1'); saved = JSON.parse(value); },
        removeItem() { assert.fail('Valid legacy context must not be deleted'); },
      },
    } });
    try {
      const state = App.data();
      assert.equal(state.seccion, ['analisis', 'unknown'].includes(section) ? 'segmentacion' : section);
      assert.equal(state.selectedPatientId, 7);
      assert.equal(state.selectedCaseId, 8);
      assert.equal(state.selectedSampleRef.sampleId, 41);
      assert.equal(state.selectedSegmentationResultRef.resultadoId, 5);
      App.methods.persistUiContext.call({ ...state, activeSelectedSampleId: 41, activeSelectedSegmentationResultId: 5 });
      assert.deepEqual(saved, { ...stored, activeTab: state.seccion });
    } finally {
      if (previous) Object.defineProperty(globalThis, 'window', previous);
      else delete globalThis.window;
    }
  });
}

test('18Q-B real navigation retains pending-edit guard and rejects removed section', () => {
  for (const target of ['caracterizacion', 'registro']) {
    let confirmations = 0;
    let approved = false;
    const context = { seccion: 'segmentacion', $refs: { mainContent: {
      hasPendingDraftWork: true,
      confirmDiscardDraftChanges() { confirmations++; return approved; },
    } } };
    context.confirmPendingDraftNavigation = () => App.methods.confirmPendingDraftNavigation.call(context);
    App.methods.requestSectionChange.call(context, target);
    assert.equal(context.seccion, 'segmentacion');
    assert.equal(confirmations, 1);
    approved = true;
    App.methods.requestSectionChange.call(context, target);
    assert.equal(context.seccion, target);
    assert.equal(confirmations, 2);
    App.methods.requestSectionChange.call(context, 'analisis');
    assert.equal(context.seccion, target);
    App.methods.requestSectionChange.call(context, 'segmentacion');
    assert.equal(context.seccion, 'segmentacion');
  }
});

test('18Q-B TopBar shows only real sections; removed controls have no orphan handlers', async () => {
  for (const seccion of ['segmentacion', 'caracterizacion', 'registro']) {
    const html = await renderToString(createSSRApp(TopBar, { seccion }));
    assert.equal((html.match(/<button/g) || []).length, 3);
    for (const title of ['Segmentación', 'Caracterización', 'Registro']) assert.ok(html.includes(title));
    for (const removed of ['Análisis', 'Notificaciones', 'Configuración', 'notification-dot', '🔔', '⚙']) assert.ok(!html.includes(removed));
  }
  assert.equal(SideBar.props.showAnalysisButton, undefined);
  assert.equal(SideBar.methods.verAnalisis, undefined);
  for (const [file, removed] of [
    ['MainContent.vue', ['Exportar CSV', 'Generar PDF', 'header-actions']],
    ['SideBar.vue', ['Ver Análisis Completo', 'showAnalysisButton', 'verAnalisis']],
  ]) {
    const source = await readFile(new URL(`../src/components/${file}`, import.meta.url), 'utf8');
    for (const value of removed) assert.ok(!source.includes(value));
  }
});

// 18Q-C: presentation stays independent from future execution settings.
const currentSection = html => html.match(/<section[^>]*aria-label="Resultado actual"[\s\S]*?<\/section>/)[0];
const validatedPanel = {
  effectiveSegmentation: { fuente: 'VALIDADA', base_origin: 'MANUAL', segmentation_strategy: null,
    revision: { numero_revision: 3, validado_en: '2026-10-01T10:00:00Z' } },
  effectiveSegmentationDisplay: 'Revisión #3 validada',
  showValidatedRevisionNotice: true,
  latestValidatedRevision: { numero_revision: 3, validado_en: '2026-10-01T10:00:00Z' },
};

test('18Q-C effective VALIDADA consolidates revision, validation date and manual base exactly once', async () => {
  const base = { ...result(7, null), base_origin: 'MANUAL', creado_en: '2026-09-01T10:00:00Z' };
  const html = await renderPanel({ ...validatedPanel, completedSegmentationResults: [base],
    ultimoResultadoSegmentacion: base, historialSegmentacion: [base] });
  const current = currentSection(html);
  assert.equal((html.match(/Revisión #3/g) || []).length, 1);
  assert.equal((html.match(/Validada el/g) || []).length, 1);
  assert.equal((current.match(/Anotación manual/g) || []).length, 1);
  assert.doesNotMatch(current, /Resultado mostrado = resultado efectivo/);
  assert.match(current, /Tipo: SALIVA/);
  assert.match(current, /Origen: Anotación manual/);
  assert.doesNotMatch(current, /objetos en la base/);
  assert.match(current, /Resultado #7/);
  assert.match(html, /La última segmentación es el resultado seleccionado/);
  assert.deepEqual([...html.matchAll(/aria-label="(Segmentación|Resultado actual|Historial)"/g)].map(m => m[1]),
    ['Segmentación', 'Resultado actual', 'Historial']);
});

test('18Q-C edited BORRADOR is explicit and separate from effective VALIDADA', async () => {
  const current = currentSection(await renderPanel({ ...validatedPanel, isEditMode: true,
    activeRevision: { numero_revision: 4, estado: 'BORRADOR' } }));
  assert.match(current, /Borrador en edición[\s\S]*Revisión #4/);
  assert.match(current, /BORRADOR · No efectivo/);
  assert.match(current, /Resultado efectivo: Revisión #3 validada/);
  assert.match(current, /Origen de la base: Anotación manual/);
  assert.doesNotMatch(current, /Resultado mostrado = resultado efectivo/);
  assert.equal((current.match(/Revisión #3/g) || []).length, 1);
  assert.equal((current.match(/Revisión #4/g) || []).length, 1);
});

test('18Q-C manual base is not labeled automatic or assigned a model', async () => {
  const current = currentSection(await renderPanel({
    effectiveSegmentation: { fuente: 'MANUAL', base_origin: 'MANUAL', segmentation_strategy: null },
    effectiveSegmentationDisplay: 'Anotación manual',
  }));
  assert.equal((current.match(/Anotación manual/g) || []).length, 1);
  assert.doesNotMatch(current, /Automático|Modelo SICAM|Cellpose|Método no disponible/);
});

test('18Q-C history failure retains available selection; loading and errors remain visible', async () => {
  const html = await renderPanel({ completedSegmentationResults: [result(2, S.ALT), result(1, S.CURRENT)],
    historialError: 'Error de historial', segmentacionError: 'Error de ejecución', effectiveSegmentationError: 'Error de effective' });
  for (const text of ['Error de historial', 'Error de ejecución', 'Error de effective', 'Resultado #1 · Modelo SICAM']) assert.ok(html.includes(text));
  assert.match(html, /<select/);
  const loading = await renderPanel({ historialLoading: true, effectiveSegmentationLoading: true });
  assert.match(loading, /Cargando historial/);
  assert.match(loading, /Cargando resultado mostrado/);
});

const panelSource = await readFile(new URL('../src/components/segmentation/SegmentationResultPanel.vue', import.meta.url), 'utf8');
const ClientPanel = { ...Panel, setup: undefined, ssrRender: undefined,
  components: { SalivaSegmentationControl: ClientControl },
  render: compile(parse(panelSource).descriptor.template.content) };

test('18Q-C continue, history selection and SALIVA/BLOOD execution events survive regrouping', () => {
  const root = hostNode('root');
  const runs = [], selections = [];
  let continued = 0;
  renderer.render(h(ClientPanel, { ...panelProps, ...validatedPanel,
    completedSegmentationResults: [result(2, S.ALT), result(1, S.CURRENT)], selectedSegmentationResultId: 2,
    showPendingDraftNotice: true, pendingDraftRevision: { numero_revision: 4, estado: 'BORRADOR' },
    onContinueEdit: () => continued++, onChangeSegmentationResult: value => selections.push(value),
    onRunSegmentation: value => runs.push(value),
  }), root);
  findAll(root, 'button').find(button => button.text === 'Continuar edición').props.onClick();
  const selector = findAll(root, 'select').find(select => select.props.onChange);
  selector.props.onChange({ target: { value: '1' } });
  findAll(root, 'form')[0].props.onSubmit({ preventDefault() {} });
  assert.equal(continued, 1);
  assert.deepEqual(selections, ['1']);
  assert.deepEqual(runs, [{ segmentation_strategy: S.CURRENT, target: 'ALL' }]);
  renderer.render(h(ClientPanel, { ...panelProps, activeSampleType: T.BLOOD, isBloodSampleType: true,
    onRunSegmentation: value => runs.push(value) }), root);
  findAll(root, 'button')[0].props.onClick();
  assert.equal(runs.length, 2);
  assert.equal(runs[1], undefined);
  renderer.render(null, root);
});


test('18Q-D toolbar tools, drawing types and undo/redo preserve events and availability', async () => {
  const root = hostNode('root'), events = [];
  const base = { viewerMode: 'EDIT', isEditMode: true, revisionLoading: false, isDraftDirty: true,
    activeRevision: { numero_revision: 8, estado: 'BORRADOR' }, editorTool: 'DRAW', canUndo: true, canRedo: false,
    drawingLabel: 'membrana', drawingLabels: Main.computed.editableDrawingLabels.call({
      activeSegmentationConfig: { labels: [
        { label: 'membrana', displayName: 'Membranas', editable: true },
        { label: 'nucleo', displayName: 'Núcleos', editable: true },
        { label: 'micronucleo', displayName: 'Micronúcleos', editable: true },
      ] } }),
    onUndo: () => events.push('undo'), onRedo: () => events.push('redo'),
    onChangeEditorTool: value => events.push(value), onChangeDrawingLabel: value => events.push(value) };
  const mount = extra => renderer.render(h(ClientToolbar, { ...base, ...extra }), root);
  const button = text => findAll(root, 'button').find(node => node.text.trim() === text);
  mount();
  assert.equal(button('Dibujar').props['aria-pressed'], true);
  assert.equal(button('Membranas').props['aria-pressed'], true);
  assert.equal(button('Núcleos').props['aria-pressed'], false);
  assert.equal(button('Deshacer').props.disabled, false);
  assert.equal(button('Rehacer').props.disabled, true);
  button('Mover vista').props.onClick(); button('Deshacer').props.onClick(); button('Núcleos').props.onClick();
  assert.deepEqual(events, ['PAN', 'undo', 'nucleo']);
  mount({ editorTool: 'PAN', canUndo: false, canRedo: true });
  assert.equal(button('Mover vista').props['aria-pressed'], true);
  assert.equal(button('Deshacer').props.disabled, true);
  button('Rehacer').props.onClick(); assert.equal(events.at(-1), 'redo');
  assert.equal(button('Membranas'), undefined);
  mount({ drawingDisabled: true }); assert.equal(button('Membranas').props.disabled, true);
  const html = await renderToString(createSSRApp(EditorToolbar, base));
  assert.match(html, /Revisión #8 · BORRADOR/);
  assert.doesNotMatch(html, /Guardar borrador|Validar revisión/);
  renderer.render(null, root);
});

test('18Q-D object context and revision workflow remain separate with existing IDs and handlers', async () => {
  const start = mainSource.indexOf('<div v-if="selectedObject" class="selected-object-grid">');
  const end = mainSource.indexOf('<div\n                    v-if="editorTool', start);
  const template = mainSource.slice(start, end);
  const renderContext = selectedObject => renderToString(createSSRApp({
    data: () => ({ selectedObject, editorTool: 'SELECT', selectedVertexIndex: null }),
    methods: { overlayLabelDisplayName: () => 'Membranas', provenanceDisplayName: () => 'Manual' },
    render: compile(template),
  }));
  assert.match(await renderContext({ id: 105, label: 'membrana', provenance: { origin: 'manual' } }), /#105/);
  assert.match(await renderContext({ id: 105, label: 'membrana' }), /Membranas/);
  assert.match(await renderContext(null), /Ninguno[\s\S]*Seleccione una máscara para editarla/);
  const context = mainSource.slice(mainSource.indexOf('class="selected-object-panel"'), mainSource.indexOf(workflowTemplate));
  assert.doesNotMatch(context, /Guardar borrador|Validar revisión|Deshacer|Rehacer/);
  for (const handler of ['deleteSelectedObject', 'deleteSelectedVertex', "setVertexEditMode('MOVE')", "setVertexEditMode('INSERT')"])
    assert.ok(context.includes(handler));
  assert.match(workflowTemplate, /BORRADOR · No efectivo/);
  assert.match(workflowTemplate, /@click="confirmAndValidateRevision"/);
});

for (const fail of [false, true]) {
  test(`18Q-D save: idle hover, concurrent click guard, ${fail ? 'error/retry' : 'success'} recovery`, async () => {
    const revision = useSegmentationRevision();
    const draft = { id_revision_segmentacion: 10, resultado_segmentacion: 5, numero_revision: 2,
      estado: 'BORRADOR', actualizado_en: '2026-10-01T10:00:00Z', resultado_editado: { objects: manualObjects } };
    revision.setActiveRevision(draft);
    let release, requests = 0, payload;
    api.defaults.adapter = config => { requests++; payload = JSON.parse(config.data); return new Promise((resolve, reject) => {
      release = () => fail ? reject({ response: { data: { error: 'Conflicto simulado' } } }) : resolve(response(config, draft));
    }); };
    const ctx = reactive({ ...revision, showRevisionActions: true, segmentacionLoading: false, reservingObjectId: false,
      isEditMode: true, isDraftDirty: true, draftPolygonPoints: [], draftPointDrag: null, vertexDrag: null,
      selectedObjectKey: null, isDrawTool: false, validateRevisionBlockReason: '', canValidateRevision: false,
      get canSaveDraft() { return Main.computed.canSaveDraft.call(this); },
      buildEditableSnapshot: value => value,
      loadWorkingRevision() { this.isDraftDirty = false; },
      saveDraft: () => Main.methods.saveDraft.call(ctx), confirmAndValidateRevision() {},
    });
    const root = hostNode('root');
    renderer.render(h({ setup: () => ctx, render: compile(workflowTemplate) }), root);
    const saveButton = () => findAll(root, 'button').find(node => node.props.class.includes('save-draft-btn'));
    assert.equal(saveButton().props.disabled, false);
    assert.equal(saveButton().props['aria-busy'], false);
    assert.doesNotMatch(saveButton().props.class, /is-saving/);
    assert.ok(!Object.keys(saveButton().props).some(key => /mouse|pointer/i.test(key)), 'Hover has no request handler');
    assert.equal(requests, 0);
    const first = saveButton().props.onClick();
    await new Promise(resolve => setImmediate(resolve));
    await nextTick();
    assert.equal(saveButton().props.disabled, true);
    assert.equal(saveButton().props['aria-busy'], true);
    assert.match(saveButton().text, /Guardando/);
    await saveButton().props.onClick(); assert.equal(requests, 1);
    assert.deepEqual(payload, { resultado_editado: draft.resultado_editado, expected_updated_at: draft.actualizado_en });
    release(); await first; await nextTick();
    assert.equal(ctx.isSavingDraft, false);
    assert.equal(saveButton().props['aria-busy'], false);
    assert.doesNotMatch(saveButton().props.class, /is-saving/);
    assert.equal(saveButton().text, 'Guardar borrador');
    assert.equal(saveButton().props.disabled, !fail);
    assert.equal(ctx.saveDraftError, fail ? 'Conflicto simulado' : '');
    assert.match(mainSource, /\.save-draft-btn:disabled\s*\{\s*cursor: not-allowed/);
    assert.match(mainSource, /\.save-draft-btn\.is-saving\s*\{\s*cursor: progress/);
    renderer.render(null, root);
  });
}

test('18Q-D first membrane updates working counts and visible layers without reload, preserving N/MN', async () => {
  const { context, editor } = selectiveContext();
  Object.defineProperty(context, 'draftPolygonPoints', { get: () => editor.draftPolygonPoints.value });
  context.activeRevisionId = 10;
  context.cancelDraftPointDrag = () => {};
  context.finishDraftPolygonEdit = editor.finishDraftPolygonEdit;
  context.overlayLabelVisibility = { membrana: false };
  context.showOverlayLabel = Main.methods.showOverlayLabel;
  const overlayContext = { get activeOverlayObjects() { return editor.workingObjects.value; },
    overlayObjectKey: object => String(object.id), scalePolygonPoints: points => points,
    get overlayDrawableObjects() { return Main.computed.overlayDrawableObjects.call(this); },
    get overlayLabelNames() { return Main.computed.overlayLabelNames.call(this); },
    get overlayLabelVisibility() { return context.overlayLabelVisibility; },
    overlayColorForLabel: () => ({ stroke: '#000', fill: '#fff' }), overlayLabelDisplayName: label => label,
  };
  assert.deepEqual(overlayContext.overlayLabelNames, ['micronucleo', 'nucleo']);
  assert.equal(editor.workingSummary.value.counts_by_label.membrana, 0);
  for (const point of [[0,0],[10,0],[10,10]]) editor.appendDraftPoint(point);
  api.defaults.adapter = async config => response(config, { id: 1001 });
  await Main.methods.finishDraftPolygon.call(context);
  assert.deepEqual(editor.workingObjects.value.slice(0, 2), manualObjects);
  assert.deepEqual(editor.workingSummary.value, { counts_by_label: { membrana: 1, nucleo: 1, micronucleo: 1 }, total_objects: 3 });
  const layers = Main.computed.overlayLabels.call(overlayContext);
  assert.deepEqual(layers.map(layer => layer.label), ['membrana', 'micronucleo', 'nucleo']);
  assert.equal(layers[0].visible, true); assert.equal(layers[0].count, 1);
  editor.undoRevisionEdit(); assert.equal(editor.workingSummary.value.counts_by_label.membrana, 0);
  editor.redoRevisionEdit(); assert.equal(editor.workingSummary.value.counts_by_label.membrana, 1);
});
