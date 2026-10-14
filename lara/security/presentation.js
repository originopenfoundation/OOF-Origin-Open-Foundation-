'use strict';
// Presentation-only filtering; original canonical files/hashes remain intact.
function redact(value){return String(value||'')
 .replace(/-{2,}\s*Forwarded message[^\n]*(?:\n|$)/gi,'')
 .replace(/(?:Note:\s*-\s*)?(?:This e-mail\s*)?CONFIDENTIALITY NOTICE[\s\S]*?All rights reserved\./gi,'')
 .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi,'[contact redacted]')
 .replace(/\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,})\b/g,'[credential redacted]')
 .replace(/\b(password|passwd|secret|api[_ -]?key)\s*[:=]\s*[^\s,;]+/gi,'$1=[redacted]')
 .replace(/\n\s*\n(?:\s*\n)+/g,'\n\n').trim();}
function chunks(value,maximum=1500){const words=redact(value).split(/\s+/);const result=[];let text='';for(const word of words){if(text&&text.length+word.length+1>maximum){result.push({text});text='';}text+=(text?' ':'')+word;}if(text)result.push({text});return result;}
module.exports={redact,chunks};
