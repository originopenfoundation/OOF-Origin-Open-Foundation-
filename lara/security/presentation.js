'use strict';
// Presentation-only filtering; original canonical files/hashes remain intact.
function redact(value){return String(value||'')
 .replace(/-{2,}\s*Forwarded message[^\n]*(?:\n|$)/gi,'')
 .replace(/(?:Note:\s*-\s*)?(?:This e-mail\s*)?CONFIDENTIALITY NOTICE[\s\S]*?All rights reserved\./gi,'')
 .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi,'[contact redacted]')
 .replace(/\b(?:(?:sk-|gsk_)[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,})\b/g,'[credential redacted]')
 .replace(/\b(password|passwd|secret|api[_ -]?key)\s*[:=]\s*[^\s,;]+/gi,'$1=[redacted]')
 .replace(/\n\s*\n(?:\s*\n)+/g,'\n\n').trim();}
function chunks(value,maximum=1500){
 const result=[];let words=[],size=0;
 // Join each bounded chunk once. Repeated += retains a rope node and word
 // backing storage for every token across the entire in-memory registry.
 for(const match of redact(value).matchAll(/\S+/g)){
  const word=match[0];
  if(size&&size+1+word.length>maximum){result.push({text:words.join(' ')});words=[];size=0;}
  words.push(word);size+=word.length+(words.length>1?1:0);
 }
 if(words.length)result.push({text:words.join(' ')});
 return result;
}
module.exports={redact,chunks};
