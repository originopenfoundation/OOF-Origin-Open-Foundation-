"use strict";
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {createGateway,createClient,GroqAdapter,ModelRegistry}=require('../../lib/oof-llm');
const {redact}=require('../../lara/security/presentation'),{validate}=require('../../lara/validation');
const {approvedScopes}=require('../../lara/knowledge/communication-approval');
const {generationPolicy}=require('../../lara/llm/policy');
const {initial,collect}=require('../../tools/lara_activation_audit.cjs');
const env={LLM_PROVIDER:'groq',LLM_MODEL:'openai/gpt-oss-120b',LLM_BASE_URL:'https://api.groq.com/openai/v1',LLM_API_KEY:'gsk_'+'s'.repeat(40),LLM_GROQ_FREE_TIER_CONFIRMED:'true',LLM_FALLBACK_PROVIDER:'none'};
const input={question:'Explain evidence in a sentence.',language:'German',data_classification:'synthetic'};
const response=(extra={},status=200,headers={})=>new Response(JSON.stringify({model:env.LLM_MODEL,choices:[{message:{content:'Evidence supports a claim.'}}],usage:{prompt_tokens:12,completion_tokens:8,total_tokens:20},...extra}),{status,headers:{'Content-Type':'application/json',...headers}});
async function withFetch(fake,fn){const prior=global.fetch;global.fetch=fake;try{await fn();}finally{global.fetch=prior;}}
test('approved Groq route pins model and endpoint and requires account attestation',()=>{
 const gateway=createGateway(env);assert(gateway.primary instanceof GroqAdapter);assert.equal(gateway.fallback,null);assert.equal(gateway.maxConcurrent,1);
 for(const change of [{LLM_MODEL:'openai/gpt-oss-20b'},{LLM_MODEL:'paid-model'},{LLM_BASE_URL:'https://evil.test/openai/v1'},{LLM_GROQ_FREE_TIER_CONFIRMED:'false'},{LLM_API_KEY:''}])assert.throws(()=>createGateway({...env,...change}),e=>e.kind==='invalid_configuration');
});
test('OpenAI-compatible alias cannot bypass Groq cost or fallback restrictions',()=>{
 assert.equal(createGateway({...env,LLM_PROVIDER:'openai-compatible'}).primary.name,'groq');
 assert.throws(()=>createGateway({...env,LLM_PROVIDER:'openai-compatible',LLM_GROQ_FREE_TIER_CONFIRMED:'false'}));
 assert.throws(()=>createGateway({...env,LLM_FALLBACK_PROVIDER:'openai-compatible',LLM_FALLBACK_MODEL:'paid',LLM_FALLBACK_API_KEY:'fallback-key',LLM_FALLBACK_BASE_URL:'https://example.test/v1'}));
 assert.throws(()=>createGateway({...env,LLM_FALLBACK_PROVIDER:'openai-compatible',LLM_FALLBACK_MODEL:env.LLM_MODEL,LLM_FALLBACK_API_KEY:'fallback-key',LLM_FALLBACK_BASE_URL:env.LLM_BASE_URL}));
});
test('Groq transport carries requested language, safe source URL and usage without exposing keys',async()=>{
 await withFetch(async(url,options)=>{assert.equal(url,env.LLM_BASE_URL+'/chat/completions');assert.equal(options.redirect,'error');assert.equal(options.headers.Authorization,'Bearer '+env.LLM_API_KEY);const body=JSON.parse(options.body);assert.equal(body.model,env.LLM_MODEL);assert.equal(JSON.parse(body.messages[1].content).response_language,'German');return response({},200,{'x-ratelimit-remaining-tokens':'7000','x-ratelimit-reset-tokens':'12.2s','set-cookie':'private'});},async()=>{
  const client=createClient({consumer_id:'LaRA',env,instructions:'Only explain public information.'}),r=await client.generate(input);
  assert.equal(r.provider,'groq');assert.equal(r.reported_model,env.LLM_MODEL);assert.equal(r.usage.total_tokens,20);assert.equal(r.rate_limits['x-ratelimit-remaining-tokens'],'7000');assert.equal(r.rate_limits['set-cookie'],undefined);assert.equal(r.fallback_used,false);assert(!JSON.stringify(r).includes(env.LLM_API_KEY));
 });
});
test('missing or substituted provider-reported model fails before model content is delivered',async()=>{
 for(const model of [undefined,'another-model'])await withFetch(()=>Promise.resolve(response({model})),async()=>await assert.rejects(createGateway(env).generateDetailed(input),e=>e.kind==='model_identity_mismatch'));
});
test('Groq 429 respects Retry-After longer than previous cap and makes no automatic retry',async()=>{
 let calls=0;await withFetch(async()=>{calls++;return response({},429,{'retry-after':'600'});},async()=>{
  const gateway=createGateway(env);await assert.rejects(gateway.generateDetailed(input),e=>e.kind==='rate_limited'&&e.retryAfter===600);
  await assert.rejects(gateway.generateDetailed(input),e=>e.kind==='rate_limited');assert.equal(calls,1);
 });
});
test('quota parser accepts an HTTP-date, not just integer seconds',()=>{const {retryAfter}=require('../../lib/oof-llm/groq-policy');assert.equal(retryAfter('Thu, 01 Jan 2026 00:10:00 GMT',Date.parse('2026-01-01T00:00:00Z')),600);});
test('external egress rejects unclassified, confidential, private-source and personal input',async()=>{
 let calls=0;await withFetch(async()=>{calls++;return response();},async()=>{
  const g=createGateway(env);
  for(const change of [{data_classification:undefined},{question:'My confidential record is here'},{question:'Email person@example.test'},{passages:[{authority_state:'QUARANTINED'}]},{passages:[{authority_state:'CANONICAL_AUTHORITATIVE',visibility:'private'}]}])await assert.rejects(g.generateDetailed({...input,...change}),e=>e.kind==='data_authorization_required');
  assert.equal(calls,0);
 });
});
test('Groq credential-like output is rejected and presentation/validation redact its key syntax',async()=>{
 const key='gsk_'+'a'.repeat(40);assert(!redact(key).includes(key));assert.equal(validate(key,'test',[],{scope:'conversation'}).ok,false);
 await withFetch(()=>Promise.resolve(response({choices:[{message:{content:key}}]})),async()=>await assert.rejects(createGateway(env).generateDetailed(input),e=>e.kind==='output_rejected'));
});
test('retrieved supporting context is explicitly labeled and cannot be promoted or given invented citations',()=>{
 const source={authority_state:'SUPPORTING_CITABLE',communication_state:'SUPPORTING_NON_CANONICAL',title:'Support',text:'Example evidence.',url:'https://originopenfoundation.org/support.html'};
 assert.equal(generationPolicy({configured:true,publicReportOnly:false,question:'Explain this',passages:[source]}).scope,'supporting');
 assert.equal(validate('This is canonical.','test',[source],{scope:'supporting'}).reason,'supporting_authority_promotion');
 assert.equal(validate('See https://originopenfoundation.org/invented.html','test',[source],{scope:'supporting'}).reason,'unsupported_citation');
});
test('public conversation/supporting approval is independent; canonical readiness never bypassed',()=>{
 const base={configured:true,publicReportOnly:true,question:'Why is the sky blue?',passages:[]};
 assert.equal(generationPolicy(base).reason,'report_only');assert.equal(generationPolicy({...base,approvedPublicScopes:['conversation']}).allowed,true);
 const canonical={authority_state:'CANONICAL_AUTHORITATIVE',communication_state:'CANONICAL_VERIFIED'};
 assert.equal(generationPolicy({...base,passages:[canonical],approvedPublicScopes:['conversation','supporting','canonical']}).allowed,false);
 assert.equal(generationPolicy({...base,identity:{status:'AMBIGUOUS'},approvedPublicScopes:['conversation']}).allowed,false);
});
test('methodological approval must be an exact governed object and digest, not an env flag or title',()=>{
 const policyFile=path.resolve(__dirname,'../../lara/knowledge/public-communication-policy.json');
 const object={id:'OOF-KO-LARA-PUBLIC-COMMUNICATION',authorityState:'CANONICAL_AUTHORITATIVE',visibility:'public',allowedConsumers:['LaRA'],status:'active',sourceAuthority:{domains:['publicCommunicationApproval'],publicCommunicationApproval:{status:'approved',policyDigest:crypto.createHash('sha256').update(fs.readFileSync(policyFile)).digest('hex'),scopes:['conversation','supporting','canonical']}}};
 assert.deepEqual(approvedScopes({objects:[]}),[]);assert.deepEqual(approvedScopes({objects:[object]}),['conversation','supporting']);assert.deepEqual(approvedScopes({objects:[{...object,authorityState:'SUPPORTING_CITABLE'}]}),[]);assert.deepEqual(approvedScopes({objects:[object,object]}),[]);assert.deepEqual(approvedScopes({objects:[{...object,sourceAuthority:{...object.sourceAuthority,publicCommunicationApproval:{...object.sourceAuthority.publicCommunicationApproval,policyDigest:'wrong'}}}]}),[]);
});
test('all 104 unexecuted language scenarios stay blocked and cannot inherit a quality PASS',async()=>{
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'lara-capture-'));
 try{const r=await collect({out:path.join(folder,'blocked.json')});assert.equal(r.cases.length,104);assert(r.cases.every(c=>c.evaluation==='BLOCKED'));assert.equal(r.quality_score,null);assert.equal(r.real_model_status,'BLOCKED');assert.equal(initial().cases.length,104);}finally{fs.rmSync(folder,{recursive:true,force:true});}
});
test('Groq model metadata never claims verified multilingual or fallback activation',()=>{
 const catalog=require('../../lib/oof-llm/models.catalog.json'),r=new ModelRegistry(catalog.models);const p=r.list().find(x=>x.id==='groq-gpt-oss-120b'),f=r.list().find(x=>x.id==='groq-gpt-oss-20b');assert.equal(p.provider,'groq');assert.equal(p.verified_languages.length,0);assert.equal(f.available,false);
});

test('source-attribution follow-ups retain the same governed retrieval topic',()=>{
 const conversation=require('../../lara/conversation');
 for(const q of ['Which sources support that explanation?','What did we just discuss?','What if the canonical sources disagree?'])assert.equal(conversation.query(q,{topic:'Known Standard'}),'Known Standard');
});
test('ten initial intelligence cases use actual governed architecture, Parent Standard and Core Module',()=>{
 const {initialCore}=require('../../tools/lara_activation_audit.cjs');const r=initialCore();assert.equal(r.cases.length,10);assert(r.cases.every(c=>c.evaluation==='NOT_RUN'));assert(r.cases[4].input.question.includes('Standard'));assert(r.cases[5].input.question.includes('Module'));
});
