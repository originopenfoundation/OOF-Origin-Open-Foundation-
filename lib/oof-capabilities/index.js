'use strict';
// Trusted in-process adapters only. No agent code loading, network, persistence,
// permission elevation or widget dependency. A timeout rejects late output; it
// is not a CPU sandbox for untrusted JavaScript.
const crypto=require('node:crypto');
const clone=x=>JSON.parse(JSON.stringify(x));
const freeze=x=>{if(x&&typeof x==='object'){Object.freeze(x);for(const v of Object.values(x))freeze(v);}return x;};
const hash=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
function createCore(definitions,{tools={},auditLimit=100}={}){
 const registered=new Map(),receipts=new WeakMap(),budgets=new WeakMap(),audit=[];
 for(const d of definitions){const spec=d.definition;if(!spec?.id||registered.has(spec.id)||!spec.version||!spec.input_contract||!spec.output_contract||!spec.purpose||!spec.knowledge_access||!Array.isArray(spec.allowed_tools)||!spec.execution_permissions||!spec.resource_limits||!spec.failure_behavior||!spec.audit_requirements||spec.lifecycle_status!=='experimental'||typeof d.execute!=='function'||typeof d.validateInput!=='function'||typeof d.validateOutput!=='function')throw Error('Invalid capability definition');registered.set(spec.id,{...d,definition:freeze(clone(spec))});}
 for(const c of registered.values()){const l=c.definition.resource_limits;for(const key of ['input_bytes','output_bytes','tool_calls','elapsed_ms'])if(!Number.isFinite(l[key])||l[key]<(key==='tool_calls'?0:1))throw Error('Invalid capability resource limits');if(l.elapsed_ms>10000||l.input_bytes>100000||l.output_bytes>300000||l.tool_calls>8)throw Error('Capability exceeds host resource ceilings');}
 function record(item){audit.push(freeze(item));while(audit.length>Math.max(1,Math.min(auditLimit,1000)))audit.shift();}
 async function execute(id,input,authority={}){
  const capability=registered.get(id);if(!capability)throw Error('Unknown capability');const spec=capability.definition,start=performance.now(),limits=spec.resource_limits;
  const permissions=new Set(authority.permissions||[]);if(!authority.session_id||!spec.execution_permissions.every(p=>permissions.has(p)))throw Error('Execution authority insufficient');
  const used=budgets.get(authority)||0;if(used>=Math.min(8,spec.resource_limits.steps||8))throw Error('Capability chain step limit');budgets.set(authority,used+1);
  const snapshot=clone(input);if(Buffer.byteLength(JSON.stringify(snapshot))>limits.input_bytes)throw Error('Input resource limit');
  if(capability.validateInput(snapshot)!==true)throw Error('Invalid capability input');
  let calls=0;const check=()=>{if(performance.now()-start>limits.elapsed_ms)throw Error('Execution time limit');if(authority.signal?.aborted)throw Error('Execution aborted');};
  const tool=async(name,args)=>{check();if(++calls>limits.tool_calls)throw Error('Tool call resource limit');if(!spec.allowed_tools.includes(name)||!permissions.has('tool:'+name)||typeof tools[name]!=='function')throw Error('Tool authority denied');return tools[name](clone(args));};
  try{check();const output=await capability.execute(freeze(snapshot),{tool,check});check();const safe=clone(output);if(Buffer.byteLength(JSON.stringify(safe))>limits.output_bytes)throw Error('Output resource limit');if(capability.validateOutput(safe)!==true)throw Error('Invalid capability output');
   const result=freeze({capability_id:id,version:spec.version,output:safe,metrics:{elapsed_ms:performance.now()-start,tool_calls:calls,model_calls:0}});receipts.set(result,{session_id:authority.session_id,digest:hash(safe)});record({capability_id:id,input_digest:hash(snapshot),output_digest:hash(safe),session_digest:hash(authority.session_id),status:'VALIDATED',elapsed_ms:result.metrics.elapsed_ms});return result;
  }catch(error){record({capability_id:id,input_digest:hash(snapshot),session_digest:hash(authority.session_id),status:'REJECTED',reason:error.message.slice(0,100)});throw error;}
 }
 async function handoff(result,target,input,authority){const receipt=receipts.get(result);if(!receipt||receipt.session_id!==authority.session_id||receipt.digest!==hash(result.output))throw Error('Unvalidated or cross-session handoff');const adapter=registered.get(target),spec=adapter?.definition;if(!spec?.handoff_from?.includes(result.capability_id))throw Error('Handoff contract denied');const mapped=adapter.mapHandoff?adapter.mapHandoff(result.output,input||{},result.capability_id):{...input,problem:result.output.result};return execute(target,{...mapped,handoff_context:{source_capability:result.capability_id,validated_output_digest:receipt.digest,session_digest:hash(authority.session_id),qualification:'Capability transport integrity; not event-verification evidence.'}},authority);}
 return Object.freeze({execute,handoff,definitions:()=>[...registered.values()].map(c=>clone(c.definition)),audit:()=>clone(audit)});
}
module.exports={createCore};
