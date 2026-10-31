'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {retryableCase,collect}=require('../../tools/lara_activation_audit.cjs');
test('quota resume preserves successful, rejected and policy-blocked results',()=>{
 for(const reason of ['source_boundary','output_rejected','identity_unresolved','session_checkpoint_missing'])assert.equal(retryableCase({evaluation:'BLOCKED',reason}),false);
 assert.equal(retryableCase({evaluation:'CAPTURED_PENDING_MANUAL_REVIEW'}),false);
 for(const reason of ['rate_limited','timeout','provider_error'])assert.equal(retryableCase({evaluation:'BLOCKED',reason}),true);
 assert.equal(retryableCase({evaluation:'NOT_RUN'}),true);
});
test('resumption sends only the next retryable scenario and retains terminal evidence',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'lara-resume-')),out=path.join(dir,'report.json'),original=global.fetch;
 const report={cases:[{id:'1',language:'en',evaluation:'BLOCKED',reason:'source_boundary',input:{question:'policy blocked'}},{id:'2',language:'en',evaluation:'BLOCKED',reason:'output_rejected',input:{question:'rejected'}},{id:'3',language:'en',evaluation:'BLOCKED',reason:'rate_limited',input:{question:'retry after quota'}}]};
 fs.writeFileSync(out,JSON.stringify(report));const chats=[];
 global.fetch=async(url,options)=>{if(url.endsWith('/_lara/status'))return new Response(JSON.stringify({llm_configured:true,report_only:true}));chats.push(JSON.parse(options.body));return new Response('data: '+JSON.stringify({done:{answer:'Synthetic transport fixture.',generation:{kind:'model',model:'synthetic-model',reported_model:'synthetic-model'}}})+'\n\n');};
 try{const actual=await collect({out,probe:{result:'ACTIVE_VERIFIED',responses:[{},{}],configured_model:'synthetic-model',provider:'synthetic'},localReview:true,maxCases:1});assert.equal(chats.length,1);assert.equal(chats[0].question,'retry after quota');assert.equal(actual.cases[0].reason,'source_boundary');assert.equal(actual.cases[1].reason,'output_rejected');assert.equal(actual.cases[2].evaluation,'CAPTURED_PENDING_MANUAL_REVIEW');}
 finally{global.fetch=original;fs.rmSync(dir,{recursive:true,force:true});}
});
