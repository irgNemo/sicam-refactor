import assert from 'node:assert/strict';
import { after, afterEach, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { createSSRApp, reactive } from 'vue';
import { renderToString } from '@vue/server-renderer';
const server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile:false,
  plugins:[vuePlugin()], optimizeDeps:{ noDiscovery:true, include:[] },
  server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom' });
const { auth } = await server.ssrLoadModule('/src/services/auth.js');
const sessionFixture = () => ({ id: 1, username: 'fixture', role: 'ADMIN', institution: { id: 1, code: 'TEST' }, must_change_password: false });
auth.user = sessionFixture();
const keepAlive = setInterval(()=>{},1000);
after(async()=>{clearInterval(keepAlive);await server.close();});
const {default:View}=await server.ssrLoadModule('/src/views/AdquisicionView.vue');
const {default:Series}=await server.ssrLoadModule('/src/components/acquisition/AcquisitionSeriesSelector.vue');
const {default:CreateForm}=await server.ssrLoadModule('/src/components/acquisition/AcquisitionSeriesCreateForm.vue');
const {default:Registration}=await server.ssrLoadModule('/src/views/RegistroView.vue');
const {default:App}=await server.ssrLoadModule('/src/App.vue');
const {default:TopBar}=await server.ssrLoadModule('/src/components/TopBar.vue');
const {default:api}=await server.ssrLoadModule('/src/services/apiClient.js');
const service=await server.ssrLoadModule('/src/services/acquisitionService.js');
const ok=(config,data)=>({config,data,status:200,headers:{},statusText:'OK'});
const profile={id:1,name:'Synthetic',image_width_px:4928,image_height_px:4928};
const calibration={id:2,acquisition_profile:1,label:'Synthetic calibration',status:'PROVISIONAL',scale_x_um_per_px:'0.055233934048',scale_y_um_per_px:'0.055010060892',created_at:'2026-10-21'};
const series={id:3,patient:1,acquisition_profile:1,calibration:2,label:'Synthetic series'};
const originalWindow=globalThis.window;
afterEach(()=>{auth.user=sessionFixture();globalThis.window=originalWindow;});
function context(component,props={}) {
  const ctx=reactive({...component.data(),...props,events:[],$refs:{fileInput:{value:''}},$emit(name,value){this.events.push([name,value]);}});
  for(const [name,method] of Object.entries(component.methods))ctx[name]=method.bind(ctx);
  for(const [name,getter] of Object.entries(component.computed||{}))Object.defineProperty(ctx,name,{get:()=>getter.call(ctx)});
  return ctx;
}
const render=(component,data={},props={})=>renderToString(createSSRApp({...component,watch:{},data:()=>({...(component.data?.() || {}),...data})},props));
const listAdapter=(items=[series])=>{api.defaults.adapter=async config=>ok(config,config.url.includes('acquisition-series')?items:config.url.includes('profiles')?[profile]:[calibration]);};

test('main navigation includes working Adquisición and preserves leave guard',async()=>{
  const html=await render(TopBar,{}, {seccion:'adquisicion'});assert.match(html,/Adquisición/);assert.match(html,/class="(?:nav-btn active|active nav-btn)"/);
  const ctx={seccion:'registro',$refs:{registro:{confirmLeave:()=>false}},confirmPendingDraftNavigation:()=>true};
  App.methods.requestSectionChange.call(ctx,'adquisicion');assert.equal(ctx.seccion,'registro');
  ctx.$refs.registro.confirmLeave=()=>true;App.methods.requestSectionChange.call(ctx,'adquisicion');assert.equal(ctx.seccion,'adquisicion');
  ctx.$refs.adquisicion={confirmLeave:()=>false};App.methods.requestSectionChange.call(ctx,'registro');assert.equal(ctx.seccion,'adquisicion');
});
test('acquisition shares operational session without Basic credentials',()=>{
  assert.equal(service.operator.ready,true); assert.equal(api.defaults.auth,undefined);
  auth.user=null; assert.equal(service.operator.ready,false);
  auth.user={...sessionFixture(),must_change_password:true}; assert.equal(service.operator.ready,false);
});
test('profile list and editable metadata render; unknown fields remain optional',async()=>{
  auth.user=sessionFixture();
  const ctx=context(View);ctx.editProfile(null);
  const html=await render(View,{profiles:[profile],profileForm:ctx.profileForm});
  assert.match(html,/Synthetic/);assert.match(html,/Nueva configuración/);assert.match(html,/Fabricante de cámara/);
  const optional=ctx.profileFields.filter(f=>!f.required);assert.ok(optional.some(f=>f.key==='camera_model'));
  let payload;api.defaults.adapter=async config=>{if(config.method==='post')payload=JSON.parse(config.data);return ok(config,[]);};
  ctx.profileForm.name='Synthetic';ctx.profileForm.image_width_px=4928;ctx.profileForm.image_height_px=4928;await ctx.saveProfile();
  assert.equal(payload.objective_magnification,null);assert.equal(payload.binning_x,null);assert.equal(ctx.profileForm,null);
});
test('calibration list shows sx/sy, provisional text, date and references without validate action',async()=>{
  auth.user=sessionFixture();const html=await render(View,{tab:'Calibraciones',profiles:[profile],calibrations:[calibration]});
  for(const text of ['0.055233934048','0.055010060892','Provisional','validación experimental','Ver referencias','Nueva calibración automática','Diámetro conocido'])assert.ok(html.includes(text));
  assert.doesNotMatch(html,/>Validar</);
});
test('automatic form sends explicit physical metadata and review token',()=>{
  const file=new File(['synthetic'],'does-not-encode-diameter.png');
  const payload=service.automaticPayload(1,'Synthetic',[{file,pattern_type:'CIRCLE',known_dimension_um:'70'}],'token');
  assert.equal(payload.get('source_token'),'token');assert.equal(payload.get('reference_0').name,file.name);
  assert.deepEqual(JSON.parse(payload.get('references')),[{pattern_type:'CIRCLE',known_dimension_um:'70'}]);
});
test('measure displays diagnostics; create uses reviewed token and becomes clean',async()=>{
  const ctx=context(View);ctx.automaticProfile=1;ctx.automaticLabel='Synthetic';ctx.references[0].file=new File(['x'],'pattern.png');
  const review={usable:true,source_token:'abc',scale_x_um_per_px:'0.05',scale_y_um_per_px:'0.06',warnings:['SINGLE_MEASURED_REFERENCE'],results:[]};
  let createToken;api.defaults.adapter=async config=>{
    if(config.url.endsWith('automatic-preview/'))return ok(config,{review});
    if(config.url.endsWith('automatic/')){createToken=config.data.get('source_token');return ok(config,{review,calibration});}
    return ok(config,[]);
  };
  await ctx.measure();assert.deepEqual(ctx.review,review);assert.equal(ctx.created,false);await ctx.createCalibration();
  assert.equal(createToken,'abc');assert.equal(ctx.created,true);assert.equal(ctx.hasUnsavedWork,false);
});
test('unusable calibration cannot be created and displays no-record message',async()=>{
  auth.user=sessionFixture();const ctx=context(View);ctx.review={usable:false};let calls=0;api.defaults.adapter=async c=>{calls++;return ok(c,{});};await ctx.createCalibration();assert.equal(calls,0);
  const html=await render(View,{tab:'Calibraciones',review:{usable:false,results:[],warnings:[]}});assert.match(html,/no se creó una calibración/);
});
test('patient without series can create or continue in pixels',async()=>{
  auth.user=sessionFixture();const ctx=context(Series,{patientId:1,disabled:false});listAdapter([]);await ctx.load();assert.equal(ctx.selectedId,'');
  const html=await render(Series,{series:[]},{patientId:1});assert.match(html,/No hay una serie/);assert.match(html,/Crear serie/);assert.match(html,/procesamiento en píxeles/);
});
test('one series auto-selects; several require choice; other patient excluded',async()=>{
  auth.user=sessionFixture();const ctx=context(Series,{patientId:1,disabled:false});listAdapter([series,{...series,id:9,patient:2}]);await ctx.load();assert.equal(ctx.selectedId,3);
  listAdapter([series,{...series,id:4}]);await ctx.load();assert.equal(ctx.selectedId,'');ctx.choose(9);assert.equal(ctx.selectedId,'');ctx.choose(4);assert.equal(ctx.selectedId,4);
});
test('patient switch discards stale series response',async()=>{
  auth.user=sessionFixture();const ctx=context(Series,{patientId:1,disabled:false});let resolve;
  api.defaults.adapter=config=>config.url.includes('acquisition-series')?new Promise(r=>{resolve=data=>r(ok(config,data));}):Promise.resolve(ok(config,[]));
  const first=ctx.load();await new Promise(r=>setImmediate(r));const oldResolve=resolve;
  ctx.patientId=2;listAdapter([{...series,patient:2,id:7}]);await ctx.load();oldResolve([series]);await first;assert.equal(ctx.selectedId,7);
});
test('series creation sends patient, nullable calibration and resets dirty baseline',async()=>{
  // creation logic now lives in AcquisitionSeriesCreateForm; selector onCreated selects the result
  const ctx=context(CreateForm,{patientId:1});ctx.profiles=[profile];ctx.form={label:'New',acquisition_profile:1,calibration:'',acquisition_date:''};let sent;
  api.defaults.adapter=async config=>{sent=JSON.parse(config.data);return ok(config,{...series,calibration:null});};await ctx.create();
  assert.equal(sent.patient,1);assert.equal(sent.calibration,null);
  // dirty (form cleared) — form fields reset after creation
  assert.equal(ctx.form.label,'');
  // verify selector onCreated selects returned series
  const selectorCtx=context(Series,{patientId:1,disabled:false});selectorCtx.series=[];
  selectorCtx.onCreated({...series,calibration:null});assert.equal(selectorCtx.selectedId,3);assert.equal(selectorCtx.dirty,false);
});
test('series without calibration, provisional and retired are explicit; retired excluded from new choices',async()=>{
  auth.user=sessionFixture();
  for(const [status,text] of [['PROVISIONAL','calibración provisional'],['RETIRED','Calibración retirada']]) {
    const html=await render(Series,{selectedId:3,series:[series],profiles:[profile],calibrations:[{...calibration,status}]},{patientId:1});assert.ok(html.includes(text));
  }
  const html=await render(Series,{selectedId:3,series:[{...series,calibration:null}],profiles:[profile]},{patientId:1});assert.match(html,/Sin calibración física/);
  // eligibleCalibrations now lives in CreateForm
  const ctx=context(CreateForm,{patientId:1});ctx.form.acquisition_profile=1;ctx.calibrations=[calibration,{...calibration,id:5,status:'RETIRED'}];assert.deepEqual(ctx.eligibleCalibrations.map(c=>c.id),[2]);
});
test('resolution feedback never derives scale or resizes image',()=>{
  assert.match(service.resolutionFeedback({width:4928,height:4928},profile),/Compatible/);
  assert.match(service.resolutionFeedback({width:2464,height:2464},profile),/incompatible/);
  assert.match(service.resolutionFeedback({width:2464,height:2464},profile),/continuar sin medidas físicas/);
  assert.match(service.resolutionFeedback(null,profile),/backend/);
});
for(const sampleType of ['SALIVA','SANGRE'])test(`upload ${sampleType}: nullable/selected series payload and backend compatibility`,async()=>{
  for(const selected of [null,series]) {
    const ctx=context(Registration);ctx.mostrarNotificacion=()=>{};ctx.formImagenes={paciente:1,caso:2,analisis:3,tipoMuestra:sampleType};ctx.selectedAcquisition={series:selected,profile,calibration};
    ctx.imagenesPreview=[{archivo:new File(['synthetic'],'source.png'),url:'blob:test',status:'PENDING'}];let payload;
    api.defaults.adapter=async config=>{if(config.method==='post'){payload=config.data;return ok(config,{id_muestra:99});}return ok(config,{status:selected?'RESOLUTION_MISMATCH':'NO_ACQUISITION_SERIES'});};
    await ctx.subirImagenes();assert.equal(payload.get('acquisition_series'),selected?'3':null);assert.equal(ctx.imagenesPreview[0].status,'SUCCESS');
    assert.equal(ctx.imagenesPreview[0].compatibility.status,selected?'RESOLUTION_MISMATCH':'NO_ACQUISITION_SERIES');
  }
});
test('compatibility failure does not mark confirmed upload failed or retry it',async()=>{
  const ctx=context(Registration);ctx.mostrarNotificacion=()=>{};ctx.formImagenes={paciente:1,caso:2,analisis:3,tipoMuestra:'SALIVA'};
  ctx.imagenesPreview=[{archivo:new File(['x'],'source.png'),status:'PENDING'}];let posts=0;
  api.defaults.adapter=async config=>{if(config.method==='post'){posts++;return ok(config,{id_muestra:99});}throw Error('offline');};
  await ctx.subirImagenes();assert.equal(ctx.imagenesPreview[0].status,'SUCCESS');assert.equal(ctx.imagenesPreview[0].compatibility.status,'CHECK_FAILED');await ctx.subirImagenes();assert.equal(posts,1);
});
test('series change releases previews and marks new series form dirty for navigation',()=>{
  const ctx=context(Registration);ctx.mostrarNotificacion=()=>{};ctx.imagenesPreview=[{url:'blob:synthetic',status:'PENDING'}];ctx.formImagenes.archivos=[{}];
  const original=URL.revokeObjectURL;let revoked;URL.revokeObjectURL=url=>{revoked=url;};
  try{ctx.acquisitionChanged({series,profile,calibration});assert.equal(revoked,'blob:synthetic');assert.equal(ctx.imagenesPreview.length,0);}finally{URL.revokeObjectURL=original;}
  ctx.seriesDirty=true;assert.equal(ctx.hasUnsavedWork,true);
});

test('upload uses compatibility returned by backend without another lookup',async()=>{
  const ctx=context(Registration);ctx.mostrarNotificacion=()=>{};ctx.formImagenes={paciente:1,caso:2,analisis:3,tipoMuestra:'SALIVA'};
  ctx.imagenesPreview=[{archivo:new File(['x'],'source.png'),status:'PENDING'}];let calls=0;
  api.defaults.adapter=async config=>{calls++;assert.equal(config.method,'post');return ok(config,{id_muestra:99,physical_compatibility:{status:'NO_ACQUISITION_SERIES'}});};
  await ctx.subirImagenes();assert.equal(calls,1);assert.equal(ctx.imagenesPreview[0].compatibility.status,'NO_ACQUISITION_SERIES');
});

test('series upload choices exclude archived profiles, series and retired calibrations',async()=>{
  auth.user=sessionFixture();const ctx=context(Series,{patientId:1,disabled:false});
  api.defaults.adapter=async config=>ok(config,config.url.includes('acquisition-series')
    ? [series,{...series,id:4,archived_at:'now'},{...series,id:5,acquisition_profile:9},{...series,id:6,calibration:9}]
    : config.url.includes('profiles') ? [profile,{...profile,id:9,archived_at:'now'}]
    : [calibration,{...calibration,id:9,status:'RETIRED'}]);
  await ctx.load();assert.deepEqual(ctx.series.map(item=>item.id),[series.id]);assert.deepEqual(ctx.profiles.map(item=>item.id),[profile.id]);
});

// ── AcquisitionSeriesCreateForm shared component tests ──────────────────────

test('T-A1: patientId is supplied by parent and form has no patient field',async()=>{
  const html=await renderToString(createSSRApp({...CreateForm,watch:{},data:()=>({...CreateForm.data(),profiles:[profile],calibrations:[calibration]})},{patientId:1}));
  // Patient must not be editable — no patient input/select rendered by the form itself
  assert.doesNotMatch(html,/Paciente<input|Paciente<select/);
  // But form fields are present
  assert.match(html,/Nombre/);assert.match(html,/Configuración/);assert.match(html,/Calibración/);
});

test('T-A2: profile and calibration are loaded fresh on every mount',async()=>{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config.url);
    return ok(config,config.url.includes('profiles')?[profile]:[calibration]);};
  const ctx=context(CreateForm,{patientId:1});await ctx.load();
  const profileCalls=calls.filter(u=>u.includes('acquisition-profiles')).length;
  const calCalls=calls.filter(u=>u.includes('calibrations')).length;
  assert.equal(profileCalls,1);assert.equal(calCalls,1);
  // Second load (simulating re-mount) fetches again
  await ctx.load();
  assert.equal(calls.filter(u=>u.includes('acquisition-profiles')).length,2);
});

test('T-A3: create POST sends correct payload with patient from prop',async()=>{
  const ctx=context(CreateForm,{patientId:5});ctx.profiles=[profile];ctx.calibrations=[calibration];
  ctx.form={label:'My Series',acquisition_profile:1,calibration:2,acquisition_date:'2026-01-01'};
  let sent;api.defaults.adapter=async config=>{sent=JSON.parse(config.data);return ok(config,{...series,id:10,patient:5});};
  await ctx.create();
  assert.equal(sent.patient,5);assert.equal(sent.label,'My Series');assert.equal(sent.acquisition_profile,1);assert.equal(sent.calibration,2);assert.equal(sent.acquisition_date,'2026-01-01');
});

test('T-A4: successful creation emits created with full series object',async()=>{
  const ctx=context(CreateForm,{patientId:1});ctx.profiles=[profile];ctx.calibrations=[calibration];
  ctx.form={label:'New',acquisition_profile:1,calibration:'',acquisition_date:''};
  const created={...series,id:20};api.defaults.adapter=async config=>ok(config,created);
  await ctx.create();
  const createdEvent=ctx.events.find(([name])=>name==='created');
  assert.ok(createdEvent,'created event not emitted');assert.deepEqual(createdEvent[1],created);
});

test('T-A5: failed creation displays error and does not emit created',async()=>{
  const ctx=context(CreateForm,{patientId:1});ctx.profiles=[profile];ctx.calibrations=[calibration];
  ctx.form={label:'Fail',acquisition_profile:1,calibration:'',acquisition_date:''};
  api.defaults.adapter=async()=>{throw {response:{status:400,data:{label:['This field is required.']}}};};
  await ctx.create();
  assert.ok(!ctx.events.find(([name])=>name==='created'),'created must not emit on failure');
  assert.ok(ctx.error,'error message must be set');
});

test('T-A6: cancel resets form and emits cancel',async()=>{
  const ctx=context(CreateForm,{patientId:1});
  ctx.form={label:'Draft',acquisition_profile:1,calibration:'',acquisition_date:''};
  ctx.cancel();
  assert.equal(ctx.form.label,'');assert.equal(ctx.form.acquisition_profile,'');
  const cancelEvent=ctx.events.find(([name])=>name==='cancel');
  assert.ok(cancelEvent,'cancel event not emitted');
});

test('T-A7: busy=true emitted before POST and busy=false in finally',async()=>{
  const ctx=context(CreateForm,{patientId:1});ctx.profiles=[profile];ctx.calibrations=[calibration];
  ctx.form={label:'New',acquisition_profile:1,calibration:'',acquisition_date:''};
  let busyStates=[];api.defaults.adapter=async config=>{busyStates.push(ctx.busy);return ok(config,{...series,id:30});};
  await ctx.create();
  const emittedBusy=ctx.events.filter(([name])=>name==='busy').map(([,v])=>v);
  assert.ok(emittedBusy.includes(true),'busy=true must be emitted');
  assert.ok(emittedBusy.includes(false),'busy=false must be emitted');
  assert.equal(ctx.busy,false,'busy must be false after completion');
  assert.ok(busyStates[0],'busy must be true during POST');
});

test('T-A8: create form renders session identity and hides form when not operator.ready',async()=>{
  auth.user={...sessionFixture()};
  const html=await renderToString(createSSRApp({...CreateForm,watch:{},data:()=>({...CreateForm.data(),profiles:[profile],calibrations:[calibration]})},{patientId:1}));
  assert.match(html,/Sesión:/);
  auth.user=null;
  const htmlUnauth=await renderToString(createSSRApp({...CreateForm,watch:{},data:()=>({...CreateForm.data()})},{patientId:1}));
  assert.doesNotMatch(htmlUnauth,/Guardar serie/);
});

// ── AcquisitionSeriesSelector regression tests after extraction ───────────────

test('T-A9: selector creation works after extraction — series added and selected',async()=>{
  const ctx=context(Series,{patientId:1,disabled:false});
  ctx.series=[{...series,id:1}];ctx.profiles=[profile];ctx.calibrations=[calibration];
  const newSeries={...series,id:99};ctx.onCreated(newSeries);
  assert.equal(ctx.selectedId,99);assert.ok(ctx.series.some(s=>s.id===99));
  assert.ok(!ctx.showForm,'form must close after creation');
});

test('T-A10: selector dirty=true while form open, dirty=false after cancel; busy propagated',async()=>{
  const ctx=context(Series,{patientId:1,disabled:false});
  assert.equal(ctx.dirty,false);
  ctx.showForm=true;assert.equal(ctx.dirty,true);
  ctx.showForm=false;assert.equal(ctx.dirty,false);
  // busy propagation: onBusy sets this.busy which the watcher emits
  ctx.onBusy(true);assert.equal(ctx.busy,true);
  ctx.onBusy(false);assert.equal(ctx.busy,false);
  // change event emitted after creation
  const events=[];ctx.$emit=(name,val)=>events.push([name,val]);
  ctx.series=[];ctx.onCreated({...series,id:88});
  assert.ok(events.some(([n])=>n==='change'),'change must be emitted after creation');
});
