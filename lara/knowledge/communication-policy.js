'use strict';
// Presentation classification only. It never grants access, identity or generation permission.
function communicationState(source){
 const authority=source.authority_state||source.authorityState;
 if(source.visibility&&source.visibility!=='public'||['QUARANTINED','RESTRICTED'].includes(authority))return 'QUARANTINED_RESTRICTED';
 if(source.authority_conflict===true)return 'AUTHORITY_CONFLICT';
 if(authority==='CANONICAL_AUTHORITATIVE')return source.object_id||source.representsObject?'CANONICAL_VERIFIED':'IDENTITY_UNRESOLVED';
 if(authority==='SUPPORTING_CITABLE')return source.object_id||source.representsObject?'SUPPORTING_NON_CANONICAL':'IDENTITY_UNRESOLVED';
 return 'AUTHORITY_REVIEW_REQUIRED';
}
module.exports={communicationState};
