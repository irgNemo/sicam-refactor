import assert from 'node:assert/strict';
import {after,test} from 'node:test';
import {fileURLToPath} from 'node:url';
import {createServer} from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import {createSSRApp,reactive} from 'vue';
import {renderToString} from '@vue/server-renderer';
const server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,plugins:[vuePlugin()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'});
const keepAlive=setInterval(()=>{},1000);after(async()=>{clearInterval(keepAlive);await server.close();});
const {default:View}=await server.ssrLoadModule('/src/components/registration/RecordManagement.vue');
const {default:Lookup}=await server.ssrLoadModule('/src/components/registration/PatientLookup.vue');
const {default:SideBar}=await server.ssrLoadModule('/src/components/SideBar.vue');
const {compactIdentifier,compactFilename,countLabel}=await server.ssrLoadModule('/src/domain/compactPresentation.js');
const {default:CompactValue}=await server.ssrLoadModule('/src/components/registration/CompactValue.vue');
const {default:Registro}=await server.ssrLoadModule('/src/views/RegistroView.vue');
const {auth}=await server.ssrLoadModule('/src/services/auth.js');
const {default:api}=await server.ssrLoadModule('/src/services/apiClient.js');
auth.user={id:1,role:'ADMIN',institution:{id:1},must_change_password:false};
function context(view=View){const c=reactive({...view.data(),$emit:()=>{}});for(const [k,f] of Object.entries(view.methods))c[k]=f.bind(c);for(const [k,f] of Object.entries(view.computed || {}))Object.defineProperty(c,k,{get:()=>f.call(c)});return c;}
const render=(data={},view=View)=>renderToString(createSSRApp({...view,data:()=>({...view.data(),...data})}));
const image=(id=1,patient=1)=>({id,type:'SALIVA',resource:'muestras',filename:`test-${id}.png`,patient_id:patient,patient:`Paciente #${patient}`,case_id:1,analysis_id:1,dimensions:{width:32,height:32},mode:'RGB',series:null,characterization_count:0,archived:false,compatibility:{status:'NO_ACQUISITION_SERIES',compatible_for_physical_units:false}});
const series={id:7,label:'TEST series',profile:{name:'TEST profile',width:32,height:32,mode:'RGB'},calibration:{label:'TEST cal',status:'PROVISIONAL'}};
const ok=(config,data)=>({config,data,status:200,statusText:'OK',headers:{}});
const turn=()=>new Promise(resolve=>setImmediate(resolve));

test('integrated modes preserve creation sections and use guarded switching',async()=>{
 const html=await render({},Registro);assert.match(html,/Nuevo registro/);assert.match(html,/Gestionar registros/);assert.doesNotMatch(html,/Gestionar registros existentes/);assert.match(html,/Nuevo paciente/);
 const c=context(Registro);c.confirmLeave=()=>false;c.requestMode('manage');assert.equal(c.recordMode,'new');c.confirmLeave=()=>true;c.formPaciente.nombre='unsaved';c.requestMode('manage');assert.equal(c.formPaciente.nombre,'unsaved');assert.equal(c.recordMode,'manage');c.requestMode('new');assert.equal(c.recordMode,'new');
});
test('management tabs and clean empty states render',async()=>{
 for(const [resource,text] of [['patients','No se encontraron pacientes.'],['cases','No se encontraron casos.'],['images','No se encontraron imágenes.']]){const html=await render({resource});assert.ok(html.includes(text));for(const label of ['Pacientes','Casos','Imágenes'])assert.ok(html.includes(label));assert.doesNotMatch(html,/<table/);}
 assert.match(await render({resource:'images',seriesFilter:'none'}),/No hay imágenes sin serie/);
});
test('patient and case lists show technical identifiers counts and lifecycle',async()=>{
 let html=await render({rows:[{id:1,label:'EJT',identificacion:'P-0008',identity_mode:'PSEUDONYMIZED',case_count:2,image_count:4,archived:false}]});assert.match(html,/Pseudonimizado/);assert.doesNotMatch(html,/PSEUDONYMIZED/);assert.match(html,/2 casos/);assert.match(html,/Ver imágenes/);
 html=await render({resource:'cases',rows:[{id:2,label:'Caso #2',patient_id:1,patient:'Paciente #1',analysis_count:2,image_count:4,archived:true}]});assert.match(html,/Caso #2/);assert.match(html,/ARCHIVADA/);
});
test('image list includes dimensions context physical and characterization state',async()=>{
 const html=await render({resource:'images',rows:[image()]});for(const text of ['32 × 32 · RGB','Caso #1','Análisis #1','Sin serie','Sin caracterización','Seleccionar test-1.png'])assert.ok(html.includes(text));
});
test('selection is restricted to visible page and excludes archived images',()=>{
 const c=context();c.rows=[image(),{...image(2),archived:true},image(3,2)];c.selectPage();assert.equal(c.selected.length,2);assert.equal(c.mixedPatients,true);c.toggle(c.rows[2]);assert.equal(c.mixedPatients,false);c.clearSelection();assert.deepEqual(c.selected,[]);
});
test('mixed patients explain the block and reviewer has no assignment control',async()=>{
 const c=context();c.rows=[image(),image(2,2)];c.selectPage();assert.match(await render({resource:'images',rows:c.rows,selected:c.selected}),/pertenecen a pacientes diferentes/);
 auth.user={...auth.user,role:'REVIEWER'};try{assert.doesNotMatch(await render({resource:'images',rows:[image()]}),/Asignar a serie|Seleccionar test/);}finally{auth.user={...auth.user,role:'ADMIN'};}
});
test('server filters pagination and stale reads cannot replace newer result',async()=>{
 const calls=[];api.defaults.adapter=config=>new Promise(resolve=>calls.push({config,resolve:data=>resolve(ok(config,data))}));
 const c=context();c.resource='images';c.patient=5;c.seriesFilter='none';const first=c.load();await turn();c.search='new';const second=c.load();await turn();
 assert.equal(calls[1].config.params.patient,5);assert.equal(calls[1].config.params.series,'none');calls[1].resolve({count:1,results:[image(2)]});await second;calls[0].resolve({count:1,results:[image(1)]});await first;assert.equal(c.rows[0].id,2);
});
test('series selection remains explicit even with one option',async()=>{
 api.defaults.adapter=async config=>ok(config,[series]);const c=context();c.rows=[image()];c.selectPage();await c.openAssignment();assert.equal(c.target,'');assert.equal(c.series.length,1);assert.equal(c.preview,null);
});
test('preview warnings display provisional and unavailable physical units',async()=>{
 const results=[{id:1,type:'SALIVA',compatibility:{status:'COMPATIBLE_PROVISIONAL',compatible_for_physical_units:true}},{id:2,type:'SALIVA',compatibility:{status:'RESOLUTION_MISMATCH',compatible_for_physical_units:false}}];
 const html=await render({resource:'images',rows:[image(),image(2)],selected:['SALIVA:1','SALIVA:2'],assignmentOpen:true,series:[series],target:7,preview:{series,results,compatible_count:1,preview_token:'x'}});assert.match(html,/PROVISIONAL/);assert.match(html,/permanecerán no disponibles/);assert.match(html,/1 compatible/);assert.match(html,/Confirmo la serie/);
});
test('assignment requires confirmation prevents duplicate submission and does not calculate science',async()=>{
 let resolve;const calls=[];api.defaults.adapter=config=>{calls.push(config);if(config.method==='post')return new Promise(r=>{resolve=data=>r(ok(config,data));});return Promise.resolve(ok(config,{count:1,results:[image()]}));};
 const c=context();c.rows=[image()];c.selectPage();c.target=7;c.preview={preview_token:'signed'};await c.assign();assert.equal(calls.length,0);
 c.confirmed=true;const pending=c.assign();await turn();await c.assign();assert.equal(calls.length,1);const body=JSON.parse(calls[0].data);assert.equal(body.confirm,true);assert.equal(body.preview_token,'signed');resolve({series,compatible_count:1});await pending;
 assert.ok(calls.every(x=>!x.url.includes('caracteriz')&&!x.url.includes('segmentar')));assert.match(c.message,/provisional/);assert.equal(c.selected.length,0);
});
test('conflict discards preview and requires a new confirmation',async()=>{
 api.defaults.adapter=async()=>{throw {response:{status:409,data:{code:'SERIES_ALREADY_ASSIGNED',detail:'Esta imagen ya pertenece a otra serie.'}}};};const c=context();c.rows=[image()];c.selectPage();c.target=7;c.preview={preview_token:'signed'};c.confirmed=true;await c.assign();assert.equal(c.preview,null);assert.equal(c.confirmed,false);assert.match(c.error,/otra serie/);
});
test('tab changes and physical-page filter discard selection',()=>{
 const c=context();c.load=()=>{c.clearSelection();};c.rows=[image()];c.selectPage();c.changeTab('cases');assert.equal(c.resource,'cases');assert.equal(c.selected.length,0);c.rows=[image(),{...image(2),compatibility:{status:'COMPATIBLE'}}];c.physical='COMPATIBLE';c.selectPage();assert.deepEqual(c.selected,['SALIVA:2']);
});

const identity=(id,technical)=>({id,initials:'EJT',identificacion:technical,identity_mode:'PSEUDONYMIZED',external_id_namespace:'TEST',external_patient_id:technical});
test('lookup duplicate initials require explicit selection and show distinct technical identities',async()=>{
 const patients=[identity(8,'A'),identity(37,'B')];const events=[];const c=context(Lookup);c.$emit=(...args)=>events.push(args);
 api.defaults.adapter=async config=>ok(config,{count:2,results:patients});await c.search('ejt');assert.equal(events.length,0);assert.equal(c.results.length,2);
 const html=await render({query:'ejt',results:patients,count:2},Lookup);assert.match(html,/title="A"/);assert.match(html,/title="B"/);assert.match(html,/Seleccione un paciente/);assert.doesNotMatch(html,/PSEUDONYMIZED/);
 c.select(c.results[1]);assert.equal(events[0][1].id,37);c.clear();assert.equal(events[1][1],null);
});
test('lookup loading empty pagination and failures are visible',async()=>{
 assert.match(await render({loading:true},Lookup),/Buscando pacientes/);
 assert.match(await render({query:'no-match'},Lookup),/No se encontraron pacientes/);
 const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,{count:21,results:[identity(22,'C')]});};
 const c=context(Lookup);c.query='ejt';await c.load(2);assert.equal(calls[0].params.page,2);assert.equal(calls[0].params.q,'ejt');assert.equal(c.page,2);
 api.defaults.adapter=async()=>{throw Error('offline');};await c.load(1);assert.match(c.error,/No se pudieron/);assert.equal(c.loading,false);
});
test('lookup stale response cannot overwrite newer search or cleared selection',async()=>{
 const calls=[];api.defaults.adapter=config=>new Promise(resolve=>calls.push({resolve:data=>resolve(ok(config,data))}));
 const c=context(Lookup);const first=c.search('A');await turn();const second=c.search('B');await turn();calls[1].resolve({count:1,results:[identity(37,'B')]});await second;calls[0].resolve({count:1,results:[identity(8,'A')]});await first;assert.equal(c.results[0].id,37);
 const third=c.search('C');await turn();c.clear();calls[2].resolve({count:1,results:[identity(40,'C')]});await third;assert.equal(c.results.length,0);
});
test('patient selection resets case and uses actual selected PK for cases and images',async()=>{
 const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,{count:1,results:config.url.includes('/cases/')?[{id:9,label:'Caso #9'}]:[image(2,37)]});};
 const c=context();c.resource='images';c.caseId=4;c.caseOptions=[{id:4}];c.selectPatient(identity(37,'B'));await turn();
 assert.equal(c.patient,37);assert.equal(c.caseId,'');assert.equal(c.caseOptions[0].id,9);assert.ok(calls.every(x=>x.params.patient===37));assert.equal(calls.find(x=>x.url.includes('/images/')).params.case,'');
 c.caseId=9;await c.load();assert.equal(calls.at(-1).params.case,9);
 c.selectPatient(null);await turn();assert.equal(c.caseId,'');assert.equal(c.caseOptions.length,0);
});
test('patient change discards previous pending case options and supports case pagination',async()=>{
 const calls=[];api.defaults.adapter=config=>new Promise(resolve=>calls.push({config,resolve:data=>resolve(ok(config,data))}));
 const c=context();c.filter=()=>{};c.selectPatient(identity(8,'A'));await turn();c.selectPatient(identity(37,'B'));await turn();
 calls[1].resolve({count:21,results:[{id:9,label:'Caso #9'}]});await turn();calls[0].resolve({count:1,results:[{id:4}]});await turn();assert.equal(c.caseOptions[0].id,9);
 const more=c.loadCases(2);await turn();calls[2].resolve({count:21,results:[{id:10}]});await more;assert.deepEqual(c.caseOptions.map(c=>c.id),[9,10]);
});
test('context renders meaningful identity and dependent case selector without numeric patient inputs',async()=>{
 const row={...image(),patient_identity:identity(8,'P-0008')};
 const html=await render({resource:'images',rows:[row],selectedPatient:row.patient_identity,patient:8,caseOptions:[{id:9,label:'Caso #9'}]});
 assert.match(html,/EJT/);assert.match(html,/title="P-0008"/);assert.match(html,/Todos los casos/);assert.match(html,/Caso #9/);assert.doesNotMatch(html,/Paciente \(ID\)|Caso \(ID\)/);
 const empty=await render({resource:'images'});assert.match(empty,/Caso<select disabled/);
});
test('Segmentacion shares lookup while selection continues emitting real IDs',()=>{
 assert.equal(SideBar.components.PatientLookup,Lookup);
 const events=[];const select=SideBar.methods.seleccionarPaciente.bind({$emit:(...args)=>events.push(args)});
 select(identity(37,'B'));select({id_paciente:8});select(null);
 assert.deepEqual(events,[['select-patient',37],['select-patient',8],['select-patient',null]]);
});

test('compact IDs retain full accessible values and expand colliding suffixes',async()=>{
 const a='ext:aaaaaaaaaaaaaaaaaa12acf',b='ext:bbbbbbbbbbbbbbbbbb12acf';
 const peers=[a,b];assert.notEqual(compactIdentifier(a,peers),compactIdentifier(b,peers));assert.equal(compactIdentifier('P-0008'),'P-0008');assert.equal(a,'ext:aaaaaaaaaaaaaaaaaa12acf');
 const html=await renderToString(createSSRApp(CompactValue,{value:a,peers}));assert.ok(html.includes(`title="${a}"`));assert.ok(html.includes(`aria-label="${a}"`));assert.match(html,/tabindex="0"/);assert.ok(html.includes(compactIdentifier(a,peers)));
 const candidates=await render({query:'ejt',results:[identity(8,a),identity(37,b)],count:2},Lookup);assert.ok(candidates.includes(compactIdentifier(a,peers)));assert.ok(candidates.includes(compactIdentifier(b,peers)));assert.match(candidates,/Seleccione un paciente/);
});
test('singular and plural labels reflect counts in management',async()=>{
 assert.equal(countLabel(1,'análisis','análisis'),'1 análisis');assert.equal(countLabel(2,'análisis','análisis'),'2 análisis');
 const one=await render({rows:[{...identity(8,'A'),case_count:1,image_count:1}]});assert.match(one,/1 caso · 1 imagen/);
 const two=await render({rows:[{...identity(8,'A'),case_count:2,image_count:2}]});assert.match(two,/2 casos · 2 imágenes/);
 const img=await render({resource:'images',rows:[{...image(),characterization_count:1}],selected:['SALIVA:1']});assert.match(img,/1 caracterización/);assert.doesNotMatch(img,/1 caracterizaciones/);assert.match(img,/1 imagen seleccionada/);
 const plural=await render({resource:'images',rows:[{...image(),characterization_count:2}]});assert.match(plural,/2 caracterizaciones/);
});
test('case rows show the case PK once and compact patient identity',async()=>{
 const patient=identity(8,'ext:aaaaaaaaaaaaaaaaaa123456');
 const html=await render({resource:'cases',rows:[{id:77,label:'Caso #77',patient_identity:patient,analysis_count:1,image_count:1}]});
 assert.match(html,/Caso #77/);assert.doesNotMatch(html,/>ID 77</);assert.ok(html.includes(compactIdentifier(patient.identificacion)));assert.match(html,/1 análisis · 1 imagen/);
});
test('filenames compact without losing full accessible value or visible actions',async()=>{
 const filename='020b5358f7cd434a83edf6f3c7a68801.jpg';assert.equal(compactFilename(filename),'020b5358…a68801.jpg');
 const html=await render({resource:'images',rows:[{...image(),filename,series}]});
 assert.ok(html.includes(`title="${filename}"`));assert.ok(html.includes(`aria-label="${filename}"`));assert.ok(html.includes(compactFilename(filename)));
 assert.match(html,/>Estado</);assert.match(html,/>Acciones</);assert.match(html,/Más acciones/);assert.match(html,/TEST profile · TEST series/);assert.match(html,/class="actions-column"/);
});
test('Segmentacion selected patient has one change action and returns to clean lookup',async()=>{
 const patient={...identity(8,'ext:aaaaaaaaaaaaaaaaaa123456'),id_paciente:8,fecha_nacimiento:'2000-01-01'};
 const selected=await render({pacienteSeleccionado:patient,loading:false},SideBar);
 assert.equal((selected.match(/Cambiar paciente/g)||[]).length,1);assert.doesNotMatch(selected,/Limpiar selección|Seleccione un paciente|Iniciales o identificador/);assert.match(selected,/Pseudonimizado/);assert.ok(selected.includes(compactIdentifier(patient.identificacion)));
 const events=[];SideBar.methods.cambiarPaciente.call({$emit:(...args)=>events.push(args)});assert.deepEqual(events,[['select-patient',null]]);
 const cleared=await render({pacienteSeleccionado:null,loading:false},SideBar);assert.match(cleared,/Iniciales o identificador/);assert.doesNotMatch(cleared,/Cambiar paciente|Seleccione un paciente/);
});

// ── RecordManagement creation workflow tests ─────────────────────────────────

test('T-R1: create button visible for ADMIN, hidden for REVIEWER',async()=>{
  auth.user={id:1,role:'ADMIN',institution:{id:1},must_change_password:false};
  const html=await render({resource:'images',assignmentOpen:true,series:[]});
  assert.match(html,/Crear serie para este paciente/);
  auth.user={...auth.user,role:'REVIEWER'};
  const htmlR=await render({resource:'images',assignmentOpen:true,series:[]});
  assert.doesNotMatch(htmlR,/Crear serie para este paciente/);
  auth.user={...auth.user,role:'ADMIN'};
});

test('T-R2: create button visible for OPERATOR',async()=>{
  auth.user={id:1,role:'OPERATOR',institution:{id:1},must_change_password:false};
  const html=await render({resource:'images',assignmentOpen:true,series:[]});
  assert.match(html,/Crear serie para este paciente/);
  auth.user={...auth.user,role:'ADMIN'};
});

test('T-R3: zero-series state still permits creation button',async()=>{
  const html=await render({resource:'images',assignmentOpen:true,series:[]});
  assert.match(html,/Crear serie para este paciente/);
  assert.match(html,/No hay series válidas/);
});

test('T-R4: existing series coexist with create button',async()=>{
  const html=await render({resource:'images',assignmentOpen:true,series:[series]});
  assert.match(html,/Crear serie para este paciente/);
  assert.match(html,/TEST series/);
});

test('T-R5: create button hidden while showSeriesForm is true',async()=>{
  const html=await render({resource:'images',assignmentOpen:true,series:[],showSeriesForm:true});
  assert.doesNotMatch(html,/Crear serie para este paciente/);
});

test('T-R6: onSeriesCreated re-fetches stricter series endpoint and selects eligible series',async()=>{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,config.url.includes('record-management/series')?[{...series,id:55}]:{count:1,results:[image()]});};
  const c=context();c.assignmentPatientId=1;c.assignmentOpen=true;const newSeries={id:55,label:'New'};
  await c.onSeriesCreated(newSeries);
  assert.ok(calls.some(x=>x.url.includes('record-management/series')),'must call record-management/series endpoint');
  assert.equal(c.target,55,'newly created eligible series must be selected');
  assert.ok(!c.showSeriesForm,'form must be closed');
});

test('T-R7: absent/non-eligible new series is not force-selected and shows message',async()=>{
  api.defaults.adapter=async config=>ok(config,config.url.includes('record-management/series')?[]:{count:1,results:[image()]});
  const c=context();c.assignmentPatientId=1;c.assignmentOpen=true;
  await c.onSeriesCreated({id:99,label:'Absent'});
  assert.equal(c.target,'','absent series must not be selected');
  assert.match(c.seriesCreationMessage,/no está disponible/);
});

test('T-R8: creation never calls preview or assignment endpoints',async()=>{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config.url);return ok(config,config.url.includes('record-management/series')?[{...series,id:60}]:{});};
  const c=context();c.assignmentPatientId=1;
  await c.onSeriesCreated({id:60});
  assert.ok(calls.every(u=>!u.includes('preview')&&!u.includes('assign')),'creation must not call preview or assign');
});

test('T-R9: preview is invalidated after series creation',async()=>{
  api.defaults.adapter=async config=>ok(config,config.url.includes('record-management/series')?[{...series,id:70}]:{});
  const c=context();c.assignmentPatientId=1;c.preview={preview_token:'old'};c.confirmed=true;
  await c.onSeriesCreated({id:70});
  assert.equal(c.preview,null,'preview must be null after creation');
  assert.equal(c.confirmed,false,'confirmed must be reset');
});

test('T-R10: closeAssignment resets showSeriesForm and assignmentPatientId',()=>{
  const c=context();c.assignmentOpen=true;c.showSeriesForm=true;c.assignmentPatientId=5;c.seriesCreationMessage='msg';
  c.closeAssignment();
  assert.equal(c.showSeriesForm,false);assert.equal(c.assignmentPatientId,null);assert.equal(c.seriesCreationMessage,'');
  assert.equal(c.assignmentOpen,false);
});

test('T-R11: onTargetChange closes creation form and invalidates preview',()=>{
  const c=context();c.showSeriesForm=true;c.preview={preview_token:'x'};c.confirmed=true;
  c.onTargetChange();
  assert.equal(c.showSeriesForm,false);assert.equal(c.preview,null);assert.equal(c.confirmed,false);
});

test('T-R12: existing assignment flow unchanged — preview then assign',async()=>{
  let resolve;const calls=[];api.defaults.adapter=config=>{calls.push(config);if(config.method==='post')return new Promise(r=>{resolve=data=>r(ok(config,data));});return Promise.resolve(ok(config,{count:1,results:[image()]}));};
  const c=context();c.rows=[image()];c.selectPage();c.target=7;c.preview={preview_token:'signed'};c.confirmed=true;
  const pending=c.assign();await turn();resolve({series,compatible_count:1});await pending;
  assert.ok(calls.some(x=>x.method==='post'&&x.url.includes('assign')),'assign endpoint must be called');
  assert.ok(calls.every(x=>!x.url.includes('caracteriz')),'characterization must not be called');
});
