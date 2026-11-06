"use strict";
const ENDPOINT='https://api.groq.com/openai/v1';
const PRIMARY='openai/gpt-oss-120b';
function configuration(env,prefix='LLM_'){
 const model=env[`${prefix}MODEL`]||PRIMARY,baseUrl=env[`${prefix}BASE_URL`]||ENDPOINT;
 if(model!==PRIMARY||baseUrl.replace(/\/$/,'')!==ENDPOINT)throw Error('Groq approved model and endpoint are pinned');
 if(env.LLM_GROQ_FREE_TIER_CONFIRMED!=='true')throw Error('Free Tier account confirmation required');
 return {model,baseUrl:ENDPOINT};
}
function dataAllowed(input){
 if(!['public','synthetic'].includes(input.data_classification))return false;
 for(const p of input.passages||[]){
  if(p.visibility&&p.visibility!=='public'||!['CANONICAL_AUTHORITATIVE','SUPPORTING_CITABLE'].includes(p.authority_state)
   ||p.communication_state&&!['CANONICAL_VERIFIED','SUPPORTING_NON_CANONICAL'].includes(p.communication_state))return false;
 }
 const text=JSON.stringify({question:input.question,history:input.history,assessment:input.assessment});
 return !/(?:\b(?:confidential|classified|restricted|ssn|social security|medical record|never share)\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:gsk_|sk-|gh[pousr]_)[A-Za-z0-9_-]{16,}\b)/i.test(text);
}
function rateLimits(headers){
 const result={};
 for(const key of ['x-ratelimit-limit-requests','x-ratelimit-limit-tokens','x-ratelimit-remaining-requests','x-ratelimit-remaining-tokens','x-ratelimit-reset-requests','x-ratelimit-reset-tokens']){
  const value=headers.get(key);if(value&&/^[0-9a-z. -]{1,80}$/i.test(value))result[key]=value;
 }
 return result;
}
function retryAfter(value,now=Date.now()){
 const seconds=Number(value),date=Date.parse(value);
 return value&&Number.isFinite(seconds)?Math.max(1,seconds):Number.isFinite(date)?Math.max(1,Math.ceil((date-now)/1000)):30;
}
module.exports={ENDPOINT,PRIMARY,configuration,dataAllowed,rateLimits,retryAfter};
