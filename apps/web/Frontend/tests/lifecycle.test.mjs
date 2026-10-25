import assert from 'node:assert/strict';
import { after, beforeEach, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { createSSRApp } from 'vue';
import { renderToString } from '@vue/server-renderer';
const server = await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,plugins:[vuePlugin()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'});
const keepAlive=setInterval(()=>{},1000);after(async()=>{clearInterval(keepAlive);await server.close();});
const service=await server.ssrLoadModule('/src/services/lifecycle.js');
const {default:api}=await server.ssrLoadModule('/src/services/apiClient.js');
const {auth}=await server.ssrLoadModule('/src/services/auth.js');
const {default:Actions}=await server.ssrLoadModule('/src/components/lifecycle/LifecycleActions.vue');
const {default:Browser}=await server.ssrLoadModule('/src/components/lifecycle/LifecycleBrowser.vue');
const user=role=>({id:1,role,institution:{id:1},must_change_password:false});
const ok=(config,data)=>({config,data,status:200,headers:{},statusText:'OK'});
const preview=(actions=['ARCHIVE'])=>({resource_type:'muestrasaliva',id:'1',display:'muestrasaliva #1',allowed_actions:actions,recommended_action:actions[0],dependencies:{ResultadoSegmentacion:1,ResultadoCaracterizacion:1},media_files:[{filename:'synthetic.png'}],warnings:[]});
beforeEach(()=>{auth.user=user('ADMIN');});
function ctx(extra={}) { return {...Actions.data(),resource:'muestras',id:1,label:'Imagen #1',disabled:false,$emit:()=>{},...extra}; }

test('role visibility and archived filter are explicit',()=>{
  for(const role of ['ADMIN','OPERATOR','REVIEWER']) {
    assert.equal(service.canManageLifecycle(user(role)),role!=='REVIEWER');
    assert.deepEqual(service.archivedParams(user(role),true),role==='ADMIN'?{include_archived:'true'}:{});
  }
  assert.equal(service.canManageLifecycle({...user('ADMIN'),must_change_password:true}),false);
  assert.deepEqual(service.archivedParams(user('ADMIN'),false),{});
});
test('preview and execution use server contract, reason and explicit confirmation',async()=>{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,config.method==='get'?preview():{event_id:1});};
  const p=await service.inspectLifecycle('muestras',1);assert.deepEqual(p.allowed_actions,['ARCHIVE']);
  for(const action of ['ARCHIVE','RESTORE','RETIRE','HARD_DELETE']) {
    await service.applyLifecycle('muestras',1,action,'  Synthetic reason  ',true);
    assert.deepEqual(JSON.parse(calls.at(-1).data),{action,reason:'Synthetic reason',confirm:true});
  }
  assert.equal(calls[0].url,'/api/lifecycle/muestras/1/');
  for(const args of [['ARCHIVE','',true],['ARCHIVE','reason',false],['PURGE','reason',true]])assert.throws(()=>service.applyLifecycle('muestras',1,...args));
});
test('dependency dialog shows impact and never invents delete for a used sample',async()=>{
  const html=await renderToString(createSSRApp({...Actions,data:()=>({...Actions.data(),opened:true,preview:preview(),action:'ARCHIVE'})},{resource:'muestras',id:1,label:'Imagen #1'}));
  assert.match(html,/role="dialog"/);assert.match(html,/Segmentaciones/);assert.match(html,/Caracterizaciones/);assert.match(html,/synthetic.png/);assert.match(html,/Archivar/);
  assert.match(html,/Motivo/);assert.match(html,/Confirmo:/);assert.match(html,/históricas/);assert.doesNotMatch(html,/Eliminar permanentemente/);
});
test('safe delete, restore and retire each show their explicit consequence',async()=>{
  for(const action of ['HARD_DELETE','RESTORE','RETIRE']) {
    const html=await renderToString(createSSRApp({...Actions,data:()=>({...Actions.data(),opened:true,preview:preview([action]),action})},{resource:'muestras',id:1}));
    assert.ok(html.includes(service.actionLabels[action]));assert.ok(html.includes(service.consequences[action]));
  }
});
test('reviewer has no lifecycle action button',async()=>{
  auth.user=user('REVIEWER');assert.doesNotMatch(await renderToString(createSSRApp(Actions,{resource:'muestras',id:1})),/Más acciones/);
  auth.user=user('OPERATOR');assert.match(await renderToString(createSSRApp(Actions,{resource:'muestras',id:1})),/Más acciones/);
});
test('submit waits for reason and confirmation, no automatic action',async()=>{
  let requests=0;api.defaults.adapter=async config=>{requests++;return ok(config,{event_id:1});};
  const state=ctx({preview:preview(),action:'ARCHIVE',reason:'Creado/subido por error'});
  await Actions.methods.execute.call(state);assert.equal(requests,0);
  state.confirmed=true;await Actions.methods.execute.call(state);assert.equal(requests,1);assert.equal(state.opened,false);
});
test('conflict reloads dependency preview and requires a new confirmation',async()=>{
  const state=ctx({opened:true,preview:preview(['HARD_DELETE']),action:'HARD_DELETE',reason:'Duplicado',confirmed:true});
  let reads=0;state.load=async()=>{reads++;state.preview=preview(['ARCHIVE']);state.action='ARCHIVE';};
  api.defaults.adapter=async()=>{throw {response:{status:409,data:{code:'SCIENTIFIC_DEPENDENCIES_EXIST'}}};};
  await Actions.methods.execute.call(state);assert.equal(state.opened,true);assert.equal(state.confirmed,false);assert.equal(reads,1);assert.match(state.error,/dependencias/);assert.equal(state.action,'ARCHIVE');
});
test('restore conflicts identify unavailable parent or calibration',()=>{
  assert.match(service.lifecycleError({response:{data:{code:'PARENT_ARCHIVED'}}}),/superior/);
  assert.match(service.lifecycleError({response:{data:{code:'CALIBRATION_RETIRED'}}}),/retirada/);
  assert.match(service.lifecycleError({response:{status:404}}),/no está disponible/);
});
test('archived browsing uses admin history parameter and does not leak it to operator',async()=>{
  for(const role of ['ADMIN','OPERATOR']) {
    auth.user=user(role);let config;
    api.defaults.adapter=async c=>{config=c;return ok(c,[{id_paciente:1,display_name:'Synthetic',archived_at:'now'}]);};
    const state={...Browser.data(),includeArchived:true};await Browser.methods.load.call(state);
    assert.deepEqual(config.params,role==='ADMIN'?{include_archived:'true'}:{});assert.equal(state.rows.length,1);
  }
});
test('archived list labels individual and inherited archive separately',async()=>{
  const data=()=>({...Browser.data(),opened:true,rows:[{id_paciente:1,display_name:'Synthetic',archived_at:'now'},{id_paciente:2,display_name:'Child',operationally_active:false}]});
  const html=await renderToString(createSSRApp({...Browser,data}));assert.match(html,/Incluir archivados/);assert.match(html,/Archivado/);assert.match(html,/Oculto por archivo/);
});
