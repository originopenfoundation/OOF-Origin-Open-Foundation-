'use strict';
// Reusable deterministic navigation over the existing, hash-verified consumer
// view. Linguistic expansions are search terms, never architecture membership.
const STOP=new Set('a an the i we our my want need how can do which what is are for to of and or in with about governance architecture methodology standard module problem help'.split(' '));
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const words=s=>[...new Set((norm(s).match(/[\p{L}\p{N}]+/gu)||[]).filter(w=>w.length>1&&!STOP.has(w)))];
const EXPANSIONS={behavior:['behavioral'],behaviour:['behavioral'],ai:['artificial','intelligence'],autonomous:['autonomy'],system:['systems'],payments:['payment'],authorization:['permission','authorisation'],spravanie:['behavioral'],energia:['energy'],voda:['water'],softver:['software']};
const GENERAL=new Set(['ai','agent','control','authorization','authority','lifecycle','system','systems','infrastructure','resource','value']);
const pending=new Set(['discovered','draft','in-progress','pending']);
function lifecycle(object){
 const status=norm(object.status)||'unknown';
 if(/withdrawn|superseded/.test(status))return /withdrawn/.test(status)?'withdrawn':'superseded';
 if(/draft|development|in.progress|incomplete/.test(status))return /draft/.test(status)?'draft':'in-progress';
 if(pending.has(status))return status;
 if(object.authorityState==='CANONICAL_AUTHORITATIVE'&&(['completed','current','published','approved'].includes(status)||/^canonical\b/.test(status)))return 'approved-canonical';
 return ['published','completed','current','approved'].includes(status)||/^canonical\b/.test(status)?'published-pending':status==='unknown'?'unresolved':status;
}
function navigate(index,problem,{disabled=new Set(),limit=6}={}){
 const original=words(problem).slice(0,40),terms=[...new Set(original.flatMap(w=>[w,...(EXPANSIONS[w]||[])]))];
 const specific=original.filter(w=>!GENERAL.has(w)),domainTerms=specific.flatMap(w=>[w,...(EXPANSIONS[w]||[])]);
 const byId=index.byId||new Map((index.objects||[]).map(o=>[o.id,o]));
 const exactArchitectures=new Set((index.objects||[]).filter(o=>o.artifactType==='Architecture'&&o.acronym&&original.includes(norm(o.acronym))).map(o=>o.id));
 const resources=new Map();
 for(const r of index.resources||[]){
  if(disabled.has(r.resource_id)||!r.object_id||!r.provenance?.contentHash)continue;
  let url;try{url=new URL(r.canonical_url);}catch{continue;}
  if(url.origin!=='https://originopenfoundation.org'||url.username||url.password)continue;
  const list=resources.get(r.object_id)||[];list.push(r);resources.set(r.object_id,list);
 }
 const matches=[],unresolved=[];
 for(const o of index.objects||[]){
  if(!['Architecture','ParentStandard','CoreModule'].includes(o.artifactType))continue;
  if(exactArchitectures.size&&!exactArchitectures.has(o.id)&&!exactArchitectures.has(o.architectureId)&&!exactArchitectures.has(byId.get(o.parentObjectId)?.architectureId))continue;
  const title=new Set(words(`${o.canonicalName} ${o.acronym||''}`));
  const metadata=new Set(words(`${o.governedSpace||''} ${o.coreQuestion||''} ${o.canonicalDefinition||''}`));
  const architecture=byId.get(o.architectureId),parent=byId.get(o.parentObjectId);
  const inherited=new Set(words(`${architecture?.canonicalName||''} ${parent?.canonicalName||''}`));
  const titleTerms=terms.filter(t=>title.has(t)),metadataTerms=terms.filter(t=>metadata.has(t));
  const inheritedTerms=terms.filter(t=>inherited.has(t));
  const available=resources.get(o.id)||[];
  const bodyMatch=available.map(resource=>{const text=norm((resource.chunks||[]).map(c=>c.text).join(' ').slice(0,16000));return {resource,terms:terms.filter(t=>new RegExp('(?:^|[^\\p{L}\\p{N}])'+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?=$|[^\\p{L}\\p{N}])','u').test(text))};});
  const bodyTerms=[...new Set(bodyMatch.flatMap(match=>match.terms))];
  if(!titleTerms.length&&!metadataTerms.length&&!inheritedTerms.length&&!bodyTerms.length)continue;
  if(domainTerms.length&&!domainTerms.some(t=>title.has(t)||metadata.has(t)||inherited.has(t)||bodyTerms.includes(t)))continue;
  const state=lifecycle(o);
  if(!['CANONICAL_AUTHORITATIVE','SUPPORTING_CITABLE'].includes(o.authorityState)||state==='unresolved'||['withdrawn','superseded'].includes(state)){
   unresolved.push({object_id:o.id,title:o.canonicalName,status:state,authority_state:o.authorityState});continue;
  }
  if(!available.length)continue;
  const canonical=o.authorityState==='CANONICAL_AUTHORITATIVE'&&state==='approved-canonical';
  const domainInMetadata=!domainTerms.length||domainTerms.some(t=>title.has(t)||metadata.has(t)||inherited.has(t));
  const eligible=available.filter(r=>domainInMetadata||bodyMatch.some(match=>match.resource===r&&match.terms.some(t=>domainTerms.includes(t))));
  const resource=eligible.find(r=>r.canonical_url===o.canonicalUrl)||eligible.sort((a,b)=>(a.authority_state==='CANONICAL_AUTHORITATIVE'?0:1)-(b.authority_state==='CANONICAL_AUTHORITATIVE'?0:1)||a.resource_id.localeCompare(b.resource_id))[0];
  if(!resource)continue;
  const exact=original.includes(norm(o.acronym));
  const evidenceTerms=bodyMatch.find(match=>match.resource===resource)?.terms||[];
  const score=titleTerms.reduce((n,t)=>n+(GENERAL.has(t)?4:10),0)+metadataTerms.length*2+inheritedTerms.length*2+evidenceTerms.length+(exact?50:0)+(o.artifactType==='Architecture'&&titleTerms.some(t=>domainTerms.includes(t))?12:0);
  matches.push({object_id:o.id,title:o.canonicalName,artifact_type:o.artifactType,architecture_id:o.architectureId,parent_object_id:o.parentObjectId,
   lifecycle_status:state,authority_state:canonical&&resource.authority_state==='CANONICAL_AUTHORITATIVE'?'CANONICAL_AUTHORITATIVE':'SUPPORTING_CITABLE',relevance:titleTerms.length||metadataTerms.length?'primary':'supporting',score,
   reasons:{title_terms:titleTerms,metadata_terms:metadataTerms,inherited_terms:inheritedTerms,source_terms:evidenceTerms,exact_acronym:exact},url:resource.canonical_url,
   provenance:resource.provenance,resource_id:resource.resource_id});
 }
 matches.sort((a,b)=>(a.relevance==='primary'?0:1)-(b.relevance==='primary'?0:1)||b.score-a.score||a.object_id.localeCompare(b.object_id));
 const selected=matches.slice(0,Math.min(Math.max(limit,1),12));
 for(const seed of selected.slice(0,3)){
  const architecture=matches.find(m=>m.object_id===seed.architecture_id);
  if(architecture&&!selected.some(m=>m.object_id===architecture.object_id)&&selected.length>1){selected.pop();selected.push({...architecture,relevance:'supporting'});}
 }
 // Supporting hierarchy is only a label for declared registry relationships;
 // it neither invents a parent nor raises a draft's authority.
 for(const item of selected){
  if(selected.some(other=>other.object_id===item.architecture_id||other.object_id===item.parent_object_id))item.relevance='supporting';
 }
 return {version:'1.0',problem:String(problem).slice(0,5000),intent:'problem-to-methodology',terms,
  status:selected.length?'MATCHED':unresolved.length?'AUTHORITY_UNRESOLVED':'UNSUPPORTED',results:selected,unresolved,
  report_only:index.report_only!==false,model_explanation_verified:false,
  next_step:selected.length?'Review the linked source and its lifecycle status; define the decision, evidence and responsible authority.':'Clarify the operational domain and desired decision; no verified methodology match is available.'};
}
function explain(navigation,language='en'){
 const sk=language==='sk';
 if(!navigation.results.length)return (sk?'Nenašiel som overenú metodológiu pre tento problém. ':'No verified methodology match was found for this problem. ')+navigation.next_step;
 return `${sk?'Relevantné metodológie':'Relevant methodologies'}:\n`+navigation.results.map(r=>`${r.title} [${r.lifecycle_status}; ${r.relevance}]\n${sk?'Zhoda v zdroji':'Source match'}: ${[...new Set([...r.reasons.title_terms,...r.reasons.metadata_terms,...r.reasons.inherited_terms,...r.reasons.source_terms])].join(', ')}\n${r.url}`).join('\n\n')+'\n\n'+navigation.next_step;
}
module.exports={navigate,explain,lifecycle};
