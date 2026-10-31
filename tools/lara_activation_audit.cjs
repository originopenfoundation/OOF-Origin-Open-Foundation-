"use strict";
// Resumable capture of actual existing LaRA HTTP/SSE responses. Never assigns PASS.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {redact}=require('../lara/security/presentation');
const inventory=require('../data/localization/lara-language-inventory.json');
const prompts=['Hello, who are you?','Tell me something interesting.','What is OOF?','What is a Parent Standard?','Give me a simpler example.','Now answer in English.','What if the canonical sources disagree?','Which sources support that explanation?'];
function initialCore(){
 const objects=require('../data/knowledge/objects-core.json').objects;
 const pick=type=>objects.find(o=>o.artifactType===type&&o.authorityState==='CANONICAL_AUTHORITATIVE'&&o.visibility==='public'&&o.allowedConsumers?.includes('LaRA'));
 const architecture=pick('Architecture'),standard=pick('ParentStandard'),module=pick('CoreModule');
 if(!architecture||!standard||!module)throw Error('Approved architecture, Parent Standard and Core Module required');
 const questions=['Hello, who are you?','Why is it useful to distinguish evidence and assumptions?','What is OOF?',`Explain ${architecture.canonicalName}.`,`Explain ${standard.canonicalName}.`,`Explain ${module.canonicalName}.`,'Give me a simpler example.','What did we just discuss?','What if the canonical sources disagree?','Which sources support that explanation?'];
 return {version:'2.1',suite:'initial_intelligence',real_model_status:'NOT_VERIFIED',quality_score:null,acceptance:'NOT_EVALUATED',cases:questions.map((question,i)=>({id:'D:'+String(i+1),language:'en',scenario:i+1,input:{question,language:'en'},evaluation:'NOT_RUN',actual:null,reason:null}))};
}
function initial(){return {version:'2.1',real_model_status:'NOT_VERIFIED',quality_score:null,acceptance:'NOT_EVALUATED',cases:inventory.languages.flatMap(locale=>prompts.map((question,i)=>({id:locale.code+':'+(i+1),language:locale.code,scenario:i+1,input:{question,language:i===5?'en':i>5?'auto':locale.code},evaluation:'NOT_RUN',actual:null,reason:null}))) };}
function parseSSE(raw){return raw.split('\n').filter(l=>l.startsWith('data: ')).map(l=>JSON.parse(l.slice(6))).find(e=>e.done)?.done||null;}
// Resuming after quota must not replay completed policy refusals or rejected
// outputs: those are inspectable results, not transient transport failures.
function retryableCase(record){
 if(record.evaluation==='CAPTURED_PENDING_MANUAL_REVIEW')return false;
 if(record.evaluation!=='BLOCKED')return true;
 return ['rate_limited','timeout','provider_error','busy','http_error','AbortError','TimeoutError','TypeError','two_authenticated_model_responses_required','model_not_configured','public_report_only_gate'].includes(record.reason);
}
async function collect({base='http://127.0.0.1:4173',out='multilingual-v21.json',probe,localReview=false,maxCases=8,suite='languages'}={}){
 const report=fs.existsSync(out)?JSON.parse(fs.readFileSync(out,'utf8')):suite==='initial'?initialCore():initial();
 const save=()=>fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n',{mode:0o600});
 const url=new URL(base),loopback=['127.0.0.1','localhost','[::1]'].includes(url.hostname);
 if(url.username||url.password||url.search||url.hash||!['https:','http:'].includes(url.protocol)||url.protocol==='http:'&&!loopback)throw Error('Use HTTPS or a loopback test server');
 if(localReview&&!loopback)throw Error('Development review must be loopback');
 report.base=base;report.checked_at=new Date().toISOString();
 if(probe?.result!=='ACTIVE_VERIFIED'||probe.responses?.length<2){
  report.real_model_status='BLOCKED';for(const c of report.cases)if(c.evaluation!=='CAPTURED_PENDING_MANUAL_REVIEW'){c.evaluation='BLOCKED';c.reason='two_authenticated_model_responses_required';}save();return report;
 }
 const fingerprint=crypto.createHash('sha256').update(JSON.stringify({base,model:probe.configured_model,provider:probe.provider,inventory,suite})).digest('hex');
 if(report.fingerprint&&report.fingerprint!==fingerprint)throw Error('Evidence baseline differs; use a new report file');
 report.fingerprint=fingerprint;
 const stateFile=out+'.sessions.private.json';let state={fingerprint,sessions:{}};
 if(fs.existsSync(stateFile)){state=JSON.parse(fs.readFileSync(stateFile,'utf8'));if(state.fingerprint!==fingerprint)throw Error('Session checkpoint baseline differs');}
 const status=await(await fetch(base+'/_lara/status',{signal:AbortSignal.timeout(60000)})).json();report.status=status;
 if(!status.llm_configured||status.report_only&&!localReview){for(const c of report.cases)if(c.evaluation!=='CAPTURED_PENDING_MANUAL_REVIEW'){c.evaluation='BLOCKED';c.reason=status.report_only?'public_report_only_gate':'model_not_configured';}report.real_model_status='BLOCKED';save();return report;}
 if(report.resume_after&&Date.parse(report.resume_after)>Date.now()){save();return report;}
 let executed=0;
 for(const c of report.cases){
  if(!retryableCase(c))continue;
  if(executed>=Math.max(1,Math.min(Number(maxCases)||8,104)))break;
  if(report.cases.some(p=>p.language===c.language&&p.evaluation==='CAPTURED_PENDING_MANUAL_REVIEW')&&!state.sessions[c.language]){c.evaluation='BLOCKED';c.reason='session_checkpoint_missing';save();continue;}
  c.evaluation='NOT_VERIFIED';c.reason=null;const started=Date.now();
  try{
   const response=await fetch(base+'/_lara/chat',{method:'POST',headers:{Origin:'https://originopenfoundation.org','Content-Type':'application/json',...(state.sessions[c.language]?{'X-LaRA-Session':state.sessions[c.language]}:{})},body:JSON.stringify(c.input),signal:AbortSignal.timeout(60000)});
   const sid=response.headers.get('x-lara-session');if(sid)state.sessions[c.language]=sid;
   fs.writeFileSync(stateFile,JSON.stringify(state),{mode:0o600});
   c.http_status=response.status;if(response.status!==200)await response.body?.cancel();const actual=response.status===200?parseSSE(await response.text()):null;
   c.actual=actual?{answer:redact(actual.answer),language:actual.language,communication_style:actual.communication_style,sources:actual.sources,generation:actual.generation,public_report_only:actual.public_report_only}:null;
   const generated=actual?.generation;
   c.evaluation=generated?.kind==='model'&&generated.model===probe.configured_model&&generated.reported_model===probe.configured_model?'CAPTURED_PENDING_MANUAL_REVIEW':'BLOCKED';
   c.reason=generated?.reason||(!actual?'http_error':c.evaluation==='BLOCKED'?'model_identity_or_generation_unverified':null);
   if(generated?.reason==='rate_limited'||response.status===429){
    c.reason='rate_limited';report.resume_after=new Date(Date.now()+Math.max(1,Number(generated?.retry_after)||Number(response.headers.get('retry-after'))||60)*1000).toISOString();
    c.latency_ms=Date.now()-started;save();break;
   }
  }catch(error){c.reason=error.name;c.evaluation='BLOCKED';}
  c.latency_ms=Date.now()-started;executed++;save();
 }
 report.real_model_status=report.cases.some(c=>c.evaluation==='CAPTURED_PENDING_MANUAL_REVIEW')?'PARTIAL':'BLOCKED';
 report.language_summary=inventory.languages.map(l=>({language:l.code,captured:report.cases.filter(c=>c.language===l.code&&c.evaluation==='CAPTURED_PENDING_MANUAL_REVIEW').length,total:8,acceptance:'NOT_EVALUATED'}));
 report.finished_at=new Date().toISOString();save();return report;
}
if(require.main===module){const args=process.argv.slice(2),arg=(n,d)=>args.includes(n)?args[args.indexOf(n)+1]:d;
 const probeFile=arg('--probe',null);collect({base:arg('--base','http://127.0.0.1:4173'),out:path.resolve(arg('--out','multilingual-v21.json')),probe:probeFile?JSON.parse(fs.readFileSync(probeFile,'utf8')):null,localReview:args.includes('--local-review'),maxCases:arg('--max-cases',8),suite:arg('--suite','languages')}).then(r=>console.log(JSON.stringify({cases:r.cases.length,status:r.real_model_status,resume_after:r.resume_after||null}))).catch(e=>{console.error(e.message);process.exitCode=1;});}
module.exports={initial,initialCore,collect,parseSSE,retryableCase};
