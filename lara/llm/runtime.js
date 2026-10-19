'use strict';
// LaRA owns identity/personality and governing instructions; shared library owns inference.
const shared=require('../../lib/oof-llm');
const prompt=require('./prompt');
const enrich=input=>({...input,consumer_id:'LaRA',instructions:prompt(input)});
class OpenAICompatibleAdapter extends shared.OpenAICompatibleAdapter{async generateResult(input){return super.generateResult(enrich(input));}}
class OpenRouterAdapter extends OpenAICompatibleAdapter{constructor(config){super({...config,name:'openrouter'});}}
class AICommunicationGateway extends shared.AICommunicationGateway{async generateDetailed(input){return super.generateDetailed(enrich(input));}}
function createGateway(env){const base=shared.createGateway(env);return new AICommunicationGateway({primary:base.primary,fallback:base.fallback,maxConcurrent:base.maxConcurrent});}
function createProvider(env){const primary=shared.createGateway(env).primary;if(!primary)return null;return primary.name==='openrouter'?new OpenRouterAdapter(primary.config):new OpenAICompatibleAdapter(primary.config);}
module.exports={...shared,OpenAICompatibleAdapter,OpenRouterAdapter,OpenRouterProvider:OpenRouterAdapter,AICommunicationGateway,createGateway,createProvider};
