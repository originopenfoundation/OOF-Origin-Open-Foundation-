'use strict';
const crypto=require('node:crypto'),fs=require('node:fs'),path=require('node:path');
const copy=x=>JSON.parse(JSON.stringify(x));
const ACTIVATION=new Set(['DISABLED','TESTING','SHADOW','ENABLED','QUARANTINED']);
class CapabilityRegistry{
 constructor(items=[]){this.items=new Map();items.forEach(x=>this.register(x));}
 register(input){const item={id:String(input.id||''),state:input.state||'DISABLED',dependencies:[...(input.dependencies||[])],evidence:[...(input.evidence||[])],updated_at:new Date().toISOString()};if(!/^[a-z][a-z0-9._-]{2,80}$/.test(item.id)||!ACTIVATION.has(item.state))throw Error('Invalid capability');this.items.set(item.id,item);return copy(item);}
 transition(id,state,{verified=false,authorization=false}={}){const item=this.items.get(id);if(!item||!ACTIVATION.has(state))throw Error('Invalid capability transition');if(state==='ENABLED'&&(!verified||!authorization))throw Error('Enabled capability requires verification and authorization');item.state=state;item.updated_at=new Date().toISOString();return copy(item);}
 assert(id){const item=this.items.get(id);if(!item||item.state!=='ENABLED')throw Error('Capability is not enabled');if(item.dependencies.some(dep=>this.items.get(dep)?.state!=='ENABLED'))throw Error('Capability dependency is unavailable');return copy(item);}
 snapshot(){return [...this.items.values()].map(copy);}
}
class WorkflowEngine{
 constructor({handlers={},capabilities=new CapabilityRegistry()}={}){this.handlers=handlers;this.capabilities=capabilities;this.audit=[];}
 async run(definition,input,{signal}={}){if(!definition?.id||!Array.isArray(definition.steps)||!definition.steps.length)throw Error('Invalid workflow');if(signal?.aborted)throw Error('Workflow cancelled');if(definition.capability)this.capabilities.assert(definition.capability);const record={run_id:crypto.randomUUID(),workflow:definition.id,started_at:new Date().toISOString(),state:'RUNNING',steps:[]};this.audit.push(record);try{let value=copy(input||{});for(const step of definition.steps){if(signal?.aborted)throw Error('Workflow cancelled');const handler=this.handlers[step];if(typeof handler!=='function')throw Error(`Missing workflow step: ${step}`);value=await handler(copy(value),{workflow:definition.id});record.steps.push({step,state:'COMPLETED'});}record.state='COMPLETED';record.output_digest=crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');return {run_id:record.run_id,state:record.state,output:value};}catch(error){record.state=String(error.message)==='Workflow cancelled'?'CANCELLED':'FAILED';record.error=String(error.message).slice(0,240);throw error;}finally{record.finished_at=new Date().toISOString();}}
 snapshot(){return copy(this.audit.slice(-100));}
}
function scientific(values){const xs=(values||[]).map(Number).filter(Number.isFinite);if(xs.length<2)throw Error('Two numeric values required');const mean=xs.reduce((a,b)=>a+b,0)/xs.length,variance=xs.reduce((a,b)=>a+(b-mean)**2,0)/(xs.length-1),sd=Math.sqrt(variance);const sorted=[...xs].sort((a,b)=>a-b),median=sorted.length%2?sorted[(sorted.length-1)/2]:(sorted[sorted.length/2-1]+sorted[sorted.length/2])/2;return {count:xs.length,mean,median,variance,sd,confidence95:{low:mean-1.96*sd/Math.sqrt(xs.length),high:mean+1.96*sd/Math.sqrt(xs.length)},anomalies:xs.map((value,index)=>({index,value,z:sd?Math.abs((value-mean)/sd):0})).filter(x=>x.z>=3)};}
function bayes({prior,likelihood,alternative}){for(const x of [prior,likelihood,alternative])if(!(x>=0&&x<=1))throw Error('Probability out of range');const denominator=prior*likelihood+(1-prior)*alternative;if(!denominator)throw Error('Undefined posterior');return {posterior:prior*likelihood/denominator};}
class PersistentSessions{
 constructor(file,{retentionMs=7*24*60*60*1000,now=()=>Date.now()}={}){this.file=file;this.retentionMs=retentionMs;this.now=now;this.data=this.read();}
 read(){try{return JSON.parse(fs.readFileSync(this.file,'utf8'));}catch{return {sessions:{}};}}
 save(){fs.mkdirSync(path.dirname(this.file),{recursive:true});fs.writeFileSync(this.file,JSON.stringify(this.data,null,2),{mode:0o600});}
 put(tenant,id,value){if(!/^[a-z0-9_-]{3,40}$/i.test(id))throw Error('Invalid session id');this.data.sessions[`${tenant}:${id}`]={tenant,value:copy(value),expires:this.now()+this.retentionMs};this.save();}
 get(tenant,id){const item=this.data.sessions[`${tenant}:${id}`];if(!item||item.expires<this.now()||item.tenant!==tenant)return null;return copy(item.value);}
 delete(tenant,id){delete this.data.sessions[`${tenant}:${id}`];this.save();}
}
function engineContract(id,{input_schema='object',output_schema='object',authorization='read_only',timeout_ms=15000,budget=0}={}){if(!/^[a-z][a-z0-9._-]{2,80}$/.test(id)||/write|deploy|publish/.test(authorization))throw Error('Invalid engine contract');return {interface_version:'lara.cross-engine/1.0',id,input_schema,output_schema,authorization,timeout_ms:Math.max(1000,timeout_ms),budget:Math.max(0,budget),provenance_required:true,failure_mode:'fail_closed'};}
module.exports={CapabilityRegistry,WorkflowEngine,scientific,bayes,PersistentSessions,engineContract,ACTIVATION};

