'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {originPolicy}=require('../../lara/security/origin');
function request(origin,method='POST',headers={}){return {method,headers:{host:'backend.onrender.com',...(origin?{origin}:{}),...headers}};}
function response(){return {headers:{},setHeader(k,v){this.headers[k]=v;},writeHead(status){this.status=status;},end(body){this.body=body;}};}
test('only exact canonical origins or same-origin requests are accepted',()=>{
 const policy=originPolicy();for(const origin of ['https://originopenfoundation.org','https://www.originopenfoundation.org','https://backend.onrender.com'])assert(policy.accepts(request(origin)));
 for(const origin of ['https://originopenfoundation.org.evil.test','http://originopenfoundation.org','null','https://evil.test',undefined])assert(!policy.accepts(request(origin)));
});
test('preflight permits chat JSON and temporary session headers, without a wildcard',()=>{
 const policy=originPolicy(),res=response();assert(policy.apply(request('https://originopenfoundation.org','OPTIONS',{'access-control-request-method':'POST','access-control-request-headers':'content-type,x-lara-session'}),res,'/_lara/chat'));
 assert.equal(res.status,204);assert.equal(res.headers['Access-Control-Allow-Origin'],'https://originopenfoundation.org');assert.equal(res.headers.Vary,'Origin');assert.equal(res.headers['Access-Control-Expose-Headers'],'X-LaRA-Session');
});
test('unapproved headers, origins and admin endpoints never get public CORS permission',()=>{
 const policy=originPolicy();for(const req of [request('https://evil.test','OPTIONS',{'access-control-request-method':'POST'}),request('https://originopenfoundation.org','OPTIONS',{'access-control-request-method':'POST','access-control-request-headers':'authorization'})]){const res=response();policy.apply(req,res,'/_lara/chat');assert.equal(res.status,403);}
 const res=response();assert.equal(policy.apply(request('https://originopenfoundation.org'),res,'/_lara/admin/settings'),false);assert.equal(res.headers['Access-Control-Allow-Origin'],undefined);
});
