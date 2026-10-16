'use strict';
// Full real registry/server regression under the same V8 heap cap as Render.
// Run from a clean/disposable checkout: node tests/lara/memory-smoke.cjs [output.json]
const fs=require('node:fs'),path=require('node:path'),net=require('node:net'),assert=require('node:assert/strict');
if(process.argv[2]==='--worker'){
 process.on('message',message=>{if(message==='stats')process.send({memory:process.memoryUsage(),max_rss_kib:process.resourceUsage().maxRSS});});
 require('../../lara/server');
}else{
 const {fork}=require('node:child_process');
 (async()=>{
  const reservation=net.createServer();await new Promise(r=>reservation.listen(0,'127.0.0.1',r));const port=reservation.address().port;await new Promise(r=>reservation.close(r));
  const started=Date.now(),report={heap_limit_mib:256,node:process.version,queries:0,result:'FAIL'};
  const child=fork(__filename,['--worker'],{execArgv:['--max-old-space-size=256'],silent:true,env:{...process.env,HOST:'127.0.0.1',PORT:String(port),NODE_ENV:'production',LLM_PROVIDER:'none',LARA_RATE_LIMIT_PER_MINUTE:'1000'}});
  let errors='';child.stderr.on('data',part=>{errors=(errors+part).slice(-2000);});
  try{
   await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(Error('Actual server startup exceeded 90 seconds')),90000);child.stdout.on('data',part=>{if(String(part).includes('listening on')){clearTimeout(timeout);resolve();}});child.once('exit',code=>{clearTimeout(timeout);reject(Error('Actual server exited before ready: '+code));});child.once('error',reject);});
   report.startup_ms=Date.now()-started;
   const base=`http://127.0.0.1:${port}`;report.status=await (await fetch(base+'/_lara/status')).json();
   assert.equal(report.status.available,true);assert(report.status.indexed_resources>0);assert.equal(report.status.llm_configured,false,'Run against a clean checkout without saved provider overrides');
   for(let i=0;i<30;i++){
    const question=['What is OOF?','Explain governance in simple language.','What is SIMULOS?','Explain authority governance.','What is AI governance?'][i%5];
    const response=await fetch(base+'/_lara/chat',{method:'POST',headers:{Origin:'https://originopenfoundation.org','Content-Type':'application/json'},body:JSON.stringify({question,language:'en'})});
    assert.equal(response.status,200);const events=(await response.text()).split('\n').filter(line=>line.startsWith('data: ')).map(line=>JSON.parse(line.slice(6)));assert(events.some(event=>event.done?.answer));report.queries++;
   }
   report.worker=await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(Error('Memory sample timeout')),5000);child.once('message',message=>{clearTimeout(timeout);resolve(message);});child.send('stats');});
   assert(report.worker.memory.heapUsed<256*1024*1024);assert(report.worker.memory.rss<512*1024*1024,'Observed worker RSS exceeded free instance RAM');report.result='PASS';
  }catch(error){report.error=error.message;report.worker_stderr=errors;process.exitCode=1;}
  finally{child.kill();report.duration_ms=Date.now()-started;if(process.argv[2])fs.writeFileSync(path.resolve(process.argv[2]),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
 })().catch(error=>{console.error(error.message);process.exitCode=1;});
}
