'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {readShared,exact}=require('../../lara/knowledge');
const {rank}=require('../../lara/retrieval');
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'lara-shared-'));
 const write=(file,value)=>{const full=path.join(root,file);fs.mkdirSync(path.dirname(full),{recursive:true});fs.writeFileSync(full,typeof value==='string'?value:JSON.stringify(value));};
 const objects=['one','two','blocked'].map(id=>({id,canonicalName:id,visibility:'public',allowedConsumers:['LaRA'],authorityState:id==='blocked'?'QUARANTINED':'CANONICAL_AUTHORITATIVE'}));
 const reps=objects.map(object=>{const html='<h1>'+object.id+' architecture</h1><p>canonical content</p>';write(object.id+'.html',html);return {id:object.id+'-rep',representsObject:object.id,title:object.canonicalName+' architecture',canonicalUrl:'https://originopenfoundation.org/'+object.id+'.html',visibility:'public',allowedConsumers:['LaRA'],authorityState:'CANONICAL_AUTHORITATIVE',authorityDomain:['definition'],provenance:{sourcePath:object.id+'.html',contentHash:crypto.createHash('sha256').update(html).digest('hex')}};});
 write('data/knowledge/reports/lara-read-only-consumer-contract.json',{mode:'read-only',mutationAllowed:false});
 write('data/knowledge/reports/lara-integration-readiness.json',{reportOnly:true,LARA_INTEGRATION_READY:false});
 write('data/knowledge/objects-core.json',{objects});write('data/knowledge/representations.json',{representations:reps});
 write('data/knowledge/relationships.json',{relationships:[{sourceId:'one',targetId:'two',relationshipType:'containsStandard',authorityState:'AUTHORITATIVE'},{sourceId:'two',targetId:'one',relationshipType:'invented',authorityState:'DISCOVERY'}]});
 write('data/knowledge/indexes/object-by-canonical-url.json',{index:{'https://originopenfoundation.org/one.html':'one'}});
 write('data/knowledge/indexes/object-by-name.json',{index:{one:['one'],ambiguous:['one','two']}});
 write('data/knowledge/indexes/object-aliases.json',{index:{alias:[{objectId:'one',resolverEligible:true}],candidate:[{objectId:'one',resolverEligible:false}]}});
 return {root,write,reps};
}
test('shared consumer preserves identities, authority, relationships and bytes without writing a database',()=>{
 const {root}=fixture();try{
  const file=path.join(root,'data/knowledge/objects-core.json'),before=fs.readFileSync(file,'utf8');
  const index=readShared(root);assert.equal(index.report_only,true);assert.equal(index.resources.length,2);
  assert.equal(index.resources[0].object_id,'one');assert.equal(index.resources[0].resource_id,'one-rep');
  assert.equal(index.resources[0].related_resources[0].resource_id,'two-rep');assert.equal(index.resources[1].related_resources.length,0);
  assert.equal(fs.readFileSync(file,'utf8'),before);assert(!fs.existsSync(path.join(root,'lara/content/knowledge-index.json')));
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('exact lookup distinguishes approved aliases, ambiguity and missing or quarantined objects',()=>{
 const {root}=fixture();try{const index=readShared(root);assert.equal(exact(index,'alias').object.id,'one');assert.equal(exact(index,'ambiguous').status,'AMBIGUOUS');assert.equal(exact(index,'candidate').status,'NOT_FOUND');assert.equal(exact(index,'blocked').status,'NOT_FOUND');assert.equal(exact(index,'https://originopenfoundation.org/one.html').status,'FOUND');}finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('source changes fail closed and missing source or traversal never becomes evidence',()=>{
 const {root,write,reps}=fixture();try{write('one.html','changed content');reps[1].provenance.sourcePath='../outside.html';write('data/knowledge/representations.json',{representations:reps});const index=readShared(root);assert.equal(index.resources.length,0);assert.equal(index.diagnostics.changed,1);}finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('canonical precedence is preserved without promoting supporting explanations',()=>{
 const index={resources:[{resource_id:'supporting',title:'SIMULOS architecture architecture',canonical_url:'https://example.test/a',authority_state:'SUPPORTING_CITABLE',chunks:[]},{resource_id:'canonical',title:'SIMULOS',canonical_url:'https://example.test/z',authority_state:'CANONICAL_AUTHORITATIVE',chunks:[]}]};
 assert.equal(rank(index,'SIMULOS','en')[0].resource.resource_id,'canonical');
});
