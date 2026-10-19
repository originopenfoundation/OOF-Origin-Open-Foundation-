'use strict';
const {ProviderError}=require('./runtime');
// Metadata contains no credentials and confers neither source authority nor access.
class ModelRegistry{
 constructor(records=[]){this.models=new Map();for(const item of records)this.register(item);}
 register(item){
  if(!item?.id||!item.model||!['openrouter','openai-compatible'].includes(item.provider)||!Number.isInteger(item.context_window)||item.context_window<1024||!['free','paid','unknown'].includes(item.cost_class))throw new ProviderError('invalid_configuration','Invalid model metadata');
  if(this.models.has(item.id))throw new ProviderError('invalid_configuration','Duplicate model metadata ID');
  const safe={id:String(item.id),model:String(item.model),provider:item.provider,context_window:item.context_window,cost_class:item.cost_class,privacy:item.privacy||'unknown',available:item.available===true,license:item.license||'unverified',consumers:[...(item.consumers||[])],advertised_languages:[...(item.advertised_languages||[])],verified_languages:[...(item.verified_languages||[])],verification_evidence:item.verification_evidence||null,latency_ms:Number.isFinite(item.latency_ms)?item.latency_ms:null,reliability:Number.isFinite(item.reliability)?item.reliability:null};
  if(safe.verified_languages.length&&!safe.verification_evidence)throw new ProviderError('invalid_configuration','Verified capabilities require evidence');
  this.models.set(safe.id,JSON.stringify(safe));return this;
 }
 list(){return [...this.models.values()].map(JSON.parse);}
 select({consumer_id,language,min_context=1024,allow_paid=false,require_verified=false,privacy}={}){
  if(!consumer_id)throw new ProviderError('invalid_configuration','Consumer identity required');
  const candidates=this.list().filter(m=>m.available&&m.consumers.includes(consumer_id)&&m.context_window>=min_context&&(allow_paid||m.cost_class==='free')&&(!privacy||m.privacy===privacy)&&(!language||(require_verified?m.verified_languages:m.advertised_languages).includes(language)));
  candidates.sort((a,b)=>(b.reliability??0)-(a.reliability??0)||(a.latency_ms??Infinity)-(b.latency_ms??Infinity)||a.id.localeCompare(b.id));
  return candidates[0]||null;
 }
}
module.exports={ModelRegistry};
