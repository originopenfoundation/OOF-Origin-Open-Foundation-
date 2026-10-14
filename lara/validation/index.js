'use strict';
function validate(answer, question, sources) {
  if(typeof answer!=='string'||!answer.trim()||answer.length>20000)return {ok:false,reason:'empty_or_oversized'};
  if(!sources.length)return {ok:false,reason:'missing_evidence'};
  // User input is not evidence for a generated canonical claim.
  const trusted=sources.map(s=>`${s.title} ${s.text}`).join(' ');
  if(/(?:[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:sk-|gh[pousr]_)[A-Za-z0-9_-]{16,})/i.test(answer))return {ok:false,reason:'private_contact_or_credential'};
  for(const sentence of answer.split(/[.!?\n]/)){
   if(/\b(?:legally binding|approved by OOF|I (?:have )?(?:approved|submitted|changed|sent)|permanent memory)\b/i.test(sentence)&&!/\b(?:not|cannot|can't|never|no|without)\b/i.test(sentence))return {ok:false,reason:'unsupported_authority_or_action'};
  }
  const normalized=value=>value.toLowerCase().replace(/[®™]/g,'').replace(/\s+/g,' ').trim();
  const evidence=normalized(trusted);
  for(const name of answer.matchAll(/\b(?:[A-Z][A-Za-z0-9®™-]*\s+){1,5}(?:Standard|Architecture|Module)\b/g)){
   const title=normalized(name[0].replace(/^(?:The|A|An)\s+/,''));
   if(!evidence.includes(title))return {ok:false,reason:'unsupported_named_resource'};
  }
  const acronyms=[...answer.matchAll(/\b[A-Z][A-Z0-9]{2,10}\b/g)].map(m=>m[0]);
  if(acronyms.some(word=>!new RegExp(`\\b${word}\\b`,'i').test(trusted)))return {ok:false,reason:'unsupported_acronym'};
  const numbers=[...answer.matchAll(/\b\d+(?:[.,]\d+)?\b/g)].map(m=>m[0]);
  if(numbers.some(n=>!trusted.includes(n)))return {ok:false,reason:'unsupported_number'};
  return {ok:true};
}
module.exports={validate};
