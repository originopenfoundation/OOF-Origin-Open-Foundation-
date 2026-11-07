'use strict';
// Run on the inference-authorized server; no keys are printed or persisted in evidence.
const fs=require('node:fs'),path=require('node:path');
const {createClient}=require('../lib/oof-llm');
async function probe(env=process.env){
 const report={version:'2.1',checked_at:new Date().toISOString(),provider:env.LLM_PROVIDER||'none',configured_model:env.LLM_MODEL||null,result:'BLOCKED_AUTHORIZED_ENVIRONMENT_REQUIRED',responses:[],verification:'Actual provider transport only; content quality requires manual review.'};
 try{
  if(!env.LLM_API_KEY){report.result='BLOCKED_CREDENTIAL_REQUIRED';return report;}
  const client=createClient({consumer_id:'LaRA',env,instructions:'You are an inference connectivity test. Answer briefly in the requested language. Never invent OOF methodology, authority or executed actions.'});
  for(const input of [{question:'Introduce yourself in one sentence without claiming to have executed any external action.',language:'English'},{question:'Explain the difference between evidence and assumption in one sentence.',language:'English'}]){
   const response=await client.generate({...input,data_classification:'synthetic',passages:[],history:[],length:'short'});
   report.responses.push({input,...response});
  }
  report.result=report.responses.every(r=>r.reported_model&&r.reported_model===report.configured_model)?'ACTIVE_VERIFIED':'NOT_VERIFIED';
  report.identity_limit='Provider/model identity is the remote API response claim; it is not cryptographic attestation.';
 }catch(error){report.result=error.kind==='rate_limited'?'BLOCKED_RATE_LIMIT':error.kind==='model_unavailable'?'BLOCKED_PROVIDER':'NOT_VERIFIED';report.error={retry_after:Number.isFinite(error.retryAfter)?error.retryAfter:null,kind:error.kind||'provider_error',message:error.kind==='invalid_configuration'?'Provider key/model/endpoint configuration is incomplete or invalid.':'Inference could not be verified.'};}
 return report;
}
if(require.main===module)probe().then(report=>{if(process.argv[2])fs.writeFileSync(path.resolve(process.argv[2]),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(report.result!=='ACTIVE_VERIFIED')process.exitCode=1;});
module.exports={probe};
