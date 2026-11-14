'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const http=require('node:http');
const {createGateway}=require('../../lib/oof-llm');

test('local provider rejects remote endpoints and cloud fallback',()=>{
 const env={LLM_PROVIDER:'llama.cpp',LLM_MODEL:'local'};
 assert.throws(()=>createGateway({...env,LLM_BASE_URL:'https://example.com/v1'}),{kind:'invalid_configuration'});
 assert.throws(()=>createGateway({...env,LLM_FALLBACK_PROVIDER:'groq'}),{kind:'invalid_configuration'});
});

test('local provider exchanges JSON and SSE over loopback without a cloud key',async()=>{
 let request;
 const server=http.createServer(async(req,res)=>{
  const parts=[];
  for await(const part of req)parts.push(part);
  request={path:req.url,auth:req.headers.authorization,body:JSON.parse(Buffer.concat(parts))};
  if(request.body.stream){
   res.setHeader('Content-Type','text/event-stream');
   res.end('data: {"model":"local","choices":[{"delta":{"content":"Ahoj"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n');
  }else res.end(JSON.stringify({model:'local',choices:[{message:{content:'Ahoj'}}]}));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  for(const streaming of ['true','false']){
   const gateway=createGateway({LLM_PROVIDER:'llama.cpp',LLM_MODEL:'local',LLM_STREAM:streaming,
    LLM_API_KEY:'cloud-credential',LLM_BASE_URL:'http://127.0.0.1:'+server.address().port+'/v1'});
   const result=await gateway.generateDetailed({question:'Ahoj',language:'Slovak',history:[{role:'user',text:'Predošlá otázka'}]});
   assert.equal(result.answer,'Ahoj');
   assert.equal(result.fallback_used,false);
   assert.equal(request.path,'/v1/chat/completions');
   assert.equal(request.auth,undefined);
   assert.equal(Boolean(request.body.stream),streaming==='true');
   assert.equal(JSON.parse(request.body.messages[1].content).conversation_history.length,1);
  }
 }finally{await new Promise(resolve=>server.close(resolve));}
});
