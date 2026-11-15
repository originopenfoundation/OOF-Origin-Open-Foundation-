'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const registry=require('../../docs/lara-functional-registry.json');

test('functional registry has unique stable IDs and resolvable source and test references',()=>{
 const ids=registry.records.map(record=>record.id);
 assert.equal(new Set(ids).size,ids.length);
 for(const record of registry.records){
  assert.match(record.id,/^LARA-F[0-9]{3,}$/);
  for(const file of [record.source,...record.tests])
   assert.ok(fs.statSync(path.resolve(__dirname,'../..',file)).isFile(),file);
  if(record.verification==='NOT YET VERIFIED')assert.equal(record.lastVerifiedRevision,null);
 }
});
