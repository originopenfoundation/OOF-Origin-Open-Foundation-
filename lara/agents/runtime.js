'use strict';
const crypto=require('node:crypto');
const ALLOWED_PERMISSIONS=new Set(['knowledge:read','website:read','research:organize']);
const STATES=new Set(['REGISTERED','RUNNING','STOPPED','FAILED','DISABLED']);
const copy=value=>JSON.parse(JSON.stringify(value));
function validateDefinition(input){
 const value=copy(input||{});if(value.interface_version!=='lara.agent.runtime/1.0')throw Error('Unsupported agent interface version');
 if(!/^[a-z][a-z0-9._-]{2,80}$/.test(value.id||''))throw Error('Invalid agent id');
 if(!Array.isArray(value.capabilities)||!value.capabilities.length)throw Error('Agent requires capabilities');
 if(!Array.isArray(value.permissions)||value.permissions.some(permission=>!ALLOWED_PERMISSIONS.has(permission)))throw Error('Agent permission is not allowed');
 if(value.permissions.some(permission=>/write|deploy|publish|notify|execute/.test(permission)))throw Error('Operational permissions are prohibited');
 value.version=String(value.version||'1.0');value.knowledge_scope=Array.isArray(value.knowledge_scope)?value.knowledge_scope:[];
 value.budget={max_runs_per_day:Math.max(1,Number(value.budget?.max_runs_per_day)||1),timeout_ms:Math.max(1000,Number(value.budget?.timeout_ms)||30_000),model_calls:Math.max(0,Number(value.budget?.model_calls)||0)};
 value.enabled=value.enabled!==false;return value;
}
class AgentRuntime {
 constructor({handlers={},now=()=>Date.now()}={}){this.handlers=handlers;this.now=now;this.agents=new Map();this.audit=[];}
 register(definition){const agent=validateDefinition(definition);this.agents.set(agent.id,{definition:agent,state:agent.enabled?'REGISTERED':'DISABLED',runs:0,last_error:null});this.record(agent.id,'REGISTERED');return this.status(agent.id);}
 start(id){const agent=this.require(id);if(!agent.definition.enabled)throw Error('Agent is disabled');if(agent.state==='RUNNING')throw Error('Agent is already running');agent.state='RUNNING';this.record(id,'STARTED');return this.status(id);}
 stop(id){const agent=this.require(id);if(agent.state==='RUNNING')agent.state='STOPPED';this.record(id,'STOPPED');return this.status(id);}
 disable(id){const agent=this.require(id);if(agent.state==='RUNNING')throw Error('Stop agent before disabling it');agent.definition.enabled=false;agent.state='DISABLED';this.record(id,'DISABLED');return this.status(id);}
 async execute(id,input={}){const agent=this.require(id);if(agent.state!=='RUNNING')throw Error('Agent must be started before execution');if(agent.runs>=agent.definition.budget.max_runs_per_day)throw Error('Agent execution budget exhausted');const handler=this.handlers[id];if(typeof handler!=='function')throw Error('No isolated handler for agent');const execution_id=crypto.randomUUID(),started=this.now();this.record(id,'EXECUTION_STARTED',{execution_id});let timer;
  try{const output=await Promise.race([Promise.resolve(handler(copy(input),copy(agent.definition))),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Agent timeout')),agent.definition.budget.timeout_ms);})]);agent.runs++;this.record(id,'EXECUTION_COMPLETED',{execution_id,duration_ms:this.now()-started,model_calls:Number(output?.model_calls)||0,external_actions:false});return {execution_id,output:copy(output||{}),external_actions:false};}
  catch(error){agent.state='FAILED';agent.last_error=String(error.message).slice(0,240);this.record(id,'EXECUTION_FAILED',{execution_id,error:agent.last_error});throw error;}finally{clearTimeout(timer);}
 }
 require(id){const agent=this.agents.get(id);if(!agent)throw Error('Unknown agent');return agent;}
 record(agent_id,event,details={}){this.audit.push({event_id:crypto.randomUUID(),agent_id,event,at:new Date(this.now()).toISOString(),...details});this.audit=this.audit.slice(-500);}
 status(id){const agent=this.require(id);return copy({id,state:agent.state,runs:agent.runs,last_error:agent.last_error,definition:agent.definition});}
 snapshot(){return copy({agents:[...this.agents.keys()].map(id=>this.status(id)),audit:this.audit.slice(-100)});}
}
const referenceAgents=[
 {interface_version:'lara.agent.runtime/1.0',id:'website.quality',version:'1.0',capabilities:['availability_check','link_check','quality_report'],permissions:['website:read'],knowledge_scope:['public_site'],budget:{max_runs_per_day:4,timeout_ms:30_000,model_calls:0}},
 {interface_version:'lara.agent.runtime/1.0',id:'knowledge.navigation',version:'1.0',capabilities:['retrieve','explain_with_sources'],permissions:['knowledge:read'],knowledge_scope:['approved_oof_registry'],budget:{max_runs_per_day:20,timeout_ms:15_000,model_calls:0}},
 {interface_version:'lara.agent.runtime/1.0',id:'research.assistance',version:'1.0',capabilities:['organize_questions','identify_evidence_gaps','record_hypotheses'],permissions:['research:organize'],knowledge_scope:['user_supplied_noncanonical'],budget:{max_runs_per_day:10,timeout_ms:15_000,model_calls:0}},
];
module.exports={AgentRuntime,ALLOWED_PERMISSIONS,STATES,referenceAgents,validateDefinition};
