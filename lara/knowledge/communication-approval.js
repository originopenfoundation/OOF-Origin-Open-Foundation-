"use strict";
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const file=path.join(__dirname,'public-communication-policy.json');
function approvedScopes(index){
 const raw=fs.readFileSync(file),policy=JSON.parse(raw);
 const candidates=(index.objects||[]).filter(o=>o.id===policy.approval_object_id);
 if(candidates.length!==1)return [];
 const o=candidates[0],approval=o.sourceAuthority?.publicCommunicationApproval;
 if(o.authorityState!=='CANONICAL_AUTHORITATIVE'||o.visibility!=='public'||!o.allowedConsumers?.includes('LaRA')
  ||!['current','active','published'].includes(o.status)||!o.sourceAuthority?.domains?.includes('publicCommunicationApproval')
  ||approval?.status!=='approved'||approval.policyDigest!==crypto.createHash('sha256').update(raw).digest('hex'))return [];
 return (approval.scopes||[]).filter(s=>policy.allowed_scopes.includes(s));
}
module.exports={approvedScopes};
