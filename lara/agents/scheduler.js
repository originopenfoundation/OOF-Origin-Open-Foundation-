'use strict';
// Durable, bounded scheduler. It never enables itself from a web request.
const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');
const STATES=new Set(['SCHEDULED','RUNNING','COMPLETED','FAILED','BLOCKED','CANCELLED']);
const copy=value=>JSON.parse(JSON.stringify(value));
function safeRead(file,fallback){try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch{return fallback;}}
class Scheduler {
  constructor({file,now=()=>Date.now(),run,intervalMs=6*60*60*1000,maxAttempts=3,timeoutMs=30_000,budget=24}={}){
    if(typeof run!=='function')throw Error('Scheduler requires a run function');
    this.file=file;this.now=now;this.run=run;this.intervalMs=Math.max(60_000,intervalMs);this.maxAttempts=Math.max(1,maxAttempts);this.timeoutMs=Math.max(1000,timeoutMs);this.budget=Math.max(1,budget);
    this.state=safeRead(file,{version:'1.0',jobs:{},history:[],checkpoints:{}});this.state.jobs||={};this.state.history||=[];this.state.checkpoints||={};
    this.recover();
  }
  persist(){if(!this.file)return;fs.mkdirSync(path.dirname(this.file),{recursive:true});const pending=this.file+'.pending';fs.writeFileSync(pending,JSON.stringify(this.state,null,2)+'\n',{mode:0o600});fs.renameSync(pending,this.file);}
  recover(){const time=this.now();for(const job of Object.values(this.state.jobs)){if(job.state==='RUNNING'){job.state='SCHEDULED';job.lock=null;job.next_run_at=Math.min(job.next_run_at||time,time);job.recovered_at=new Date(time).toISOString();}}this.persist();}
  schedule(agentId,{intervalMs=this.intervalMs,payload={}}={}){if(!/^[a-z][a-z0-9._-]{2,80}$/.test(agentId))throw Error('Invalid agent id');const old=this.state.jobs[agentId],time=this.now();const job=old||{agent_id:agentId,created_at:new Date(time).toISOString(),runs:0,attempt:0};Object.assign(job,{interval_ms:Math.max(60_000,intervalMs),payload:copy(payload),state:'SCHEDULED',next_run_at:old?.next_run_at??time,updated_at:new Date(time).toISOString()});this.state.jobs[agentId]=job;this.persist();return copy(job);}
  cancel(agentId){const job=this.state.jobs[agentId];if(!job)return null;if(job.state==='RUNNING')throw Error('Cannot cancel a running job');job.state='CANCELLED';job.updated_at=new Date(this.now()).toISOString();this.persist();return copy(job);}
  canRun(agentId){const since=this.now()-24*60*60*1000;return this.state.history.filter(x=>x.agent_id===agentId&&x.started_at>=since).length<this.budget;}
  async runDue({agentId=null,event=null}={}){const time=this.now();const candidates=Object.values(this.state.jobs).filter(job=>job.state==='SCHEDULED'&&(!agentId||job.agent_id===agentId)&&(event||job.next_run_at<=time));const results=[];for(const job of candidates)results.push(await this.execute(job,event));return results;}
  async execute(job,event){const time=this.now();if(job.state==='RUNNING')return {state:'BLOCKED',reason:'duplicate_execution'};if(!this.canRun(job.agent_id)){job.state='BLOCKED';job.blocked_reason='budget_exhausted';this.persist();return copy(job);}
    const id=crypto.randomUUID(),record={execution_id:id,agent_id:job.agent_id,started_at:time,event:event||null,state:'RUNNING',model_calls:0,cost:null};job.state='RUNNING';job.lock=id;job.updated_at=new Date(time).toISOString();this.state.history.push(record);this.persist();
    let timer;try{const output=await Promise.race([Promise.resolve(this.run(copy(job),{event,timeoutMs:this.timeoutMs})),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Object.assign(Error('Execution timed out'),{kind:'timeout'})),this.timeoutMs);})]);record.state='COMPLETED';record.outcome=copy(output||{});record.model_calls=Number(output?.model_calls)||0;record.cost=output?.cost??null;job.state='SCHEDULED';job.attempt=0;job.runs++;job.next_run_at=time+job.interval_ms;this.state.checkpoints[job.agent_id]={execution_id:id,completed_at:this.now(),outcome_digest:crypto.createHash('sha256').update(JSON.stringify(record.outcome)).digest('hex')};}
    catch(error){record.state='FAILED';record.error=String(error.message||'execution_failed').slice(0,240);job.attempt=(job.attempt||0)+1;if(job.attempt>=this.maxAttempts){job.state='FAILED';job.next_run_at=null;}else{job.state='SCHEDULED';job.next_run_at=time+Math.min(job.interval_ms,1000*2**job.attempt);}}
    finally{clearTimeout(timer);record.finished_at=this.now();job.lock=null;job.updated_at=new Date(this.now()).toISOString();this.state.history=this.state.history.slice(-500);this.persist();}
    return copy(record);
  }
  snapshot(){return copy({jobs:Object.values(this.state.jobs),history:this.state.history.slice(-50),checkpoints:this.state.checkpoints});}
}
module.exports={Scheduler,STATES};
