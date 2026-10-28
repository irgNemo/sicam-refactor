import assert from 'node:assert/strict';
import {test} from 'node:test';
import {canonicalDevelopmentUrl, canonicalDevelopmentOrigin} from '../dev/canonicalOrigin.mjs';

test('localhost redirects to the API loopback host, preserving frontend port and path',()=>{
 assert.equal(canonicalDevelopmentUrl('http://127.0.0.1:8000','localhost:5173','/registro?tab=dataset'),'http://127.0.0.1:5173/registro?tab=dataset');
 assert.equal(canonicalDevelopmentUrl('http://127.0.0.1:8000','localhost:5173','//example.invalid/path'),'http://127.0.0.1:5173//example.invalid/path');
});
test('canonical, remote, relative and HTTPS configurations are left alone',()=>{
 for(const [api,host] of [['http://127.0.0.1:8000','127.0.0.1:5173'],['/','localhost:5173'],['https://api.example.invalid','localhost:5173'],['http://localhost:8000','localhost:5173'],['http://127.0.0.1:8000','example.invalid:5173'],['https://127.0.0.1:8000','localhost:5173']])assert.equal(canonicalDevelopmentUrl(api,host,'/'),null);
});
test('redirect is temporary, development-only and never forwards submitted credentials',()=>{
 const plugin=canonicalDevelopmentOrigin('http://127.0.0.1:8000');assert.equal(plugin.apply,'serve');
 let middleware;plugin.configureServer({config:{server:{}},middlewares:{use:handler=>{middleware=handler}}});
 let status,headers,ended=false,next=0;
 const response={writeHead:(code,value)=>{status=code;headers=value},end:()=>{ended=true}};
 middleware({method:'GET',headers:{host:'localhost:5173'},url:'/'},response,()=>next++);
 assert.equal(status,307);assert.equal(headers.Location,'http://127.0.0.1:5173/');assert.equal(headers['Cache-Control'],'no-store');assert.equal(ended,true);
 for(const method of ['POST','PUT','DELETE'])middleware({method,headers:{host:'localhost:5173'},url:'/api/auth/login/'},response,()=>next++);
 assert.equal(next,3);
});
