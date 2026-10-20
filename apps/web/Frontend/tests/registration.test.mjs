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
