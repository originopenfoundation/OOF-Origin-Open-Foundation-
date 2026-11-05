'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createVerifier}=require('../../lib/oof-evidence-verification');
const {present,validatePlan}=require('../../lib/oof-evidence-verification/presentation');
const {copy,languages}=require('../../lib/oof-localization');
function fixture(){const index={objects:[],resources:[],relationships:[],registry_fingerprint:'synthetic'},verifier=createVerifier(index);const result=verifier.assess({text:'An agent acted. A payment occurred.'});return{index,verifier,result};}
test('evidence presentation rejects new status, extra claims, omitted or repeated IDs',()=>{const {result}=fixture(),ids=result.claims.map(c=>c.claim_id);validatePlan({schema_version:'1.0',claim_order:ids},result);for(const plan of [{schema_version:'1.0',claim_order:ids,status:'VERIFIED'},{schema_version:'1.0',claim_order:ids.slice(1)},{schema_version:'1.0',claim_order:[ids[0],ids[0]]},{schema_version:'1.0',claim_order:[...ids,'invented']}])assert.throws(()=>validatePlan(plan,result));});
test('presentation without eligible sources or consent performs zero inference',async()=>{const f=fixture();let calls=0;const r=await present({...f,language:'en',permitted:true,gateway:{primary:{},generateDetailed:()=>{calls++;}}});assert.equal(calls,0);assert.equal(r.kind,'deterministic_fallback');assert.equal(r.model_calls,0);});
test('localized evidence plan retains no-event-proof and proposed-test boundaries in every language',()=>{const f=fixture();for(const lang of languages){const answer=require('../../lib/oof-evidence-verification').explain(f.result,lang);assert(answer.includes(copy(lang).notEventProof));assert(answer.includes(copy(lang).proposed));assert(answer.includes(copy(lang).acceptanceText));}});
