'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {publicEgressPolicy}=require('../../lara/llm/public-egress');
const {generationPolicy}=require('../../lara/llm/policy');
test('public visitor consent cannot replace governed public communication approval',()=>{
 const result=generationPolicy({configured:true,publicReportOnly:true,question:'Hello',passages:[],approvedPublicScopes:[]});
 assert.equal(result.allowed,false);assert.equal(result.reason,'report_only');
});
test('an approved public scope still needs explicit visitor consent for the pinned provider',()=>{
 assert.equal(generationPolicy({configured:true,publicReportOnly:true,question:'Hello',passages:[],approvedPublicScopes:['conversation']}).allowed,true);
 for(const consent of [undefined,false,'true',1])assert.deepEqual(publicEgressPolicy({publicRequest:true,provider:'groq',consent}),{allowed:false,reason:'provider_consent_required'});
 assert.deepEqual(publicEgressPolicy({publicRequest:true,provider:'groq',consent:true}),{allowed:true,data_classification:'public'});
 assert.deepEqual(publicEgressPolicy({publicRequest:true,provider:'openrouter',consent:true}),{allowed:false,reason:'public_provider_not_approved'});
});
test('controlled local review remains independent from public visitor consent',()=>{
 assert.deepEqual(publicEgressPolicy({publicRequest:false,provider:'groq'}),{allowed:true});
});
