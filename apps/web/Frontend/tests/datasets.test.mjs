import assert from 'node:assert/strict';
import {after,test} from 'node:test';
import {fileURLToPath} from 'node:url';
import {createServer} from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import {createSSRApp,reactive} from 'vue';
import {renderToString} from '@vue/server-renderer';
const server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,plugins:[vuePlugin()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'});
const keep=setInterval(()=>{},1000);after(async()=>{clearInterval(keep);await server.close();});
const {default:View}=await server.ssrLoadModule('/src/views/DatasetsView.vue');
const {default:Lookup}=await server.ssrLoadModule('/src/components/registration/PatientLookup.vue');
const {default:App}=await server.ssrLoadModule('/src/App.vue');
const {default:api}=await server.ssrLoadModule('/src/services/apiClient.js');
const {auth}=await server.ssrLoadModule('/src/services/auth.js');
auth.user={id:1,role:'ADMIN',institution:{id:1},must_change_password:false};
const patient=(id,code)=>({id,initials:'EJT',identificacion:code,identity_mode:'PSEUDONYMIZED'});
const draft={id:'test-uuid',name:'Synthetic',description:'',status:'DRAFT',institution_id:1,version:1,characterization_version:'2.2',units_mode:'PIXELS',config:{classes:['Class A'],features:['nucleus_area'],validated_only:true},patients:[{patient_id:8,class_label:'Class A',identity:patient(8,'A'),local_id:'P001'}]};
const summary={selected_patient_count:3,included_patient_count:2,zero_row_patient_count:1,patients:3,samples:2,excluded_samples:1,rows:5,nuclei:3,mn_associations:4,class_counts:{A:{patients:1,samples:1,rows:2},B:{patients:1,samples:1,rows:3}},provisional_count:2,exclusion_counts:{NO_PHYSICAL_VALUES:1}};
const preview={version:1,preview_hash:'stable-hash',summary,columns:['ID_paciente','Area_px2'],patients:[],exclusions:[{sample:'P001_IMG001',reason:'NO_PHYSICAL_VALUES',description:'Faltan valores físicos.'}]};
const generated={...draft,status:'GENERATED',version:2,summary,exclusions:preview.exclusions,manifest:{split_group:'patient',content_hash:'hash'},row_count:5,patient_count:2};
function ctx(){const c=reactive({...View.data(),$emit:()=>{}});for(const [k,f] of Object.entries(View.methods))c[k]=f.bind(c);for(const [k,f] of Object.entries(View.computed))Object.defineProperty(c,k,{get:()=>f.call(c)});return c;}
const render=data=>renderToString(createSSRApp({...View,data:()=>({...View.data(),...data})}));
const ok=(config,data)=>({config,data,status:200,statusText:'OK',headers:{}});

test('module list and existing navigation expose dataset section',async()=>{
 const html=await render({list:{results:[{...draft,patient_count:1,row_count:0}],count:1}});assert.match(html,/Conjuntos de datos/);assert.match(html,/Synthetic/);assert.match(html,/Nuevo conjunto/);assert.match(html,/por paciente, no por fila/);
 assert.equal(App.components.DatasetsView,View);
});
test('PatientLookup keeps explicit PK membership and duplicate initials distinct',()=>{
 assert.equal(View.components.PatientLookup,Lookup);const c=ctx();c.newDraft();c.addPatient(patient(8,'A'));c.addPatient(patient(37,'B'));c.addPatient(patient(8,'A'));
 assert.deepEqual(c.form.patients.map(p=>p.patient_id),[8,37]);assert.ok(c.form.patients.every(p=>p.class_label===''));
 c.form.patients[0].class_label='Defined label';assert.equal(c.payload().patients[0].class_label,'Defined label');assert.equal(c.payload().patients[0].patient_id,8);
 c.removePatient(8);assert.deepEqual(c.form.patients.map(p=>p.patient_id),[37]);
});
test('draft create and update are explicit and retain server version',async()=>{
 const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,config.method==='get'?{results:[],count:0}:draft);};
 const c=ctx();c.newDraft();c.form.name='Synthetic';c.addPatient(patient(8,'A'));c.form.patients[0].class_label='Class A';assert.equal(await c.save(),true);assert.equal(c.current.id,'test-uuid');assert.equal(c.dirty,false);assert.equal(calls[0].method,'post');
 c.form.description='changed';await c.save();assert.equal(calls[2].method,'put');assert.equal(JSON.parse(calls[2].data).version,1);
});
test('version physical controls filters and feature edits invalidate confirmation',async()=>{
 const c=ctx();c.accept(draft);c.form.units_mode='BOTH';c.form.characterization_version='2.1';c.versionChanged();assert.equal(c.form.units_mode,'PIXELS');
 c.form.validated_only=false;c.form.features=['nucleus_perimeter'];assert.equal(c.dirty,true);assert.equal(c.payload().validated_only,false);
 const html=await render({current:draft,form:{...c.form},options:{versions:['2.1','2.2'],features:[],unavailable:['Solidez']}});assert.match(html,/<option value="PHYSICAL" disabled[^>]*>Físicas/);assert.match(html,/Solo VALIDADA/);assert.match(html,/Solidez/);
});
test('preview shows row grain exclusions class balance provisional and needs confirmation',async()=>{
 const c=ctx();c.accept({...draft,units_mode:'BOTH'});c.preview=preview;
 const html=await render({current:c.current,form:c.form,saved:JSON.stringify(c.form),preview});assert.match(html,/5 filas/);assert.match(html,/3 núcleos/);assert.match(html,/4 asociaciones MN/);assert.match(html,/NO_PHYSICAL_VALUES/);assert.match(html,/calibración provisional/);assert.match(html,/snapshot generado será inmutable/);
 const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,preview);};await c.generate();assert.equal(calls.length,0);
 await c.previewDataset();assert.equal(c.preview.preview_hash,'stable-hash');assert.equal(c.confirmed,false);
});
test('generate sends reviewed hash and freezes display without scientific calls',async()=>{
 const c=ctx();c.accept(draft);c.preview=preview;c.confirmed=true;const calls=[];
 api.defaults.adapter=async config=>{calls.push(config);return ok(config,config.method==='post'?generated:{results:[generated],count:1});};await c.generate();
 assert.deepEqual(JSON.parse(calls[0].data),{version:1,preview_hash:'stable-hash',confirm:true});assert.equal(c.current.status,'GENERATED');assert.ok(calls.every(c=>!c.url.includes('segmentar')&&!c.url.includes('caracterizar')));
 const html=await render({current:generated});assert.match(html,/Configuración inmutable/);assert.match(html,/Descargar CSV/);assert.match(html,/Descargar Excel/);assert.match(html,/Descargar manifiesto/);assert.doesNotMatch(html,/Guardar borrador|2. Pacientes y clases/);
});
test('stale generation discards preview and requires review again',async()=>{
 const c=ctx();c.accept(draft);c.preview=preview;c.confirmed=true;api.defaults.adapter=async()=>{throw {response:{status:409,data:{code:'PREVIEW_CHANGED',detail:'Los datos cambiaron.'}}};};await c.generate();assert.equal(c.preview,null);assert.equal(c.confirmed,false);assert.match(c.error,/PREVIEW_CHANGED/);
});
test('reviewer has consultation and download but no create or generation controls',async()=>{
 auth.user={...auth.user,role:'REVIEWER'};try{const html=await render({current:generated});assert.match(html,/Descargar CSV/);assert.doesNotMatch(html,/Nuevo conjunto|Guardar borrador|Generar snapshot/);const c=ctx();c.newDraft();assert.equal(c.current,null);}finally{auth.user={...auth.user,role:'ADMIN'};}
});


test('dataset classes reject empty or equivalent names and patient assignment uses select',async()=>{
 const c=ctx();c.newDraft();c.newClass='  Diabetes+Ca ';c.addClass();assert.deepEqual(c.form.classes,['Diabetes+Ca']);
 c.newClass='DIABETES+CA';c.addClass();assert.match(c.error,/Ya existe una clase equivalente/);assert.equal(c.form.classes.length,1);
 c.newClass='   ';c.addClass();assert.match(c.error,/no puede estar vacío/);
 c.addPatient(patient(8,'A'));c.form.patients[0].class_label='Diabetes+Ca';
 assert.deepEqual(c.payload().classes,['Diabetes+Ca']);
 const html=await render({current:c.current,form:c.form});assert.match(html,/Clases del conjunto/);assert.match(html,/<select[^>]*><option value=""[^>]*>Seleccione clase/);assert.match(html,/Diabetes\+Ca/);
});
test('patient counts zero-row warning localized units dates and human feature labels',async()=>{
 const c=ctx();c.accept(draft);c.preview=preview;
 const html=await render({current:c.current,form:c.form,saved:JSON.stringify(c.form),preview});
 assert.match(html,/Pacientes seleccionados: 3/);assert.match(html,/Pacientes incluidos: 2/);assert.match(html,/Pacientes sin datos elegibles: 1/);assert.match(html,/no aporta\(n\) datos elegibles/);
 assert.equal(c.unitLabel('PIXELS'),'Píxeles');assert.equal(c.unitLabel('PHYSICAL'),'Físicas');assert.equal(c.unitLabel('BOTH'),'Ambas');
 const date='2026-10-28T19:42:17.088644Z';assert.equal(c.formatDate(date),new Date(date).toLocaleString('es-MX',{dateStyle:'short',timeStyle:'short'}));assert.ok(!c.formatDate(date).includes('T19:'));
 assert.equal(c.featureLabel('nucleus_area','BOTH'),'Área núcleo (px² / µm²)');assert.equal(c.featureLabel('mn_eccentricity','PHYSICAL'),'Excentricidad micronúcleo');
 const frozen=await render({current:{...generated,units_mode:'PHYSICAL',config:{features:['nucleus_area','centroid_distance'],validated_only:true}}});assert.match(frozen,/Área núcleo \(µm²\)/);assert.match(frozen,/Distancia entre centroides MN–núcleo \(µm\)/);assert.match(frozen,/Físicas/);assert.doesNotMatch(frozen,/Variables: nucleus_area/);
});
