'use strict';
const PUBLIC_ROUTES=new Set(['/_lara/status','/_lara/chat','/_lara/enquiry','/_lara/identity/create','/_lara/identity/restore','/_lara/session']);
function originPolicy(env={}){
 const allowed=new Set((env.LARA_ALLOWED_ORIGINS||'https://originopenfoundation.org,https://www.originopenfoundation.org').split(',').map(value=>value.trim()).filter(value=>{try{const u=new URL(value);return u.origin===value&&u.protocol==='https:';}catch{return false;}}));
 function accepts(req){const value=req.headers.origin;if(!value)return false;try{const u=new URL(value);return allowed.has(value)||(u.origin===value&&['http:','https:'].includes(u.protocol)&&u.host===req.headers.host);}catch{return false;}}
 function apply(req,res,pathname){
  if(!PUBLIC_ROUTES.has(pathname))return false;
  res.setHeader('Vary','Origin');
  if(req.headers.origin&&!accepts(req)){res.writeHead(403,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Origin is not allowed'}));return true;}
  if(req.headers.origin){res.setHeader('Access-Control-Allow-Origin',req.headers.origin);res.setHeader('Access-Control-Allow-Credentials','true');res.setHeader('Access-Control-Expose-Headers','X-LaRA-Session');}
  if(req.method==='OPTIONS'){
   const headers=String(req.headers['access-control-request-headers']||'').toLowerCase().split(',').map(x=>x.trim()).filter(Boolean);
   if(!accepts(req)||!['GET','POST','DELETE'].includes(req.headers['access-control-request-method'])||headers.some(h=>!['content-type','x-lara-session'].includes(h))){res.writeHead(403);res.end();return true;}
   res.setHeader('Access-Control-Allow-Methods','GET, POST, DELETE');res.setHeader('Access-Control-Allow-Headers','Content-Type, X-LaRA-Session');res.setHeader('Access-Control-Max-Age','600');res.writeHead(204);res.end();return true;
  }
  return false;
 }
 return {accepts,apply};
}
module.exports={originPolicy};
