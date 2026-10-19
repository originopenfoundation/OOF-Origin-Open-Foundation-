'use strict';
// Read-only, in-memory view of the shared registry. No new knowledge database.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chunks:presentedChunks}=require('../security/presentation');
const ALLOWED=new Set(['CANONICAL_AUTHORITATIVE','SUPPORTING_CITABLE']);
const normalize=value=>String(value).toLowerCase().replace(/[®™]/g,'').replace(/\babout\b/g,' ').replace(/\([^)]*\)/g,' ').replace(/[^a-z0-9]+/g,' ').trim();
const accessible=item=>item.visibility==='public'&&Array.isArray(item.allowedConsumers)&&item.allowedConsumers.includes('LaRA')&&ALLOWED.has(item.authorityState);
function textOf(html){return html.replace(/<!--[\s\S]*?-->/g,' ').replace(/<(script|style|noscript|svg|nav|footer)\b[^>]*>[\s\S]*?<\/\1\s*>/gi,' ').replace(/<\/(p|div|section|article|li|h[1-6]|tr|main)>/gi,'\n').replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&nbsp;/g,' ').replace(/&#(x[0-9a-f]+|[0-9]+);/gi,(m,n)=>{const code=n[0].toLowerCase()==='x'?parseInt(n.slice(1),16):Number(n);return Number.isInteger(code)&&code>=0&&code<=0x10ffff?String.fromCodePoint(code):m;}).replace(/[\t\r ]+/g,' ').replace(/\n{3,}/g,'\n\n').trim();}
function readShared(root){
 const base=path.join(root,'data/knowledge'),read=file=>JSON.parse(fs.readFileSync(path.join(base,file),'utf8'));
 const contract=read('reports/lara-read-only-consumer-contract.json');
 if(contract.mode!=='read-only'||contract.mutationAllowed!==false)throw Error('Unsupported LaRA knowledge contract');
 const readiness=read('reports/lara-integration-readiness.json');
 const objects=read('objects-core.json').objects,byId=new Map(objects.map(o=>[o.id,o]));
 const representations=read('representations.json').representations;
 const resources=[],diagnostics={excluded:0,missing:0,changed:0};
 for(const rep of representations){
  const object=rep.representsObject?byId.get(rep.representsObject):null;
  if(!accessible(rep)||(rep.representsObject&&(!object||!accessible(object)))){diagnostics.excluded++;continue;}
  const relative=rep.provenance?.sourcePath;
  if(typeof relative!=='string'||!relative.endsWith('.html'))continue;
  const file=path.resolve(root,relative);
  if(!file.startsWith(path.resolve(root)+path.sep)){diagnostics.excluded++;continue;}
  let html;try{html=fs.readFileSync(file,'utf8');}catch{diagnostics.missing++;continue;}
  const source=html.replace(/<!-- OOF AI DISCOVERY START -->[\s\S]*?<!-- OOF AI DISCOVERY END -->\s*/g,'').replace(/\r\n|\r/g,'\n');
  const hash=crypto.createHash('sha256').update(source).digest('hex');
  if(hash!==rep.provenance.contentHash){diagnostics.changed++;continue;}
  const text=textOf(html),chunks=presentedChunks(text);
  resources.push({resource_id:rep.id,object_id:object?.id||null,representation_id:rep.id,
   title:rep.title,resource_type:object?.artifactType||rep.artifactTypeHint||'Methodology Resource',
   canonical_url:rep.canonicalUrl,authority_state:rep.authorityState,authority_domain:rep.authorityDomain,
   provenance:rep.provenance,canonical_language:rep.language,keywords:[object?.acronym,object?.canonicalName].filter(Boolean),
   topics:[],chunks,related_resources:[]});
 }
 const canonicalByObject=new Map(resources.filter(r=>r.authority_state==='CANONICAL_AUTHORITATIVE').map(r=>[r.object_id,r]));
 for(const edge of read('relationships.json').relationships){
  if(!['AUTHORITATIVE','VALIDATED_AUTHORITATIVE'].includes(edge.authorityState))continue;
  const source=canonicalByObject.get(edge.sourceId),target=canonicalByObject.get(edge.targetId);
  if(source&&target)source.related_resources.push({resource_id:target.resource_id,relationship:edge.relationshipType,authority:edge.authorityState});
 }
 const inventory_digest=crypto.createHash('sha256').update(resources.map(r=>`${r.resource_id}:${r.provenance.contentHash}`).sort().join('\n')).digest('hex');
 let registry_fingerprint=null;try{registry_fingerprint=read('manifest.json').buildFingerprint;}catch{}
 return {resources,resource_count:resources.length,inventory_digest,registry_fingerprint,objects,byId,byUrl:read('indexes/object-by-canonical-url.json').index,
  byName:read('indexes/object-by-name.json').index,aliases:read('indexes/object-aliases.json').index,
  readiness,report_only:readiness.reportOnly!==false||readiness.LARA_INTEGRATION_READY!==true,diagnostics};
}
function exact(index,value){
 const direct=index.byId.has(value)?value:index.byUrl[value];
 const ids=direct?[direct]:(index.byName[normalize(value)]||(index.aliases[normalize(value)]||[]).filter(a=>a.resolverEligible===true).map(a=>a.objectId));
 const eligible=[...new Set(ids)].map(id=>index.byId.get(id)).filter(o=>o&&accessible(o));
 if(eligible.length>1)return {status:'AMBIGUOUS',object:null,candidateIds:eligible.map(o=>o.id)};
 if(eligible.length===1)return {status:'FOUND',object:eligible[0]};
 return {status:'NOT_FOUND',object:null};
}
module.exports={readShared,exact,textOf};
