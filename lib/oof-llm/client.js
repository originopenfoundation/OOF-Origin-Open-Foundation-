'use strict';
const {createGateway,ProviderError}=require('./runtime');
function createClient({consumer_id,env={},instructions,validateOutput,registry}={}){
 if(!/^[A-Za-z0-9_-]{1,64}$/.test(consumer_id||'')||typeof instructions!=='string'||!instructions.trim())throw new ProviderError('invalid_configuration','Consumer identity and governing instructions required');
 // Each client owns adapters, cooldowns and metrics; no conversations or credentials are global.
 const gateway=createGateway({...env,LLM_APP_NAME:consumer_id});
 return Object.freeze({
  capabilities:()=>gateway.getCapabilities(),diagnostics:()=>gateway.snapshot(),
  async generate(input){
   if(registry&&input.requirements){const selected=registry.select({...input.requirements,consumer_id});if(!selected)throw new ProviderError('model_unavailable','No permitted model satisfies consumer requirements');if(selected.model!==env.LLM_MODEL||selected.provider!==env.LLM_PROVIDER)throw new ProviderError('model_unavailable','Selected model is not the explicitly configured route');}
   const result=await gateway.generateDetailed({...input,consumer_id,instructions});
   if(!result)throw new ProviderError('not_configured','No inference model configured');
   if(validateOutput){const check=await validateOutput(result.answer,input);if(!check?.ok)throw new ProviderError('output_rejected','Consumer output validation rejected response');}
   return {...result,consumer_id,cost:null,cost_verified:false};
  }
 });
}
module.exports={createClient};
