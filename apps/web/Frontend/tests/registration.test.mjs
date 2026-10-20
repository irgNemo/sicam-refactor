import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { createSSRApp, reactive } from 'vue';
import { renderToString } from '@vue/server-renderer';

const server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false,
  plugins: [vuePlugin()], optimizeDeps: { noDiscovery: true, include: [] },
  server: { middlewareMode: true, hmr: false, ws: false, watch: null }, appType: 'custom' });
const keepAlive = setInterval(() => {}, 1000);
after(async () => { clearInterval(keepAlive); await server.close(); });
const { default: View } = await server.ssrLoadModule('/src/views/RegistroView.vue');
const { default: App } = await server.ssrLoadModule('/src/App.vue');
const { default: api } = await server.ssrLoadModule('/src/services/apiClient.js');
const { registrationErrorMessage, registrationFieldErrors } = await server.ssrLoadModule('/src/services/registrationErrors.js');
const source = await readFile(new URL('../src/views/RegistroView.vue', import.meta.url), 'utf8');
const ok = (config, data) => ({ config, status: 200, statusText: 'OK', headers: {}, data });
const invalid = data => ({ response: { status: 400, data } });
const turn = () => new Promise(resolve => setImmediate(resolve));
function context() {
  const ctx = reactive({ ...View.data(), $refs: { fileInput: { value: '' } }, notices: [] });
  for (const [name, method] of Object.entries(View.methods)) ctx[name] = method.bind(ctx);
  for (const [name, getter] of Object.entries(View.computed)) Object.defineProperty(ctx, name, { get: () => getter.call(ctx) });
  ctx.mostrarNotificacion = (message, type) => ctx.notices.push({ message, type });
  return ctx;
}
function files(ctx, t, names = ['a.png', 'b.tif']) {
  const revoked = []; let index = 0;
  t.mock.method(URL, 'createObjectURL', () => `blob:synthetic-${++index}`);
  t.mock.method(URL, 'revokeObjectURL', url => revoked.push(url));
  ctx.formImagenes.paciente = 1; ctx.formImagenes.caso = 2; ctx.formImagenes.analisis = 3;
  ctx.onFileChange({ target: { files: names.map(name => new File(['synthetic'], name, { type: 'image/png' })) } });
  return revoked;
}
function deferred() {
  const calls = [];
  api.defaults.adapter = config => new Promise((resolve, reject) => calls.push({ config, resolve: data => resolve(ok(config, data)), reject }));
  return calls;
}
function mockWindow(t, value) {
  const before = globalThis.window;
  globalThis.window = value;
  t.after(() => { if (before === undefined) delete globalThis.window; else globalThis.window = before; });
}

test('patient success: payload, duplicate guard, ID, list refresh and clean state', async () => {
  const c = context(); c.formPaciente = { nombre: 'Test', apellido: 'Fixture', identificacion: 'T1', fecha_nacimiento: '2000-01-01', email: '', telefono: '' };
  const payload = { ...c.formPaciente }, calls = deferred();
  const first = c.crearPaciente(); await turn(); await c.crearPaciente();
  assert.equal(calls.length, 1); assert.equal(c.isCreatingPatient, true);
  assert.deepEqual(JSON.parse(calls[0].config.data), payload);
  calls[0].resolve({ id_paciente: 7 }); await turn();
  assert.equal(calls[1].config.method, 'get'); calls[1].resolve([{ id_paciente: 7 }]); await first;
  assert.equal(c.newlyCreatedPatientId, 7); assert.equal(c.formPaciente.nombre, '');
  assert.equal(c.pacientes[0].id_paciente, 7); assert.equal(c.isCreatingPatient, false); assert.equal(c.hasUnsavedWork, false);
});

test('patient duplicate ID error keeps fields, explains validation and restores loading', async () => {
  const c = context(); c.formPaciente.identificacion = 'duplicate';
  api.defaults.adapter = async () => { throw invalid({ identificacion: ['Ya existe.'], email: ['No válido.'], non_field_errors: ['Identidad inválida.'] }); };
  await c.crearPaciente(); assert.equal(c.isCreatingPatient, false); assert.equal(c.formPaciente.identificacion, 'duplicate');
  assert.match(c.notices.at(-1).message, /Identificación: Ya existe/); assert.match(c.notices.at(-1).message, /Email: No válido/);
  assert.match(c.notices.at(-1).message, /Identidad inválida/);
  c.limpiarFormularioActivo(); assert.equal(c.hasUnsavedWork, false);
});

test('error formatter excludes internal errors and unknown fields and limits length', () => {
  for (const error of [{ response: { status: 500, data: { nombre: ['Traceback'] } } }, invalid({ traceback: ['secret'] }), invalid('<html>internal</html>')])
    assert.equal(registrationErrorMessage(error, 'Error'), 'Error');
  assert.ok(registrationErrorMessage(invalid({ titulo: ['x'.repeat(5000)] }), 'Error').length < 700);
  assert.match(registrationErrorMessage(invalid({ id_caso_fk: ['Incompatible'] }), 'Error'), /Caso: Incompatible/);
});

for (const withAnalysis of [false, true]) test(`case with analysis=${withAnalysis}: one request and duplicate guard`, async () => {
  const c = context(); c.vistaActiva = 'caso'; c.formCaso = { paciente: 1, titulo: 'Test', descripcion: 'note', crear_analisis: withAnalysis };
  const calls = deferred(), first = c.crearCaso(); await turn(); await c.crearCaso();
  assert.equal(calls.length, 1); assert.equal(c.isCreatingCase, true);
  assert.equal(calls[0].config.url, withAnalysis ? '/api/casos/crear-con-analisis/' : '/api/casos/');
  assert.deepEqual(JSON.parse(calls[0].config.data), { paciente: 1, titulo: 'Test', descripcion: 'note' });
  calls[0].resolve(withAnalysis ? { caso: { id_caso: 8 }, analisis: { id_analisis: 9 } } : { id_caso: 8 }); await first;
  assert.equal(c.isCreatingCase, false); assert.equal(c.newlyCreatedCaseId, 8);
  assert.equal(c.newlyCreatedAnalysisId, withAnalysis ? 9 : null); assert.equal(c.vistaActiva, 'caso'); assert.equal(c.hasUnsavedWork, false);
});

for (const field of ['titulo', 'id_caso_fk']) test(`transaction error ${field}: no compensation or second request`, async () => {
  const c = context(); c.formCaso = { paciente: 1, titulo: 'Test', descripcion: '', crear_analisis: true };
  let n = 0; api.defaults.adapter = async config => { n++; assert.equal(config.url, '/api/casos/crear-con-analisis/'); throw invalid({ [field]: ['Rechazado'] }); };
  await c.crearCaso(); assert.equal(n, 1); assert.equal(c.isCreatingCase, false); assert.equal(c.newlyCreatedCaseId, null);
  assert.equal(c.formCaso.titulo, 'Test'); assert.match(c.notices.at(-1).message, /Rechazado/);
});

test('patient change immediately clears children and previews; late response cannot replace current options', async t => {
  const c = context(), revoked = files(c, t); c.casosDisponibles = [{ id_caso: 2 }]; c.analisisDisponibles = [{ id_analisis: 3 }];
  const calls = deferred(), first = c.cargarCasosPaciente();
  assert.equal(c.formImagenes.caso, ''); assert.equal(c.formImagenes.analisis, '');
  assert.deepEqual(c.casosDisponibles, []); assert.deepEqual(c.analisisDisponibles, []); assert.equal(revoked.length, 2);
  assert.match(c.notices[0].message, /reinició/);
  await turn(); c.formImagenes.paciente = 9; const second = c.cargarCasosPaciente(); await turn();
  calls[1].resolve([{ id_caso: 90 }]); await second; calls[0].resolve([{ id_caso: 10 }]); await first;
  assert.equal(c.casosDisponibles[0].id_caso, 90); assert.equal(c.isLoadingCases, false);
  c.formImagenes.paciente = ''; await c.cargarCasosPaciente(); assert.deepEqual(c.casosDisponibles, []);
});

test('case change immediately clears analyses; stale error cannot overwrite new response', async () => {
  const c = context(); c.formImagenes.caso = 1; c.formImagenes.analisis = 11; c.analisisDisponibles = [{ id_analisis: 11 }];
  const calls = deferred(), first = c.cargarAnalisisCaso(); assert.equal(c.formImagenes.analisis, ''); assert.deepEqual(c.analisisDisponibles, []);
  await turn(); c.formImagenes.caso = 2; const second = c.cargarAnalisisCaso(); await turn();
  calls[1].resolve([{ id_analisis: 22 }]); await second; calls[0].reject(new Error('old')); await first;
  assert.equal(c.analisisDisponibles[0].id_analisis, 22); assert.equal(c.notices.length, 0);
  c.formImagenes.caso = ''; await c.cargarAnalisisCaso(); assert.deepEqual(c.analisisDisponibles, []);
});

for (const kind of ['Cases', 'Analyses']) test(`load ${kind} error leaves children clear, visible error, retry available`, async () => {
  const c = context(); c.formImagenes.paciente = 1; c.formImagenes.caso = 2; c.formImagenes.analisis = 3;
  api.defaults.adapter = async () => { throw new Error('network'); };
  const method = kind === 'Cases' ? 'cargarCasosPaciente' : 'cargarAnalisisCaso';
  await c[method](); assert.equal(c.formImagenes.analisis, ''); assert.equal(c[`isLoading${kind}`], false); assert.match(c.notices.at(-1).message, /reintentar/);
  api.defaults.adapter = async config => ok(config, []); await c[method](); assert.equal(c[kind === 'Cases' ? 'casesLoadError' : 'analysesLoadError'], false);
});

test('clearing patient also invalidates pending analysis response', async () => {
  const c = context(); c.formImagenes.caso = 2; const calls = deferred(), first = c.cargarAnalisisCaso(); await turn();
  c.formImagenes.paciente = ''; await c.cargarCasosPaciente(); calls[0].resolve([{ id_analisis: 3 }]); await first;
  assert.deepEqual(c.analisisDisponibles, []); assert.equal(c.isLoadingAnalyses, false);
});

for (const type of ['SALIVA', 'SANGRE']) test(`${type} sequential upload, partial failure, retry only errors and no concurrent batch`, async t => {
  const c = context(); files(c, t); c.formImagenes.tipoMuestra = type;
  const calls = deferred(), first = c.subirImagenes(); await turn();
  assert.equal(calls.length, 1); assert.equal(c.isUploading, true);
  assert.deepEqual(c.imagenesPreview.map(x => x.status), ['UPLOADING', 'PENDING']);
  assert.equal(calls[0].config.url, type === 'SANGRE' ? '/api/muestras-sangre/' : '/api/muestras/'); assert.equal(calls[0].config.data.get('analisis'), '3');
  await c.subirImagenes(); assert.equal(calls.length, 1);
  c.resetFilesForContext(); c.removerImagen(0); c.limpiarFormularioActivo(); assert.equal(c.imagenesPreview.length, 2);
  calls[0].resolve({ id_muestra: 10 }); await turn(); assert.equal(calls.length, 2);
  calls[1].reject(invalid({ imagen: ['Imagen inválida'] })); await first;
  assert.deepEqual(c.imagenesPreview.map(x => x.status), ['SUCCESS', 'ERROR']); assert.equal(c.isUploading, false); assert.equal(c.hasUnsavedWork, true);
  const retry = c.subirImagenes(); await turn(); assert.equal(calls.length, 3); assert.equal(calls[2].config.data.get('imagen').name, 'b.tif');
  calls[2].resolve({ id_muestra: 11 }); await retry;
  assert.deepEqual(c.imagenesPreview.map(x => x.status), ['SUCCESS', 'SUCCESS']); await c.subirImagenes();
  assert.equal(calls.length, 3); assert.equal(c.hasUnsavedWork, false);
});

test('missing upload context is rejected; reset/replacement/remove/clear release URLs', async t => {
  const c = context(), revoked = files(c, t); c.formImagenes.analisis = ''; let n = 0;
  api.defaults.adapter = async config => { n++; return ok(config, {}); }; await c.subirImagenes(); assert.equal(n, 0);
  c.resetFilesForContext(); assert.equal(c.imagenesPreview.length, 0); assert.equal(revoked.length, 2);
  c.onFileChange({ target: { files: [new File(['x'], 'new.png')] } });
  c.onFileChange({ target: { files: [new File(['x'], 'replace.png')] } }); assert.equal(revoked.length, 3);
  c.removerImagen(0); assert.equal(revoked.length, 4);
  c.onFileChange({ target: { files: [new File(['x'], 'clear.png')] } }); c.vistaActiva = 'imagenes'; c.limpiarFormularioActivo(); assert.equal(revoked.length, 5);
});

test('unmount revokes URLs, removes unload listener, clears timer and invalidates loaders', async t => {
  const c = context(), revoked = files(c, t), removed = [];
  t.mock.method(globalThis, 'clearTimeout', id => removed.push(id));
  mockWindow(t, { removeEventListener: (name, handler) => removed.push([name, handler]) });
  c.notificationTimer = 123; const calls = deferred(), load = c.cargarAnalisisCaso(); await turn();
  c.onFileChange({ target: { files: [new File(['x'], 'unmount.png')] } }); View.beforeUnmount.call(c);
  calls[0].resolve([{ id_analisis: 99 }]); await load;
  assert.equal(c.disposed, true); assert.deepEqual(c.analisisDisponibles, []); assert.equal(revoked.length, 3);
  assert.ok(removed.includes(123)); assert.ok(removed.some(item => Array.isArray(item) && item[0] === 'beforeunload'));
});

test('dirty navigation: clean, cancel/preserve, confirm/switch, section leave, pending images and reload', t => {
  let confirm = false, confirmations = 0;
  mockWindow(t, { confirm: () => { confirmations++; return confirm; } });
  const c = context(); c.requestTabChange('caso'); assert.equal(c.vistaActiva, 'caso'); assert.equal(confirmations, 0);
  c.formPaciente.nombre = 'Unsubmitted'; c.requestTabChange('imagenes'); assert.equal(c.vistaActiva, 'caso'); assert.equal(c.formPaciente.nombre, 'Unsubmitted');
  confirm = true; c.requestTabChange('imagenes'); assert.equal(c.vistaActiva, 'imagenes');
  const app = { seccion: 'registro', $refs: { registro: c }, confirmPendingDraftNavigation: () => true };
  confirm = false; App.methods.requestSectionChange.call(app, 'segmentacion'); assert.equal(app.seccion, 'registro');
  confirm = true; App.methods.requestSectionChange.call(app, 'segmentacion'); assert.equal(app.seccion, 'segmentacion');
  c.limpiarFormPaciente(); let prevented = 0; const event = { preventDefault: () => prevented++, returnValue: undefined };
  c.handleBeforeUnload(event); assert.equal(prevented, 0); files(c, t, ['pending.png']); assert.equal(c.hasUnsavedWork, true);
  c.handleBeforeUnload(event); assert.equal(prevented, 1); assert.equal(event.returnValue, ''); c.isUploading = true; assert.equal(c.confirmLeave(), false);
});

test('markup: upload busy lock, context hooks, retries and preview fallback', async () => {
  const html = await renderToString(createSSRApp({ ...View, data: () => ({ ...View.data(), vistaActiva: 'imagenes', isUploading: true }) }));
  assert.match(html, /<fieldset[^>]*disabled[^>]*aria-busy="true"/); assert.match(html, /Subiendo/);
  assert.equal((source.match(/@change="resetFilesForContext"/g) || []).length, 2);
  assert.match(source, /@error="img.previewUnavailable = true"/); assert.match(source, /Vista previa no disponible/);
  assert.match(source, /Reintentar carga de casos/); assert.match(source, /Reintentar carga de análisis/); assert.doesNotMatch(source, /v-html|Promise\.all/);
});

const render = overrides => renderToString(createSSRApp({ ...View, data: () => ({ ...View.data(), ...overrides }) }));
const element = (html, tag, id) => html.match(new RegExp(`<${tag}[^>]*id="${id}"[^>]*>`))?.[0] ?? '';

test('presentation: three freely accessible sections and one current navigation button', async () => {
  for (const [section, title, label] of [['paciente', 'Nuevo paciente', 'Paciente'], ['caso', 'Nuevo caso', 'Caso'], ['imagenes', 'Agregar imágenes', 'Imágenes']]) {
    const html = await render({ vistaActiva: section });
    const nav = html.match(/<nav[\s\S]*?<\/nav>/)[0];
    for (const text of ['Paciente', 'Caso', 'Imágenes']) assert.ok(nav.includes(text));
    assert.equal((nav.match(/aria-current="page"/g) || []).length, 1);
    assert.match(nav, new RegExp(`aria-current="page"[^>]*>${label}</button>`));
    assert.doesNotMatch(nav, /disabled/);
    assert.match(html, new RegExp(`<h3[^>]*>${title}</h3>`));
  }
});

test('presentation: patient labels, input order and required/optional fields stay intact', async () => {
  const html = await render({});
  const fields = ['identificacion', 'fecha_nacimiento', 'nombre', 'apellido', 'email', 'telefono'];
  let previous = -1;
  for (const [index, field] of fields.entries()) {
    const id = `patient-${field}`, input = element(html, 'input', id);
    assert.ok(input);
    assert.ok(html.includes(`<label for="${id}"`));
    assert.ok(html.indexOf(input) > previous);
    previous = html.indexOf(input);
    assert.equal(/\brequired\b/.test(input), index < 4);
  }
  assert.doesNotMatch(html, /id="(?:identity_mode|initials|external_patient_id|case_number)"/);
  assert.match(await render({ isCreatingPatient: true }), /Registrando\.\.\./);
});

test('presentation: DRF field errors reach accessible inline text, escape HTML and clear on retry/reset', async () => {
  const c = context();
  api.defaults.adapter = async () => { throw invalid({ identificacion: ['ID duplicado <script>'], email: ['Email inválido'], traceback: ['SECRET'] }); };
  await c.crearPaciente();
  const html = await render({ patientErrors: c.patientErrors });
  assert.match(element(html, 'input', 'patient-identificacion'), /aria-invalid="true"/);
  assert.match(element(html, 'input', 'patient-identificacion'), /aria-describedby="patient-identificacion-error"/);
  assert.match(html, /id="patient-identificacion-error"[^>]*>ID duplicado &lt;script&gt;/);
  assert.match(html, /id="patient-email-error"[^>]*>Email inválido/);
  assert.doesNotMatch(html, /<script>|SECRET/);
  const calls = deferred(), retry = c.crearPaciente(); await turn();
  assert.deepEqual(c.patientErrors, {});
  calls[0].reject(invalid({ nombre: ['Obligatorio'] })); await retry;
  c.limpiarFormPaciente(); assert.deepEqual(c.patientErrors, {});
  assert.deepEqual(registrationFieldErrors({ response: { status: 500, data: { nombre: ['SECRET'] } } }), {});
});

test('presentation: case context, optional analysis, field errors and busy state', async () => {
  const c = context(); c.vistaActiva = 'caso';
  api.defaults.adapter = async () => { throw invalid({ id_paciente_fk: ['Paciente inválido'], titulo: ['Título obligatorio'], descripcion: ['Descripción inválida'] }); };
  await c.crearCaso();
  const html = await render({ vistaActiva: 'caso', caseErrors: c.caseErrors });
  for (const id of ['case-patient', 'case-name', 'case-description']) {
    assert.ok(html.includes(`<label for="${id}"`));
    assert.ok(html.includes(`aria-describedby="${id}-error"`));
    assert.ok(html.includes(`id="${id}-error"`));
  }
  assert.match(element(html, 'input', 'crear_analisis'), /type="checkbox"/);
  assert.match(element(html, 'input', 'crear_analisis'), /\bchecked\b/);
  assert.match(html, /Se creará un análisis asociado al nuevo caso/);
  assert.match(await render({ vistaActiva: 'caso', isCreatingCase: true }), /Creando\.\.\./);
  c.limpiarFormCaso(); assert.deepEqual(c.caseErrors, {});
});

test('presentation: patients loading lifecycle and dependent selectors with empty/loading states', async () => {
  const c = context(), calls = deferred(), loading = c.cargarPacientes(); await turn();
  assert.equal(c.isLoadingPatients, true);
  for (const section of ['caso', 'imagenes']) {
    const html = await render({ vistaActiva: section, isLoadingPatients: c.isLoadingPatients });
    assert.match(html, /Cargando pacientes\.\.\./);
    assert.match(element(html, 'select', section === 'caso' ? 'case-patient' : 'upload-patient'), /disabled/);
  }
  calls[0].resolve([]); await loading; assert.equal(c.isLoadingPatients, false);
  const html = await render({ vistaActiva: 'imagenes' });
  for (const id of ['upload-case', 'upload-analysis']) assert.match(element(html, 'select', id), /disabled/);
  assert.match(element(html, 'input', 'upload-files'), /disabled/);
  for (const text of ['Seleccione un paciente para ver sus casos.', 'Seleccione un caso para ver sus análisis.', 'No hay archivos seleccionados.']) assert.ok(html.includes(text));
  const formImagenes = { ...View.data().formImagenes, paciente: 1, caso: 2 };
  const busy = await render({ vistaActiva: 'imagenes', formImagenes, isLoadingCases: true, isLoadingAnalyses: true });
  for (const [id, message] of [['upload-case', 'Cargando casos...'], ['upload-analysis', 'Cargando análisis...']]) {
    assert.match(element(busy, 'select', id), /disabled/); assert.ok(busy.includes(message));
  }
  assert.match(await render({ vistaActiva: 'imagenes', formImagenes }), /No hay análisis disponibles para este caso/);
});

test('presentation: upload destination, real sample radios, statuses, preview fallback and retry label', async () => {
  const imagenesPreview = ['PENDING', 'UPLOADING', 'SUCCESS', 'ERROR'].map((status, i) => ({
    archivo: { name: `fixture-${i}.tif` }, url: `blob:fixture-${i}`, status,
    previewUnavailable: i === 3, error: i === 3 ? 'Imagen inválida' : '',
  }));
  const state = { vistaActiva: 'imagenes', pacientes: [{ id_paciente: 1, nombre: 'Test', apellido: 'Fixture' }],
    casosDisponibles: [{ id_caso: 2, titulo: 'Caso de prueba' }], analisisDisponibles: [{ id_analisis: 3, estado: 0 }],
    formImagenes: { ...View.data().formImagenes, paciente: 1, caso: 2, analisis: 3 }, imagenesPreview };
  const html = await render(state), destination = html.match(/<dl[\s\S]*?<\/dl>/)[0];
  for (const text of ['Test Fixture', 'Caso de prueba', '#3', 'saliva']) assert.ok(destination.includes(text));
  for (const [i, status] of ['Pendiente', 'Subiendo...', 'Subida', 'Error'].entries()) {
    assert.ok(html.includes(`fixture-${i}.tif`)); assert.ok(html.includes(status));
  }
  assert.match(html, /Vista previa no disponible/); assert.match(html, /Imagen inválida/);
  for (const type of ['SALIVA', 'SANGRE']) {
    assert.ok(html.includes(`<label for="upload-type-${type}"`));
    assert.match(element(html, 'input', `upload-type-${type}`), /type="radio"/);
  }
  assert.match(element(html, 'input', 'upload-files'), /type="file" multiple accept="image\/\*"/);
  assert.doesNotMatch(html, /Arrastra|drag-and-drop/);
  assert.match(await render({ ...state, imagenesPreview: imagenesPreview.slice(2) }), /Reintentar fallidos/);
  assert.match(await render({ ...state, isUploading: true }), /Subiendo\.\.\./);
});

function analysisContext() {
  const c = context();
  c.vistaActiva = 'imagenes';
  c.formImagenes.paciente = 1; c.formImagenes.caso = 2;
  c.casosDisponibles = [{ id_caso: 2, paciente: 1, titulo: 'Synthetic case' }];
  return c;
}

test('18R-D create analysis: empty case action, double submit, context lock, refresh and selected open result', async () => {
  const c = analysisContext();
  const html = await render({ vistaActiva: 'imagenes', formImagenes: c.formImagenes, casosDisponibles: c.casosDisponibles });
  assert.match(html, /No hay análisis disponibles para este caso/);
  assert.match(html, />Crear análisis<\/button>/);
  assert.match(source, /@click="crearAnalisis"/);
  const calls = deferred(), create = c.crearAnalisis(); await turn(); await c.crearAnalisis();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].config.url, '/api/analisis/');
  assert.deepEqual(JSON.parse(calls[0].config.data), { id_paciente_fk: 1, id_caso_fk: 2, estado: 0 });
  assert.equal(c.isBusy, true); assert.equal(c.confirmLeave(), false);
  await c.cargarCasosPaciente(); await c.cargarAnalisisCaso(); c.limpiarFormularioActivo();
  assert.equal(c.formImagenes.paciente, 1); assert.equal(c.formImagenes.caso, 2);
  const busy = await render({ vistaActiva: 'imagenes', isCreatingAnalysis: true });
  assert.match(busy, /<fieldset[^>]*disabled[^>]*aria-busy="true"/);
  assert.match(busy, /Creando análisis\.\.\./);
  const analysis = { id_analisis: 4, id_caso_fk: 2, id_paciente_fk: 1, estado: 0 };
  calls[0].resolve(analysis); await turn();
  assert.equal(calls[1].config.url, '/api/casos/2/analisis/');
  calls[1].resolve([analysis]); await create;
  assert.equal(c.formImagenes.analisis, 4); assert.equal(c.newlyCreatedAnalysisId, 4);
  assert.equal(c.isCreatingAnalysis, false); assert.equal(c.isLoadingAnalyses, false);
  assert.equal(c.hasUnsavedWork, false); assert.equal(c.vistaActiva, 'imagenes');
  assert.equal(c.canCreateAnalysis, false);
  const populated = await render({ vistaActiva: 'imagenes', formImagenes: c.formImagenes, casosDisponibles: c.casosDisponibles, analisisDisponibles: c.analisisDisponibles });
  assert.doesNotMatch(populated, />Crear análisis<\/button>/);
  assert.match(populated, /<dt[^>]*>Estado<\/dt><dd[^>]*>Abierto<\/dd>/);
});

test('18R-D failed analysis creation preserves context/files, reports DRF error and permits retry', async t => {
  const c = analysisContext(); files(c, t);
  c.formImagenes.analisis = '';
  const preview = c.imagenesPreview[0], calls = deferred(), first = c.crearAnalisis(); await turn();
  calls[0].reject(invalid({ id_caso_fk: ['El caso no pertenece al paciente.'] })); await first;
  assert.equal(c.formImagenes.paciente, 1); assert.equal(c.formImagenes.caso, 2);
  assert.equal(c.imagenesPreview[0], preview); assert.equal(c.isCreatingAnalysis, false);
  assert.match(c.notices.at(-1).message, /Caso: El caso no pertenece/);
  const retry = c.crearAnalisis(); await turn();
  calls[1].resolve({ id_analisis: 4, estado: 0 }); await turn();
  calls[2].resolve([{ id_analisis: 4, estado: 0 }]); await retry;
  assert.equal(c.formImagenes.analisis, 4); assert.equal(c.imagenesPreview[0], preview);
});

test('18R-D confirmed creation survives failed list refresh without a second creation', async () => {
  const c = analysisContext(), calls = deferred(), first = c.crearAnalisis(); await turn();
  calls[0].resolve({ id_analisis: 4, estado: 0 }); await turn();
  calls[1].reject(new Error('network')); await first;
  assert.equal(c.formImagenes.analisis, 4); assert.equal(c.analisisDisponibles[0].id_analisis, 4);
  assert.equal(c.analysesLoadError, true); assert.equal(c.isCreatingAnalysis, false);
  await c.crearAnalisis(); assert.equal(calls.length, 2);
  const refresh = c.cargarAnalisisCaso(); await turn();
  calls[2].resolve([{ id_analisis: 4, estado: 0 }]); await refresh;
  assert.equal(c.analysesLoadError, false); assert.equal(c.canCreateAnalysis, false);
});

test('18R-D analysis creation invalidates older GETs and ignores response after disposal', async () => {
  const c = analysisContext(), calls = deferred();
  const old = c.cargarAnalisisCaso(); await turn();
  const recent = c.cargarAnalisisCaso(); await turn();
  calls[1].resolve([]); await recent;
  const create = c.crearAnalisis(); await turn();
  calls[2].resolve({ id_analisis: 4, estado: 0 }); await turn();
  calls[3].resolve([{ id_analisis: 4, estado: 0 }]); await create;
  calls[0].resolve([]); await old;
  assert.equal(c.formImagenes.analisis, 4); assert.equal(c.analisisDisponibles[0].id_analisis, 4);
  const other = analysisContext(), more = deferred(), pending = other.crearAnalisis(); await turn();
  other.disposed = true; other.analysesGeneration++;
  more[0].resolve({ id_analisis: 5, estado: 0 }); await pending;
  assert.equal(other.formImagenes.analisis, ''); assert.deepEqual(other.analisisDisponibles, []);
  assert.equal(more.length, 1);
});

test('18R-D mismatched patient/case or failed/loading discovery never offers or posts creation', async () => {
  for (const overrides of [{ formImagenes: { paciente: 99, caso: 2 } }, { isLoadingAnalyses: true },
    { analysesLoadError: true }, { casesLoadError: true }, { analisisDisponibles: [{ id_analisis: 4 }] }]) {
    const c = analysisContext(); Object.assign(c, overrides);
    const calls = deferred(); await c.crearAnalisis();
    assert.equal(c.canCreateAnalysis, false); assert.equal(calls.length, 0);
  }
});

for (const state of [0, 1, 2]) test(`18R-D analysis state ${state}: visible destination, file picker and upload/retry guard`, async t => {
  const c = analysisContext(); files(c, t, ['state.png']);
  c.analisisDisponibles = [{ id_analisis: 3, estado: state }];
  const html = await render({ vistaActiva: 'imagenes', formImagenes: c.formImagenes, analisisDisponibles: c.analisisDisponibles, imagenesPreview: c.imagenesPreview });
  assert.match(html, new RegExp(`<dt[^>]*>Estado</dt><dd[^>]*>${c.estadoTexto(state)}</dd>`));
  assert.equal(/\bdisabled\b/.test(element(html, 'input', 'upload-files')), state === 2);
  assert.equal(/análisis está cerrado y no admite/.test(html), state === 2);
  const submit = html.match(/<button type="submit"[^>]*>/)[0];
  assert.equal(/\bdisabled\b/.test(submit), state === 2);
  let count = 0; api.defaults.adapter = async config => { count++; return ok(config, { id_muestra: 10 }); };
  await c.subirImagenes();
  assert.equal(count, state === 2 ? 0 : 1);
  c.imagenesPreview[0].status = 'ERROR'; await c.subirImagenes();
  assert.equal(count, state === 2 ? 0 : 2);
  assert.equal(c.analisisDisponibles[0].estado, state);
});

test('18R-D switch to closed analysis clears pending files, revokes URLs and rejects new selection', async t => {
  const c = analysisContext(), revoked = files(c, t);
  c.analisisDisponibles = [{ id_analisis: 3, estado: 0 }, { id_analisis: 4, estado: 2 }];
  c.formImagenes.analisis = 4; c.resetFilesForContext();
  assert.equal(revoked.length, 2); assert.equal(c.imagenesPreview.length, 0);
  assert.match(c.notices.at(-1).message, /reinició por cambio de contexto/);
  c.onFileChange({ target: { files: [new File(['x'], 'blocked.png')] } });
  assert.equal(c.imagenesPreview.length, 0);
});

test('18R-D birthdate max uses local date; yesterday/today accepted, tomorrow blocked before HTTP', async () => {
  const c = context(), now = new Date();
  const local = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  assert.equal(c.currentLocalDate(), local);
  assert.match(element(await render({}), 'input', 'patient-fecha_nacimiento'), new RegExp(`max="${local}"`));
  c.currentLocalDate = () => '2026-10-20';
  for (const date of ['2026-10-19', '2026-10-20', '2026-10-21']) {
    c.formPaciente.fecha_nacimiento = date;
    let posts = 0;
    api.defaults.adapter = async config => { if (config.method === 'post') posts++; return ok(config, config.method === 'post' ? { id_paciente: 1 } : []); };
    await c.crearPaciente();
    assert.equal(posts, date === '2026-10-21' ? 0 : 1);
  }
  assert.match(c.patientErrors.fecha_nacimiento, /no puede ser futura/);
  assert.match(await render({ patientErrors: c.patientErrors }), /id="patient-fecha_nacimiento-error"[^>]*>La fecha/);
  assert.match(source, /@change="validateBirthDate" @invalid="validateBirthDate"/);
  c.formPaciente.fecha_nacimiento = '2026-10-20';
  assert.equal(c.validateBirthDate(), true);
  assert.equal(c.patientErrors.fecha_nacimiento, undefined);
  api.defaults.adapter = async () => { throw invalid({ fecha_nacimiento: ['La fecha de nacimiento no puede ser futura.'] }); };
  await c.crearPaciente();
  assert.match(c.patientErrors.fecha_nacimiento, /no puede ser futura/);
  assert.equal(c.isCreatingPatient, false);
});

const pseudoFields = { initials: 'ACL', external_id_namespace: 'test', external_patient_id: '007', fecha_nacimiento: '2000-01-01' };

test('18R-E accessible mode selector defaults to identified and displays only relevant fields in order', async () => {
  const c = context();
  assert.equal(c.patientIdentityMode, 'IDENTIFIED'); assert.equal(c.hasUnsavedWork, false);
  const identified = await render({});
  assert.match(element(identified, 'input', 'patient-mode-IDENTIFIED'), /checked/);
  for (const field of ['initials', 'external_patient_id', 'external_id_namespace']) assert.equal(element(identified, 'input', `patient-${field}`), '');
  c.requestPatientMode('PSEUDONYMIZED');
  assert.equal(c.patientIdentityMode, 'PSEUDONYMIZED'); assert.equal(c.hasUnsavedWork, true);
  const html = await render({ patientIdentityMode: c.patientIdentityMode });
  assert.match(element(html, 'input', 'patient-mode-PSEUDONYMIZED'), /checked/);
  assert.match(html, /<legend[^>]*>Tipo de registro/);
  assert.match(html, /label for="patient-mode-PSEUDONYMIZED"/);
  assert.match(source, /@change="requestPatientMode\(mode.value, \$event\)"/);
  let previous = -1;
  for (const field of ['external_patient_id', 'fecha_nacimiento', 'initials', 'external_id_namespace']) {
    const input = element(html, 'input', `patient-${field}`);
    assert.ok(input); assert.match(input, /required/);
    assert.ok(html.indexOf(input) > previous); previous = html.indexOf(input);
    assert.ok(html.includes(`label for="patient-${field}"`));
  }
  for (const field of ['nombre', 'apellido', 'email', 'telefono', 'identificacion']) assert.equal(element(html, 'input', `patient-${field}`), '');
  c.requestPatientMode('IDENTIFIED'); assert.equal(c.patientIdentityMode, 'IDENTIFIED'); assert.equal(c.hasUnsavedWork, false);
});

test('18R-E mode change confirms exclusive data, cancellation restores radios, confirmation retains common date', t => {
  let accept = false, confirmations = 0;
  mockWindow(t, { confirm: () => { confirmations++; return accept; } });
  const c = context(); Object.assign(c.formPaciente, { nombre: 'Test', apellido: 'Fixture', identificacion: 'ADMIN', email: 'test@example.com', telefono: '555', fecha_nacimiento: '2000-01-01' });
  const before = { ...c.formPaciente };
  const radios = [{ value: 'IDENTIFIED', checked: false }, { value: 'PSEUDONYMIZED', checked: true }];
  const event = { target: { form: { querySelectorAll: () => radios } } };
  c.requestPatientMode('PSEUDONYMIZED', event);
  assert.equal(confirmations, 1); assert.equal(c.patientIdentityMode, 'IDENTIFIED');
  assert.deepEqual(c.formPaciente, before); assert.deepEqual(radios.map(r => r.checked), [true, false]);
  accept = true; c.requestPatientMode('PSEUDONYMIZED');
  for (const field of ['nombre', 'apellido', 'identificacion', 'email', 'telefono']) assert.equal(c.formPaciente[field], '');
  assert.equal(c.formPaciente.fecha_nacimiento, '2000-01-01');
  Object.assign(c.formPaciente, pseudoFields); accept = false;
  c.requestPatientMode('IDENTIFIED'); assert.equal(c.patientIdentityMode, 'PSEUDONYMIZED'); assert.equal(c.formPaciente.initials, 'ACL');
  accept = true; c.requestPatientMode('IDENTIFIED');
  for (const field of ['initials', 'external_patient_id', 'external_id_namespace']) assert.equal(c.formPaciente[field], '');
  assert.equal(c.formPaciente.fecha_nacimiento, '2000-01-01');
});

test('18R-E common date alone needs no confirmation; clear retains mode and resets dirty baseline', t => {
  mockWindow(t, { confirm: () => { assert.fail('Only a common date must not trigger confirmation'); } });
  const c = context(); c.formPaciente.fecha_nacimiento = '2000-01-01';
  c.requestPatientMode('PSEUDONYMIZED'); assert.equal(c.formPaciente.fecha_nacimiento, '2000-01-01');
  c.limpiarFormularioActivo(); assert.equal(c.patientIdentityMode, 'PSEUDONYMIZED'); assert.equal(c.hasUnsavedWork, false);
  for (const field of ['initials', 'external_id_namespace', 'external_patient_id', 'fecha_nacimiento']) {
    c.formPaciente[field] = 'test'; assert.equal(c.hasUnsavedWork, true); c.limpiarFormPaciente();
  }
  c.requestPatientMode('IDENTIFIED'); assert.equal(c.hasUnsavedWork, true);
});

test('18R-E pseudonymized minimal payload, double submit lock, refresh, mode retained and no autoadvance', async () => {
  const c = context(); c.requestPatientMode('PSEUDONYMIZED'); Object.assign(c.formPaciente, pseudoFields);
  // Even stale hidden values must not leak into the payload.
  c.formPaciente.nombre = 'not-sent'; c.formPaciente.identificacion = 'not-sent'; c.formPaciente.email = 'not-sent';
  const calls = deferred(), first = c.crearPaciente(); await turn(); await c.crearPaciente();
  assert.equal(calls.length, 1);
  assert.deepEqual(JSON.parse(calls[0].config.data), { ...pseudoFields, identity_mode: 'PSEUDONYMIZED' });
  c.requestPatientMode('IDENTIFIED'); assert.equal(c.patientIdentityMode, 'PSEUDONYMIZED');
  assert.match(await render({ patientIdentityMode: 'PSEUDONYMIZED', isCreatingPatient: true }), /Registrando\.\.\./);
  calls[0].resolve({ id_paciente: 10 }); await turn();
  calls[1].resolve([{ id_paciente: 10, identity_mode: 'PSEUDONYMIZED', ...pseudoFields }]); await first;
  assert.equal(c.newlyCreatedPatientId, 10); assert.equal(c.pacientes[0].id_paciente, 10);
  assert.equal(c.patientIdentityMode, 'PSEUDONYMIZED'); assert.equal(c.hasUnsavedWork, false);
  assert.equal(c.isCreatingPatient, false); assert.equal(c.vistaActiva, 'paciente');
  assert.ok(Object.values(c.formPaciente).every(value => value === ''));
});

test('18R-E pseudonymized errors attach to fields and duplicate authority survives failed submit', async () => {
  const c = context(); c.requestPatientMode('PSEUDONYMIZED'); Object.assign(c.formPaciente, pseudoFields);
  api.defaults.adapter = async () => { throw invalid({ initials: ['Iniciales requeridas'], external_id_namespace: ['Origen requerido'], external_patient_id: ['Ya existe un paciente con este ID en el origen seleccionado.'], fecha_nacimiento: ['La fecha de nacimiento no puede ser futura.'] }); };
  await c.crearPaciente();
  assert.equal(c.formPaciente.external_patient_id, '007'); assert.equal(c.patientIdentityMode, 'PSEUDONYMIZED');
  assert.equal(c.isCreatingPatient, false); assert.equal(c.hasUnsavedWork, true);
  const html = await render({ patientIdentityMode: 'PSEUDONYMIZED', patientErrors: c.patientErrors });
  for (const field of ['initials', 'external_id_namespace', 'external_patient_id', 'fecha_nacimiento']) {
    assert.match(element(html, 'input', `patient-${field}`), /aria-invalid="true"/);
    assert.ok(html.includes(`aria-describedby="patient-${field}-error"`));
    assert.ok(html.includes(c.patientErrors[field]));
  }
  assert.match(c.notices.at(-1).message, /ID hospitalario:/);
  assert.match(c.notices.at(-1).message, /Origen \/ institución:/);
});

test('18R-E registration labels hide technical IDs in case, image selector and destination with safe fallbacks', async () => {
  const c = context();
  const patients = [
    { id_paciente: 1, nombre: 'Test', apellido: 'Fixture', identificacion: 'ADMIN' },
    { id_paciente: 2, identity_mode: 'PSEUDONYMIZED', ...pseudoFields, identificacion: 'TECHNICAL_SECRET' },
  ];
  assert.equal(c.patientRegistrationLabel(patients[0]), 'Test Fixture · ADMIN');
  assert.equal(c.patientRegistrationLabel(patients[1]), 'ACL · test / 007');
  assert.equal(c.patientRegistrationLabel({ identity_mode: 'PSEUDONYMIZED', identificacion: 'TECHNICAL_SECRET' }), 'Paciente pseudonimizado');
  assert.equal(c.patientRegistrationLabel({ display_name: 'Legacy' }), 'Legacy');
  assert.equal(c.patientRegistrationLabel(null), '');
  for (const section of ['caso', 'imagenes']) {
    const html = await render({ vistaActiva: section, pacientes: patients,
      formImagenes: { ...View.data().formImagenes, paciente: 2 } });
    assert.ok(html.includes('Test Fixture · ADMIN')); assert.ok(html.includes('ACL · test / 007'));
    assert.doesNotMatch(html, /TECHNICAL_SECRET/);
    if (section === 'imagenes') assert.ok(html.match(/<dl[\s\S]*?<\/dl>/)[0].includes('ACL · test / 007'));
  }
});
