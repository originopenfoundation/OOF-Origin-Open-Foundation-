'use strict';
const DEFINITIONS={
 oof:{tenant_id:'oof',label:'OOF',knowledge_scope:'approved_oof_registry',clinical:false},
 affordia:{tenant_id:'affordia',label:'Affordia Health pilot',knowledge_scope:'affordia_synthetic_pilot_only',clinical:true},
};
function tenant(id){const selected=DEFINITIONS[id];if(!selected)throw Error('Unknown tenant');return {...selected};}
function sessionKey(tenantId,sessionId){if(!/^[a-z0-9_-]{3,40}$/i.test(sessionId||''))throw Error('Invalid session id');return `${tenant(tenantId).tenant_id}:${sessionId}`;}
function assertScope(tenantId,resource){const selected=tenant(tenantId);if(resource?.tenant_id&&resource.tenant_id!==selected.tenant_id)throw Error('Cross-tenant resource access denied');if(selected.clinical&&resource?.kind==='medical_decision')throw Error('Clinical decision support is not enabled');return true;}
module.exports={DEFINITIONS,tenant,sessionKey,assertScope};

