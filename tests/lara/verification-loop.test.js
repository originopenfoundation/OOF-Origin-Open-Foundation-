'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {reviewLoop}=require('../../lara/verification-loop');
const defaults={objective:'Review evidence',iterations:3,budgetMs:1000};

test('repairs then verifies within the configured limit',()=>{
 let value=0;
 const result=reviewLoop({...defaults,observe:()=>value,verify:value=>value===1,repair:()=>{value++;}});
 assert.equal(result.status,'verified');
 assert.deepEqual(result.trace.map(step=>step.stage),['verify','repair','verify']);
});

test('does not repair after the final attempt',()=>{
 let repairs=0;
 const result=reviewLoop({...defaults,observe:()=>null,verify:()=>false,repair:()=>{repairs++;}});
 assert.equal(result.status,'iteration_limit');
 assert.equal(repairs,2);
});

test('rejects unsafe bounds and keeps step errors out of the trace',()=>{
 const steps={observe:()=>{throw new Error('private details');},verify:()=>true,repair:()=>{}};
 assert.throws(()=>reviewLoop({...defaults,...steps,iterations:6}),TypeError);
 const result=reviewLoop({...defaults,...steps});
 assert.equal(result.status,'step_failed');
 assert.deepEqual(result.trace,[{attempt:1,stage:'observe',failed:true}]);
});
