import assert from 'node:assert/strict';
import { after, beforeEach, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { createSSRApp } from 'vue';
import { renderToString } from '@vue/server-renderer';
const server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,plugins:[vuePlugin()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'});
const keepAlive=setInterval(()=>{},1000);after(async()=>{clearInterval(keepAlive);await server.close();});
const {auth}=await server.ssrLoadModule('/src/services/auth.js');
const service=await server.ssrLoadModule('/src/services/adminAudit.js');
const {default:api}=await server.ssrLoadModule('/src/services/apiClient.js');
const {default:Panel}=await server.ssrLoadModule('/src/components/administration/AdminAuditPanel.vue');
const {default:Admin}=await server.ssrLoadModule('/src/views/AdministrationView.vue');
const user=role=>({id:1,role,institution:{id:1,name:'Synthetic'},must_change_password:false});
const ok=(config,data)=>({config,data,status:200,headers:{},statusText:'OK'});
beforeEach(()=>{auth.user=user('ADMIN');});
const row={id:2,action:'HARD_DELETE',created_at:'2026-10-25T10:00:00Z',actor:{username:'synthetic',current_role:'ADMIN'},institution:{code:'TEST'},description:'muestrasaliva #67',reason:'Synthetic reason',is_test:true,target_deleted:true,metadata:{dependencies:{},media_cleanup:[{filename:'TEST_LIFECYCLE_test.png',sha256:'a'.repeat(64),status:'DELETED'}]}};

test('admin navigation exposes audit archives and health, with unauthorized rendering blocked',async()=>{
  assert.match(await renderToString(createSSRApp(Admin)),/Auditoría/);
  assert.match(await renderToString(createSSRApp(Admin)),/Archivados/);
  assert.match(await renderToString(createSSRApp(Admin)),/Diagnóstico/);
  for(const role of ['OPERATOR','REVIEWER']){auth.user=user(role);const html=await renderToString(createSSRApp(Panel,{mode:'events'}));assert.match(html,/No tiene acceso/);assert.doesNotMatch(html,/<table/);}
});
test('institution filter is platform-only and dates/actors/pagination reach API',async()=>{
  const filters={institution:2,date_from:'2026-10-01',actor:3,action:'ARCHIVE',target_type:'paciente',page:2,search:''};let config;
  api.defaults.adapter=async c=>{config=c;return ok(c,{count:0,results:[]});};
  await service.fetchAudit('events',filters,user('ADMIN'));assert.equal(config.params.institution,undefined);assert.equal(config.params.page,2);assert.equal(config.params.date_from,'2026-10-01');
  await service.fetchAudit('events',filters,{is_superuser:true});assert.equal(config.params.institution,2);
});
test('event detail remains readable after deletion without exposing arbitrary metadata',async()=>{
  const data=()=>({...Panel.data(),result:{count:1,results:[row]},detail:row});
  const html=await renderToString(createSSRApp({...Panel,data},{mode:'events'}));
  for(const text of ['Recurso eliminado','TEST','Synthetic reason','TEST_LIFECYCLE_test.png','SHA-256','Rol actual: ADMIN'])assert.ok(html.includes(text));
  assert.doesNotMatch(html,/Editar evento|Borrar evento/);
});
test('archive row reuses lifecycle inspector and retired calibration never offers unretire',async()=>{
  const rows=[{id:1,resource:'pacientes',description:'paciente #1',status:'ARCHIVED'},{id:2,resource:'calibrations',description:'calibration #2',status:'RETIRED'}];
  const html=await renderToString(createSSRApp({...Panel,data:()=>({...Panel.data(),result:{count:2,results:rows}})},{mode:'archived'}));
  assert.match(html,/Más acciones/);assert.match(html,/Sin reactivación administrativa/);assert.match(html,/RETIRED/);assert.doesNotMatch(html,/UNRETIRE|VALIDATED/);
});
test('archive filters use archived_by and preserve same page',async()=>{
  let config;api.defaults.adapter=async c=>{config=c;return ok(c,{count:1,results:[]});};
  const state={...Panel.data(),mode:'archived',page:3};state.filters={...state.filters,type:'muestras',actor:4,search:'69'};
  await Panel.methods.load.call(state);assert.equal(config.params.archived_by,4);assert.equal(config.params.actor,undefined);assert.equal(config.params.type,'muestras');assert.equal(config.params.search,'69');assert.equal(config.params.page,3);
});
test('pagination does not follow arbitrary URLs and resets when searching',async()=>{
  const state={page:1,detail:row,load:async()=>{}};
  await Panel.methods.changePage.call(state,1);assert.equal(state.page,2);assert.equal(state.detail,null);
  await Panel.methods.search.call(state);assert.equal(state.page,1);
});
test('file scan is explicit, diagnostic statuses are readable and non-mutating',async()=>{
  let config;api.defaults.adapter=async c=>{config=c;return ok(c,{status:'WARNING',scope:'INSTITUTION',issue_limit:100,checks:[{code:'MEDIA_REFERENCES',status:'WARNING',count:1,issues:[{resource_type:'muestrasaliva',id:7,field:'imagen'}]},{code:'PRODUCTION_MEDIA_ACCESS_CONTROL',status:'DEPLOYMENT_ACTION_REQUIRED',issues:[]}]});};
  const state={...Panel.data()};await Panel.methods.loadHealth.call(state,true);assert.equal(config.method,'get');assert.equal(config.params.check_files,'true');
  const html=await renderToString(createSSRApp({...Panel,data:()=>state},{mode:'health'}));assert.match(html,/Verificar archivos/);assert.match(html,/WARNING/);assert.match(html,/muestrasaliva #7/);assert.match(html,/DEPLOYMENT_ACTION_REQUIRED/);
});
test('stale responses cannot overwrite the current page',async()=>{
  let finish;api.defaults.adapter=c=>new Promise(resolve=>{finish=()=>resolve(ok(c,{count:9,results:[]}));});
  const state={...Panel.data(),mode:'events'};const promise=Panel.methods.load.call(state);await new Promise(resolve=>setTimeout(resolve,0));state.generation++;finish();await promise;assert.equal(state.result.count,0);
});
test('user administration exposes operational dates and last-admin explanation',async()=>{
  const html=await renderToString(createSSRApp(Admin));for(const text of ['Último login','Creación','Contraseña pendiente','último ADMIN'])assert.ok(html.includes(text));
});
