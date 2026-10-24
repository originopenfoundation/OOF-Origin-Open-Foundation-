'use strict';
// Captures real existing API responses; never assigns model quality from keywords.
const fs=require('node:fs'),path=require('node:path');
const args=process.argv.slice(2),arg=(n,d)=>args.includes(n)?args[args.indexOf(n)+1]:d;
const base=arg('--base','http://127.0.0.1:4173'),out=path.resolve(arg('--out','multilingual-evidence.json'));
const inventory=require('../data/localization/lara-language-inventory.json');
const prompts=['Hello, who are you?','Tell me something interesting.','What is OOF?','What is a Parent Standard?','Give me a simpler example.','Now answer in English.','What if the canonical sources disagree?','Which sources support that explanation?'];
(async()=>{const report={version:'2.0',started_at:new Date().toISOString(),base,status:null,cases:[],quality_score:null,real_model_status:'BLOCKED'};
try{report.status=await(await fetch(base+'/_lara/status',{signal:AbortSignal.timeout(60000)})).json();
for(const locale of inventory.languages){let session=null;for(const [i,question] of prompts.entries()){
 const record={language:locale.code,scenario:i+1,input:{question,language:i===5?'en':i>5?'auto':locale.code},evaluation:'BLOCKED',reason:null};
 if(!report.status.llm_configured||report.status.report_only){record.reason=report.status.report_only?'public_report_only_gate':'model_not_configured';report.cases.push(record);continue;}
 try{const response=await fetch(base+'/_lara/chat',{method:'POST',headers:{Origin:'https://originopenfoundation.org','Content-Type':'application/json',...(session?{'X-LaRA-Session':session}:{})},body:JSON.stringify(record.input),signal:AbortSignal.timeout(60000)});session=response.headers.get('x-lara-session')||session;const text=await response.text();const done=text.split('\n').filter(l=>l.startsWith('data: ')).map(l=>JSON.parse(l.slice(6))).find(e=>e.done)?.done;record.http_status=response.status;record.actual=done||null;record.evaluation=done?.generation?.kind==='model'?'PENDING_MANUAL_REVIEW':'BLOCKED';record.reason=done?.generation?.reason||null;}catch(error){record.reason=error.name;}report.cases.push(record);
}}
if(report.cases.some(c=>c.evaluation==='PENDING_MANUAL_REVIEW'))report.real_model_status='PARTIAL';
}catch(error){report.error=error.name;}
report.finished_at=new Date().toISOString();fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({cases:report.cases.length,real_model_status:report.real_model_status,error:report.error||null}));})();
