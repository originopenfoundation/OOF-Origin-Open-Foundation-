'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {navigate,explain}=require('../../lara/knowledge/navigator');
function fixture(status='completed',authority='CANONICAL_AUTHORITATIVE'){
 const object={id:'arch',canonicalName:'Software Lifecycle Governance Architecture',acronym:'EXAMPLE',artifactType:'Architecture',status,authorityState:authority,canonicalUrl:'https://originopenfoundation.org/example.html'};
 const resource={resource_id:'rep',object_id:'arch',canonical_url:object.canonicalUrl,authority_state:authority,provenance:{sourcePath:'example.html',contentHash:'a'.repeat(64)}};
 return {objects:[object],resources:[resource],report_only:true};
}
test('navigator exposes inspectable ranking and provenance while preserving report-only',()=>{
 const result=navigate(fixture(),'software lifecycle governance');
 assert.equal(result.status,'MATCHED');assert.equal(result.results[0].lifecycle_status,'approved-canonical');
 assert.deepEqual(result.results[0].reasons.title_terms,['software','lifecycle']);
 assert.equal(result.results[0].score,26);assert.equal(result.report_only,true);assert.equal(result.model_explanation_verified,false);
 assert.match(explain(result),/example.html/);assert.deepEqual(result,navigate(fixture(),'software lifecycle governance'));
});
test('drafts are labelled and never promoted even with a contradictory canonical flag',()=>{
 for(const state of ['draft','in-progress','pending']){
  const result=navigate(fixture(state),'software');
  assert.equal(result.results[0].lifecycle_status,state);assert.equal(result.results[0].authority_state,'SUPPORTING_CITABLE');
 }
});
test('existing detailed lifecycle terminology maps without creating approval from publication',()=>{
 assert.equal(navigate(fixture('canonical · open standard'),'software').results[0].lifecycle_status,'approved-canonical');
 assert.equal(navigate(fixture('draft standard'),'software').results[0].lifecycle_status,'draft');
 assert.equal(navigate(fixture('published','SUPPORTING_CITABLE'),'software').results[0].lifecycle_status,'published-pending');
 assert.equal(navigate(fixture('completed','SUPPORTING_CITABLE'),'software').results[0].authority_state,'SUPPORTING_CITABLE');
});
test('conflicting, unknown and withdrawn authority is visible but never recommended',()=>{
 for(const [status,authority] of [['unknown','CANONICAL_AUTHORITATIVE'],['withdrawn','CANONICAL_AUTHORITATIVE'],['completed','QUARANTINED']]){
  const result=navigate(fixture(status,authority),'software');
  assert.equal(result.status,'AUTHORITY_UNRESOLVED');assert.equal(result.results.length,0);assert.equal(result.unresolved.length,1);
 }
});
test('unknown problem and generic governance terms do not invent a recommendation',()=>{
 assert.equal(navigate(fixture(),'quantum pineapple governance').status,'UNSUPPORTED');
 assert.equal(navigate(fixture(),'governance architecture').results.length,0);
});
test('unverified, disabled or external resources cannot yield navigation links',()=>{
 const index=fixture();assert.equal(navigate(index,'software',{disabled:new Set(['rep'])}).results.length,0);
 delete index.resources[0].provenance.contentHash;assert.equal(navigate(index,'software').results.length,0);
 index.resources[0].provenance.contentHash='a'.repeat(64);index.resources[0].canonical_url='https://attacker.example/x';assert.equal(navigate(index,'software').results.length,0);
});
test('multiple domains can return distinct source-backed objects without fabricated parent links',()=>{
 const index=fixture();index.objects.push({...index.objects[0],id:'energy',canonicalName:'Energy Infrastructure Standard',artifactType:'ParentStandard'});
 index.resources.push({...index.resources[0],resource_id:'energy-rep',object_id:'energy'});
 const result=navigate(index,'software and energy infrastructure');assert.equal(result.results.length,2);
 assert(result.results.every(r=>r.relevance==='primary'));assert(result.results.every(r=>!r.parent_object_id));
});
