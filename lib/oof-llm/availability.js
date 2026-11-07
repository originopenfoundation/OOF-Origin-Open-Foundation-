'use strict';
// Adapter-local quota state. No timers, polling, conversations or credentials.
function seconds(value,now=Date.now()){
 if(typeof value!=='string'||!value.trim())return null;
 const v=value.trim();
 if(/^\d+(?:\.\d+)?$/.test(v)){const n=Number(v);return Number.isFinite(n)&&n>=0&&n<=31536000?Math.max(1,Math.ceil(n)):null;}
 if(/^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), /i.test(v)){
  const n=(Date.parse(v)-now)/1000;return Number.isFinite(n)&&n>=0&&n<=31536000?Math.max(1,Math.ceil(n)):null;
 }
 return null;
}
function duration(value){
 if(typeof value!=='string'||value.length>80)return null;
 const parts=[...value.matchAll(/(\d+(?:\.\d+)?)(ms|d|h|m|s)/g)];
 if(!parts.length||parts.map(x=>x[0]).join('')!==value)return null;
 const n=parts.reduce((sum,m)=>sum+Number(m[1])*({ms:.001,s:1,m:60,h:3600,d:86400}[m[2]]),0);
 return Number.isFinite(n)&&n>=0&&n<=31536000?Math.max(1,Math.ceil(n)):null;
}
class Availability{
 constructor(){this.quota=null;this.checking=false;this.verified=false;this.failure=null;}
 snapshot(now=Date.now()){
  const q=this.quota;
  return {state:q?(this.checking?'checking':now<q.until?'cooldown':'recheck_required'):this.failure?'unavailable':this.verified?'available':'configured_not_verified',
   quota_restricted:Boolean(q),restriction:q?.restriction||null,retry_after:q?Math.max(0,Math.ceil((q.until-now)/1000)):0,
   recheck_at:q?new Date(q.until).toISOString():null,reset_at:q?.resetAt||null,reset_known:Boolean(q?.resetAt),reason:this.failure||null};
 }
 restrict(headers,{groq=false}={},now=Date.now()){
  // Groq documents remaining-requests/reset-requests as RPD, tokens as TPM.
  const daily=groq&&headers.get('x-ratelimit-remaining-requests')==='0';
  const token=groq&&headers.get('x-ratelimit-remaining-tokens')==='0';
  const retry=seconds(headers.get('retry-after'),now);
  const reset=groq&&(daily||token)?duration(headers.get(daily?'x-ratelimit-reset-requests':'x-ratelimit-reset-tokens')):null;
  const waits=[retry,reset].filter(n=>n!==null);const wait=waits.length?Math.max(...waits):30;
  const until=now+wait*1000;
  this.quota={until,restriction:daily?'daily_requests':token?'temporary_tokens':'rate_limit_unknown',resetAt:reset!==null?new Date(now+reset*1000).toISOString():null};
  this.checking=false;this.verified=false;this.failure=null;
  return this.snapshot(now);
 }
 begin(now=Date.now()){
  const s=this.snapshot(now);
  if(s.state==='cooldown'||s.state==='checking')return false;
  if(this.quota)this.checking=true;
  return true;
 }
 success(){this.quota=null;this.checking=false;this.verified=true;this.failure=null;}
 failed(kind){
  this.checking=false;
  if(kind!=='cancelled'){this.quota=null;this.verified=false;this.failure=kind;}
 }
}
module.exports={Availability,seconds,duration};
