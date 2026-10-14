'use strict';
const {queryTerms}=require('../language');
const normalized=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const tokens=value=>new Set(normalized(value).match(/[\p{L}\p{N}-]+/gu)||[]);
const tokenCache=new WeakMap();
function rank(index, query, lang, disabled=new Set(), limit=5) {
  const terms=queryTerms(query,lang).map(normalized); const q=normalized(query);
  if(!terms.length) return [];
  if(terms.every(t=>['oof','originopen','foundation'].includes(t)))return (index.resources||[]).filter(r=>!disabled.has(r.resource_id)&&r.provenance?.sourcePath==='index.html').map(resource=>({resource,score:1}));
  const scored=(index.resources||[]).filter(r=>!disabled.has(r.resource_id)).map(r=>{
    const title=(r.title||'').toLocaleLowerCase(), meta=[...(r.keywords||[]),...(r.topics||[]),r.architecture||'',r.parent_standard||'',r.module||''].join(' ').toLocaleLowerCase();
    if(!tokenCache.has(r))tokenCache.set(r,{title:tokens(title),meta:tokens(meta),body:tokens((r.chunks||[]).map(c=>c.text).join(' '))});
    let score=0,matched=0,anchors=0;const {title:titleWords,meta:metaWords,body:bodyWords}=tokenCache.get(r);
    for(const term of terms){const direct=titleWords.has(term)||metaWords.has(term),body=bodyWords.has(term);if(direct||body)matched++;if(direct){score+=10;anchors++;}else if(body)score+=1;}
    if(!anchors||matched<Math.max(1,Math.ceil(terms.length*0.6)))return {resource:r,score:0};
    const cleanTitle=normalized(r.title).replace(/^oof[®™]?\s*/,'');
    if(cleanTitle.startsWith(terms.join(' ')))score+=40;
    const acr=(r.title||'').match(/\(([A-Z][A-Z0-9-]{1,12})\)/)?.[1]; if(acr&&terms.includes(acr.toLocaleLowerCase()))score+=20;
    if(score>0&&r.resource_type==='Architecture')score+=1;
    return {resource:r,score};
  }).sort((a,b)=>(a.resource.authority_state==='SUPPORTING_CITABLE'?1:0)-(b.resource.authority_state==='SUPPORTING_CITABLE'?1:0)||b.score-a.score||a.resource.canonical_url.localeCompare(b.resource.canonical_url));
  const matches=scored.filter(x=>x.score>0);const selected=matches.slice(0,limit);const byId=new Map(scored.map(x=>[x.resource.resource_id,x]));const expanded=new Map(selected.map(x=>[x.resource.resource_id,x]));
  // Expand only OOF registry-declared relationships from strong source matches.
  for(const seed of selected.slice(0,3))for(const edge of seed.resource.related_resources||[]){if(!['AUTHORITATIVE','VALIDATED_AUTHORITATIVE'].includes(edge.authority))continue;const candidate=byId.get(edge.resource_id);if(candidate&&!expanded.has(edge.resource_id))expanded.set(edge.resource_id,{...candidate,score:0,related_via:seed.resource.resource_id});}
  return [...expanded.values()].slice(0,Math.min(limit+3,8));
}
module.exports={rank};
