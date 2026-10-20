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
const { registrationErrorMessage } = await server.ssrLoadModule('/src/services/registrationErrors.js');
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
