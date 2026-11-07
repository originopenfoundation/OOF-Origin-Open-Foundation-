'use strict';
// Model availability never grants canonical readiness or new permissions.
function protectedIntent(question){return /(?:hidden.*instructions|skryt.*(?:pokyn|instruk)|bypass|override.*(?:identity|authorization)|can you.*(?:approve|registry|enquiry|legally|remember)|mozes.*(?:schval|register|pamat)|kannst du.*(?:genehmig|register)|invent.*(?:official|standard)|ignore.*canonical)/iu.test(question.normalize('NFD').replace(/[\u0300-\u036f]/g,''));}
function smallTalk(question){return /^(?:hello\b|hi\b|hey\b|ahoj\b|hallo\b|who are you|kto si|wer bist du|tell me (?:something interesting|a.*joke)|can we talk about something other than OOF)/iu.test(question);}
function communicationScope(passages){
 if(!passages.length)return 'conversation';
 if(passages.some(p=>!['CANONICAL_AUTHORITATIVE','SUPPORTING_CITABLE'].includes(p.authority_state)
  ||p.communication_state&&!['CANONICAL_VERIFIED','SUPPORTING_NON_CANONICAL'].includes(p.communication_state)))return 'restricted_or_unresolved';
 return passages.some(p=>p.authority_state==='CANONICAL_AUTHORITATIVE')?'canonical':'supporting';
}
function generationPolicy({configured,publicReportOnly,identity,canonicalLinkRequest,question,passages,approvedPublicScopes=[]}){
 const scope=communicationScope(passages);
 const publicPermitted=['conversation','supporting'].includes(scope)&&approvedPublicScopes.includes(scope);
 if(publicReportOnly&&!publicPermitted)return {allowed:false,reason:'report_only',communication_scope:scope,approval_required:true};
 if(!configured)return {allowed:false,reason:'not_configured'};
 if(identity&&identity.status!=='FOUND')return {allowed:false,reason:'identity_unresolved'};
 if(protectedIntent(question))return {allowed:false,reason:'protected_boundary'};
 if(scope==='restricted_or_unresolved')return {allowed:false,reason:'source_boundary'};
 if(canonicalLinkRequest&&passages.length)return {allowed:false,reason:'exact_link'};
 if(passages.length)return {allowed:true,scope:scope==='supporting'?'supporting':'grounded',communication_scope:scope};
 if(smallTalk(question))return {allowed:true,scope:'conversation',communication_scope:scope};
 if(!/(?:\bOOF\b|\bLaRA\b|standard|architecture|module|govern|authorit|methodolog|štandard|architekt|modul|metodik|autorita|riaden)/iu.test(question))return {allowed:true,scope:'conversation',communication_scope:scope};
 return {allowed:false,reason:'missing_evidence'};
}

module.exports={generationPolicy,protectedIntent,smallTalk,communicationScope};
