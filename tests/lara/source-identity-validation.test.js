'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {validate}=require('../../lara/validation');
const source={title:'Known Standard',text:'Known Standard governs evidence.',object_id:'OOF-KO-ARCH-EXAMPLE',resource_id:'https://originopenfoundation.org/known.html#webpage',url:'https://originopenfoundation.org/known.html'};
test('a source-supplied object identity is accepted with typographic citation hyphens',()=>{
 assert.equal(validate('Known Standard governs evidence [OOF‑KO‑ARCH‑EXAMPLE].','test',[source]).ok,true);
});
test('known identity fragments and visitor input cannot manufacture another object',()=>{
 for(const id of ['OOF-KO-EXAMPLE-ARCH','OOF-KO-ARCH-UNKNOWN','OOF-KO-ARCH-999'])assert.deepEqual(validate('Known Standard ['+id+'].',id,[source]),{ok:false,reason:'unsupported_object_identity'});
});
