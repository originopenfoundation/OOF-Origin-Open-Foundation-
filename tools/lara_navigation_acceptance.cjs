'use strict';
// Actual local HTTP/SSE integration, zero inference calls. No credential loading.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),net=require('node:net'),{spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const cases=[
 ['payment','AI agent payment authorization'],['behavior','AI behavioral governance'],
 ['autonomy','Autonomous system control'],['software','Software lifecycle governance SLGA'],
 ['energy','Energy infrastructure governance'],['water','Water resource governance'],
 ['value','Asset tokenization and value lifecycle'],['unknown','quantum pineapple mythology'],
 ['multiple','software and energy infrastructure']
];
async function run(){
 if(fs.existsSync(path.join(root,'.env')))throw Error('Run in a checkout without .env; this probe never accesses credentials');
 const reservation=net.createServer();await new Promise(r=>reservation.listen(0,'127.0.0.1',r));const port=reservation.address().port;await new Promise(r=>reservation.close(r));
 const base=`http://127.0.0.1:${port}`,report={revision:require('node:child_process').execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),provider:'none',authenticated_responses:0,model_acceptance:'NOT_TESTED',cases:[],result:'FAIL'};
 const child=spawn(process.execPath,['--max-old-space-size=256','lara/server.js'],{cwd:root,env:{...process.env,HOST:'127.0.0.1',PORT:String(port),NODE_ENV:'development',LLM_PROVIDER:'none',LLM_API_KEY:'',LARA_RATE_LIMIT_PER_MINUTE:'1000'},stdio:['ignore','pipe','pipe']});
 let errors='';child.stderr.on('data',p=>{errors=(errors+p).slice(-2000);});
 async function chat(question,mode='navigator',cookie){
  const started=performance.now(),response=await fetch(base+'/_lara/chat',{method:'POST',headers:{Origin:base,'Content-Type':'application/json',...(cookie?{Cookie:cookie}:{})},body:JSON.stringify({question,mode,language:'en'})});
  assert.equal(response.status,200,await response.clone().text());
  const events=(await response.text()).split('\n').filter(l=>l.startsWith('data: ')).map(l=>JSON.parse(l.slice(6)));
  const done=events.find(e=>e.done)?.done;assert(done);assert.equal(done.generation.provider,null);
  return {done,cookie:response.headers.get('set-cookie')?.split(';')[0]||cookie,latency_ms:performance.now()-started};
 }
 try{
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Server startup timeout')),90000);child.stdout.on('data',p=>{if(String(p).includes('listening on')){clearTimeout(timer);resolve();}});child.once('exit',code=>{clearTimeout(timer);reject(Error('Server exited '+code+': '+errors));});});
  for(const [id,question] of cases){
   const {done,latency_ms}=await chat(question),navigation=done.navigation;assert(navigation);
   assert.equal(navigation.report_only,true);assert.equal(navigation.model_explanation_verified,false);
   if(id==='unknown')assert.equal(navigation.status,'UNSUPPORTED');else assert(navigation.results.length>0,id);
   if(id==='software'){assert.equal(navigation.results[0].object_id,'OOF-KO-ARCH-SLGA');assert.equal(navigation.results[0].lifecycle_status,'in-progress');assert.equal(navigation.results[0].authority_state,'SUPPORTING_CITABLE');}
   const links=[];
   for(const result of navigation.results){
    assert(result.provenance.contentHash);const url=new URL(result.url);assert.equal(url.origin,'https://originopenfoundation.org');
    const response=await fetch(base+url.pathname);assert.equal(response.status,200,result.url);await response.body.cancel();links.push(result.url);
    if(['draft','pending','in-progress','published-pending'].includes(result.lifecycle_status))assert.equal(result.authority_state,'SUPPORTING_CITABLE');
   }
   report.cases.push({id,question,latency_ms,answer:done.answer,navigation,verified_links:links,status:'VERIFIED'});
  }
  const first=await chat('What is SLGA?','knowledge');assert.match(first.done.answer,/in-progress/);assert.match(first.done.answer,/not verified/);
  const followup=await chat('Is it approved?','knowledge',first.cookie);assert.match(followup.done.answer,/in-progress/);assert.match(followup.done.answer,/not verified/);
  report.lifecycle_communication={direct:first.done.answer,followup:followup.done.answer,status:'VERIFIED'};
  const isolated=await chat('Is it approved?','knowledge');assert(!isolated.done.answer.includes('SLGA'));report.session_isolation='VERIFIED';
  const {navigate}=require('../lara/knowledge/navigator');
  const conflict=navigate({objects:[{id:'conflict',canonicalName:'Conflicting software authority',artifactType:'Architecture',status:'completed',authorityState:'QUARANTINED'}],resources:[],report_only:true},'software');
  assert.equal(conflict.status,'AUTHORITY_UNRESOLVED');assert.equal(conflict.results.length,0);
  report.cases.push({id:'conflicting-authority',fixture:true,status:'VERIFIED',navigation:conflict});
  report.result='PASS';
 }catch(error){report.error=error.message;process.exitCode=1;}finally{child.kill();const output=path.resolve(process.argv[2]||'lara-navigation-evidence.json');fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({result:report.result,cases:report.cases.length,error:report.error,output}));}
}
run().catch(error=>{console.error(error.message);process.exitCode=1;});
