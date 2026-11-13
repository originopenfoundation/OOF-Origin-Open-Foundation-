'use strict';
const crypto=require('node:crypto');
const copy=value=>JSON.parse(JSON.stringify(value));
const STATES=new Set(['OPEN','BLOCKED','RESOLVED','NOT_APPLICABLE']);
class BlockerRegistry{
 constructor(){this.items=[];}
 add(input){const item={blocker_id:input.blocker_id||`LARA-V271-${crypto.randomUUID()}`,capability:String(input.capability||''),category:String(input.category||''),error:String(input.error||''),reproduction:Array.isArray(input.reproduction)?input.reproduction:[],root_cause:String(input.root_cause||''),attempts:Array.isArray(input.attempts)?input.attempts:[],required_action:String(input.required_action||''),required_access:String(input.required_access||''),verification:String(input.verification||''),stops_dependent_work:Boolean(input.stops_dependent_work),state:input.state||'OPEN'};if(!item.capability||!item.category||!item.error||!STATES.has(item.state))throw Error('Invalid blocker record');this.items.push(item);return copy(item);}
 snapshot(){return copy(this.items);}
}
function milestone(input={}){const requiredA=['authorized_test_conversation','multi_turn_context','knowledge_retrieval','browser','voice_supported_environment','first_run_measured','security_critical_clear','owner_instructions'];const requiredB=[...requiredA,'canonical_public_approval','approved_scopes','policy_digest','multilingual_suite','public_consent','controlled_release','public_conversation'];const fields=input.public_generation?requiredB:requiredA;const missing=fields.filter(key=>input[key]!==true);return {milestone:input.public_generation?'LARA_V271_PUBLIC_GENERATION_READY':'LARA_V271_OWNER_TESTING_READY',achieved:missing.length===0,missing};}
module.exports={BlockerRegistry,milestone,STATES};

