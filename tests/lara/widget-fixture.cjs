'use strict';
// Isolated UI contract fixture. No external model calls or credentials.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');let state={state:'configured_not_verified',quota_restricted:false},until=0,chat=0,status=0,sessionHeaders=[];
const app=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname==='/')return res.end('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LaRA quota contract fixture - no real model</title><link rel="stylesheet" href="/assets/lara/lara.css"><body><h1>LaRA quota contract fixture</h1><p>Controlled engineering responses. No real inference.</p><script>window.LARA_API_BASE=location.origin;</script><script src="/assets/lara/lara.js"></script></body></html>');
 if(url.pathname.startsWith('/assets/lara/')&&['.js','.css','.jpg'].includes(path.extname(url.pathname))){res.setHeader('Content-Type',url.pathname.endsWith('.js')?'text/javascript; charset=utf-8':url.pathname.endsWith('.jpg')?'image/jpeg':'text/css; charset=utf-8');res.setHeader('Cache-Control','no-store');return res.end(fs.readFileSync(path.join(root,url.pathname)));}
 if(url.pathname==='/data/localization/lara-language-inventory.json'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({languages:[]}));}
 if(url.pathname==='/_lara/status'){status++;if(state.quota_restricted&&Date.now()>=until)state={...state,state:'recheck_required',retry_after:0};res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({model_availability:state}));}
 if(url.pathname==='/fixture/counters'){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({chat,status,sessionHeaders,state}));}
 if(url.pathname==='/_lara/chat'){
  chat++;sessionHeaders.push(req.headers['x-lara-session']||null);let raw='';for await(const p of req)raw+=p;const q=JSON.parse(raw).question;
  if(q==='network'){req.socket.destroy();return;}
  if(q==='timeout'){state={state:'unavailable',quota_restricted:false,reason:'timeout'};}
  else if(q==='model'){state={state:'unavailable',quota_restricted:false,reason:'model_unavailable'};}
  if(q==='clock-skew'){until=Date.now()+3000;state={state:'cooldown',quota_restricted:true,restriction:'rate_limit_unknown',retry_after:3,recheck_at:new Date(Date.now()-60000).toISOString(),reset_known:false};}
  else if(q==='checking'){until=Date.now()-1;state={state:'checking',quota_restricted:true,restriction:'rate_limit_unknown',retry_after:0,recheck_at:new Date(until).toISOString()};}
  else if(q==='quota'){until=Date.now()+30000;state={state:'cooldown',quota_restricted:true,restriction:'daily_requests',retry_after:30,recheck_at:new Date(until).toISOString(),reset_at:null,reset_known:false};}
  else if(!['timeout','model'].includes(q))state=q==='auth'?{state:'unavailable',quota_restricted:false,reason:'authentication_error'}:{state:'available',quota_restricted:false};
  res.writeHead(200,{'Content-Type':'text/event-stream','X-LaRA-Session':'synthetic-ui-session'});
  return res.end('data: '+JSON.stringify({done:{answer:state.quota_restricted?'Controlled quota preview.':q==='auth'?'Controlled authentication error preview.':'Controlled fixture answer.',language:'en',sources:[],generation:{kind:state.quota_restricted?'preview':'model',reason:state.quota_restricted?'rate_limited':null},model_availability:state}})+'\n\n');
 }
 res.writeHead(404);res.end();
});
app.listen(Number(process.env.LARA_WIDGET_TEST_PORT)||0,'127.0.0.1',()=>console.log('UI_FIXTURE http://127.0.0.1:'+app.address().port));
