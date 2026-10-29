'use strict';
// LaRA owns identity/personality and governing instructions; shared library owns inference.
const shared=require('../../lib/oof-llm');
const prompt=require('./prompt');
const enrich=input=>({...input,consumer_id:'LaRA',instructions:prompt(input)});
class OpenAICompatibleAdapter extends shared.OpenAICompatibleAdapter{async generateResult(input){return super.generateResult(enrich(input));}}
class OpenRouterAdapter extends OpenAICompatibleAdapter{constructor(config){super({...config,name:'openrouter'});}}
class AICommunicationGateway extends shared.AICommunicationGateway{async generateDetailed(input){return super.generateDetailed(enrich(input));}}
function createGateway(env){const base=shared.createGateway(env);const gateway=new AICommunicationGateway({primary:base.primary,fallback:base.fallback,maxConcurrent:base.maxConcurrent});
 const generate=gateway.generateDetailed.bind(gateway);
 gateway.generateDetailed=input=>generate({...input,data_classification:env.LLM_EXTERNAL_DATA_APPROVED==='true'?'public':input.data_classification});
 return gateway;}
function createProvider(env){const primary=shared.createGateway(env).primary;if(!primary)return null;if(primary.name==='groq'){const generate=primary.generateResult.bind(primary);primary.generateResult=input=>generate(enrich({...input,data_classification:env.LLM_EXTERNAL_DATA_APPROVED==='true'?'public':input.data_classification}));return primary;}
 return primary.name==='openrouter'?new OpenRouterAdapter(primary.config):new OpenAICompatibleAdapter(primary.config);}
module.exports={...shared,OpenAICompatibleAdapter,OpenRouterAdapter,OpenRouterProvider:OpenRouterAdapter,AICommunicationGateway,createGateway,createProvider};
