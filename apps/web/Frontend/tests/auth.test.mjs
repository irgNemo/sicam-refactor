import assert from 'node:assert/strict';
import { after, beforeEach, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vuePlugin from '@vitejs/plugin-vue';
import { createSSRApp } from 'vue';
import { renderToString } from '@vue/server-renderer';
const server = await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,plugins:[vuePlugin()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'});
const keepAlive=setInterval(()=>{},1000);after(async()=>{clearInterval(keepAlive);await server.close();delete globalThis.sessionStorage;});
const service=await server.ssrLoadModule('/src/services/auth.js');
const {default:api}=await server.ssrLoadModule('/src/services/apiClient.js');
const {default:App}=await server.ssrLoadModule('/src/App.vue');
const {default:TopBar}=await server.ssrLoadModule('/src/components/TopBar.vue');
const {default:Admin}=await server.ssrLoadModule('/src/views/AdministrationView.vue');
const {default:Registry}=await server.ssrLoadModule('/src/views/RegistroView.vue');
const {default:Acquisition}=await server.ssrLoadModule('/src/views/AdquisicionView.vue');
const {auth,can}=service;
const user=(role='OPERATOR', extra={})=>({id:1,username:'synthetic',first_name:'Synthetic',last_name:'Fixture',email:'fixture@example.invalid',role,institution:{id:1,code:'TEST',name:'Synthetic institution'},must_change_password:false,...extra});
const ok=(config,data)=>({config,data,status:200,headers:{},statusText:'OK'});
beforeEach(()=>{const storage=new Map();globalThis.sessionStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};auth.user=user();auth.ready=true;auth.error='';delete api.defaults.headers.common['X-CSRFToken'];});

test('role matrix distinguishes operator/reviewer/admin and forced password change',()=>{
  for(const capability of ['administer','infrastructure','register','validate','segment']) {
    assert.equal(can(capability,null),false);assert.equal(can(capability,user('ADMIN',{must_change_password:true})),false);
    assert.equal(can(capability,user('ADMIN')),true);assert.equal(can(capability,user(null,{is_superuser:true})),true);
  }
  assert.equal(can('register',user('REVIEWER')),false);assert.equal(can('validate',user('REVIEWER')),true);
  assert.equal(can('validate',user()),false);assert.equal(can('administer',user()),false);assert.equal(can('unrecognized',user()),false);
});
test('login bootstraps CSRF then rotates token, uses cookies and no Basic auth',async()=>{
  const calls=[];api.defaults.adapter=async config=>{calls.push(config);return ok(config,config.url.endsWith('/me/')?{user:null,csrf_token:'initial'}:{user:user('OPERATOR',{must_change_password:true}),csrf_token:'rotated'});};
  await service.login('synthetic','temporary-fixture');
  assert.deepEqual(calls.map(c=>c.url),['/api/auth/me/','/api/auth/login/']);assert.equal(calls[1].headers['X-CSRFToken'],'initial');
  assert.equal(calls[1].withCredentials,true);assert.equal(calls[1].auth,undefined);assert.equal(api.defaults.headers.common['X-CSRFToken'],'rotated');assert.equal(auth.user.must_change_password,true);
  assert.equal(sessionStorage.getItem('password'),null);
});
test('auth errors never expose Django HTML and retain structured validation messages',()=>{
  const html='<!DOCTYPE html><html><body>CSRF cookie not set.</body></html>';
  const message=service.authErrorMessage({response:{status:403,data:html}});
  assert.match(message,/cookies/);assert.doesNotMatch(message,/DOCTYPE|<html>|CSRF cookie not set/);
  assert.equal(service.authErrorMessage({response:{status:403,data:{detail:'Credenciales o acceso no válidos.'}}}),'Credenciales o acceso no válidos.');
  assert.equal(service.authErrorMessage({response:{status:400,data:{new_password:['Use una contraseña nueva.']}}}),'Use una contraseña nueva.');
  assert.equal(service.authErrorMessage({response:{status:500,data:html}}),'No se pudo completar la solicitud. Inténtelo de nuevo.');
  assert.equal(service.authErrorMessage(new Error('network')),'No se pudo conectar.');
});
test('password change clears operational gate only after server success',async()=>{
  auth.user=user('OPERATOR',{must_change_password:true});let body;
  api.defaults.adapter=async config=>{body=JSON.parse(config.data);return ok(config,{user:user(),csrf_token:'new'});};
  await service.changePassword('old-fixture','new-fixture','new-fixture');assert.deepEqual(body,{current_password:'old-fixture',new_password:'new-fixture',confirmation:'new-fixture'});assert.equal(can('register'),true);
});
test('logout clears user and patient context after server invalidation',async()=>{
  sessionStorage.setItem('sicam.auth.context','1:1');sessionStorage.setItem('sicam.uiContext.v1','patient');
  api.defaults.adapter=async config=>ok(config,{user:null,csrf_token:'anonymous'});await service.logout();assert.equal(auth.user,null);assert.equal(sessionStorage.getItem('sicam.uiContext.v1'),null);
});
test('failed logout retains session and reports failure',async()=>{
  api.defaults.adapter=async()=>{throw new Error('network');};await assert.rejects(service.logout());assert.equal(auth.user.id,1);
});
test('session refresh retains same-user context and clears it across users',async()=>{
  sessionStorage.setItem('sicam.auth.context','1:1');sessionStorage.setItem('sicam.uiContext.v1','existing');
  api.defaults.adapter=async config=>ok(config,{user:user(),csrf_token:'token'});await service.refreshSession();assert.equal(sessionStorage.getItem('sicam.uiContext.v1'),'existing');
  api.defaults.adapter=async config=>ok(config,{user:user('OPERATOR',{id:2}),csrf_token:'token'});await service.refreshSession();assert.equal(sessionStorage.getItem('sicam.uiContext.v1'),null);
});
test('direct administrative navigation is guarded for operator and reviewer',()=>{
  const ctx={seccion:'registro',confirmPendingDraftNavigation:()=>true,$refs:{}};
  for(const role of ['OPERATOR','REVIEWER']){auth.user=user(role);App.methods.requestSectionChange.call(ctx,'administracion');assert.equal(ctx.seccion,'registro');}
  auth.user=user('ADMIN');App.methods.requestSectionChange.call(ctx,'administracion');assert.equal(ctx.seccion,'administracion');
});
test('administration fails closed if directly rendered by unauthorized user',async()=>{
  auth.user=user();const html=await renderToString(createSSRApp(Admin));assert.match(html,/No tiene acceso/);assert.doesNotMatch(html,/<table/);
  auth.user=user('ADMIN');const permitted=await renderToString(createSSRApp(Admin));assert.match(permitted,/Crear usuario/);assert.doesNotMatch(permitted,/Crear institución/);
  auth.user=user(null,{is_superuser:true});assert.match(await renderToString(createSSRApp(Admin)),/Instituciones/);
});
test('header identity, institution, logout and admin visibility',async()=>{
  let html=await renderToString(createSSRApp(TopBar,{seccion:'registro'}));assert.match(html,/Synthetic/);assert.match(html,/TEST/);assert.match(html,/Cerrar sesión/);assert.doesNotMatch(html,/Administración/);
  auth.user=user('ADMIN');html=await renderToString(createSSRApp(TopBar,{seccion:'registro'}));assert.match(html,/Administración/);
});
test('reviewer Registry and acquisition hide creation actions',async()=>{
  auth.user=user('REVIEWER');const html=await renderToString(createSSRApp(Registry));assert.match(html,/Acceso de consulta/);assert.doesNotMatch(html,/Nuevo paciente|Crear caso|Subir imágenes/);
  const acquisition=await renderToString(createSSRApp(Acquisition));assert.doesNotMatch(acquisition,/Nueva configuración|Nueva calibración automática/);
});
test('logout preserves editor and registry unsaved-change guards',async()=>{
  let requests=0;api.defaults.adapter=async config=>{requests++;return ok(config,{user:null});};
  await App.methods.requestLogout.call({confirmPendingDraftNavigation:()=>false,$refs:{}});assert.equal(requests,0);
  await App.methods.requestLogout.call({confirmPendingDraftNavigation:()=>true,$refs:{registro:{confirmLeave:()=>false}}});assert.equal(requests,0);
  await App.methods.requestLogout.call({confirmPendingDraftNavigation:()=>true,$refs:{}});assert.equal(requests,1);
});

test('initial bootstrap accepts an existing server session and the gate also shows anonymous login',async()=>{
 auth.ready=false;auth.user=null;let requests=0;
 api.defaults.adapter=async config=>{requests++;assert.equal(config.url,'/api/auth/me/');return ok(config,{user:user(),csrf_token:'session-token'});};
 await service.initializeSession();assert.equal(auth.ready,true);assert.equal(auth.user.id,1);assert.equal(requests,1);
 const {default:Gate}=await server.ssrLoadModule('/src/AuthGate.vue');
 let html=await renderToString(createSSRApp(Gate));assert.doesNotMatch(html,/Iniciar sesión/);assert.match(html,/Cerrar sesión/);
 api.defaults.adapter=async config=>ok(config,{user:null,csrf_token:'anonymous'});
 await service.refreshSession();html=await renderToString(createSSRApp(Gate));assert.match(html,/Iniciar sesión/);assert.doesNotMatch(html,/Cerrar sesión/);
});
test('logout refresh and re-login use server state instead of cached UI identity',async()=>{
 let active=true;
 api.defaults.adapter=async config=>{
  assert.equal(config.withCredentials,true);
  if(config.url.endsWith('/logout/'))active=false;
  if(config.url.endsWith('/login/'))active=true;
  return ok(config,{user:active?user():null,csrf_token:active?'active':'anonymous'});
 };
 await service.logout();await service.refreshSession();assert.equal(auth.user,null);
 await service.login('synthetic','synthetic-test-only');assert.equal(auth.user.id,1);
 await service.refreshSession();assert.equal(auth.user.id,1);
});
