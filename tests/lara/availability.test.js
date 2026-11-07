'use strict';
// Controlled transport fixtures verify engineering only, never real-model quality.
const test=require('node:test'),assert=require('node:assert/strict');
const {Availability,seconds,duration}=require('../../lib/oof-llm/availability');
const {createGateway}=require('../../lib/oof-llm');
const env={LLM_PROVIDER:'groq',LLM_MODEL:'openai/gpt-oss-120b',LLM_BASE_URL:'https://api.groq.com/openai/v1',LLM_API_KEY:'synthetic-test-key',LLM_GROQ_FREE_TIER_CONFIRMED:'true',LLM_FALLBACK_PROVIDER:'none'};
const input={question:'Explain evidence.',data_classification:'synthetic'};
test('quota time parsing accepts seconds, HTTP-date and compound provider resets without inventing a date',()=>{
 assert.equal(seconds('600'),600);assert.equal(seconds('Sun, 25 Oct 2026 12:10:00 GMT',Date.parse('2026-10-25T12:00:00Z')),600);
 for(const v of ['',null,'-1','NaN','tomorrow','999999999999999'])assert.equal(seconds(v),null);
 assert.equal(duration('2m59.56s'),180);assert.equal(duration('1h2m3s'),3723);assert.equal(duration('1d'),86400);
 for(const v of ['',null,'1 minute','-2s','12sBAD','999999999d'])assert.equal(duration(v),null);
});
test('confirmed RPD exhaustion differs from token cooldown and waits for the longest reliable restriction',()=>{
 const a=new Availability(),now=Date.parse('2026-10-25T12:00:00Z');
 let s=a.restrict(new Headers({'retry-after':'2','x-ratelimit-remaining-requests':'0','x-ratelimit-reset-requests':'2h'}),{groq:true},now);
 assert.equal(s.restriction,'daily_requests');assert.equal(s.retry_after,7200);assert.equal(s.reset_at,'2026-10-25T14:00:00.000Z');
 s=a.restrict(new Headers({'x-ratelimit-remaining-tokens':'0','x-ratelimit-reset-tokens':'7.66s'}),{groq:true},now);
 assert.equal(s.restriction,'temporary_tokens');assert.equal(s.retry_after,8);
});
test('429 without reliable reset has a local backoff, not a fabricated quota reset',()=>{
 const a=new Availability(),s=a.restrict(new Headers({'retry-after':'invalid'}),{groq:true},1000);
 assert.equal(s.restriction,'rate_limit_unknown');assert.equal(s.reset_known,false);assert.equal(s.reset_at,null);assert.equal(s.retry_after,30);
 assert.equal(a.snapshot(31000).state,'recheck_required');assert.equal(a.verified,false);
});
test('Retry-After permits a recheck but does not attest the exact provider quota reset',()=>{
 const s=new Availability().restrict(new Headers({'retry-after':'600'}),{groq:true},1000);
 assert.equal(s.retry_after,600);assert.equal(s.reset_known,false);assert.equal(s.reset_at,null);
});
test('only one request may check recovery; only successful inference confirms availability',()=>{
 const a=new Availability();a.restrict(new Headers({'retry-after':'1'}),{},0);
 assert.equal(a.begin(999),false);assert.equal(a.begin(1000),true);assert.equal(a.begin(1000),false);
 assert.equal(a.snapshot(1000).state,'checking');a.success();assert.equal(a.snapshot().state,'available');assert.equal(a.snapshot().quota_restricted,false);
});
test('non-quota failures and cancellation do not fabricate Free Tier exhaustion',()=>{
 for(const kind of ['authentication_error','timeout','provider_error','model_unavailable','output_rejected']){
  const a=new Availability();a.failed(kind);assert.equal(a.snapshot().quota_restricted,false);assert.equal(a.snapshot().state,'unavailable');
 }
 const a=new Availability();a.restrict(new Headers({'retry-after':'1'}),{},0);a.begin(1000);a.failed('cancelled');assert.equal(a.snapshot(1000).state,'recheck_required');
});
test('adapter cooldown blocks a request storm and supports one recovery request without polling or fallback',async()=>{
 const original=global.fetch,clock=Date.now;let now=1000,calls=0,release;
 Date.now=()=>now;
 global.fetch=async()=>{calls++;if(calls===1)return new Response('',{status:429,headers:{'retry-after':'1'}});await new Promise(r=>release=r);return new Response(JSON.stringify({model:env.LLM_MODEL,choices:[{message:{content:'Evidence supports a claim.'}}]}));};
 try{
  const g=createGateway(env);await assert.rejects(g.generateDetailed(input),e=>e.kind==='rate_limited');
  for(let i=0;i<20;i++)await assert.rejects(g.generateDetailed(input),e=>e.kind==='rate_limited');
  assert.equal(calls,1);now=2000;assert.equal(g.availability().state,'recheck_required');assert.equal(calls,1);
  const result=g.generateDetailed(input);await assert.rejects(g.generateDetailed(input),e=>e.kind==='busy');release();
  assert.equal((await result).fallback_used,false);assert.equal(calls,2);assert.equal(g.availability().state,'available');
 }finally{Date.now=clock;global.fetch=original;}
});
test('authentication failure after cooldown is reported independently and does not extend the quota',async()=>{
 const original=global.fetch;global.fetch=async()=>new Response('',{status:401});
 try{const g=createGateway(env);await assert.rejects(g.generateDetailed(input),e=>e.kind==='authentication_error');assert.equal(g.availability().state,'unavailable');assert.equal(g.availability().quota_restricted,false);assert.equal(g.availability().reason,'authentication_error');}
 finally{global.fetch=original;}
});
