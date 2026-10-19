'use strict';
// Model availability never grants canonical readiness or new permissions.
function protectedIntent(question){return /(?:hidden.*instructions|skryt.*(?:pokyn|instruk)|bypass|override.*(?:identity|authorization)|can you.*(?:approve|registry|enquiry|legally|remember)|mozes.*(?:schval|register|pamat)|kannst du.*(?:genehmig|register)|invent.*(?:official|standard)|ignore.*canonical)/iu.test(question.normalize('NFD').replace(/[\u0300-\u036f]/g,''));}
function smallTalk(question){return /^(?:hello\b|hi\b|hey\b|ahoj\b|hallo\b|who are you|kto si|wer bist du|tell me (?:something interesting|a.*joke)|can we talk about something other than OOF)/iu.test(question);}
function generationPolicy({configured,publicReportOnly,identity,canonicalLinkRequest,question,passages}){
 if(publicReportOnly)return {allowed:false,reason:'report_only'};
 if(!configured)return {allowed:false,reason:'not_configured'};
 if(identity&&identity.status!=='FOUND')return {allowed:false,reason:'identity_unresolved'};
 if(protectedIntent(question))return {allowed:false,reason:'protected_boundary'};
 if(canonicalLinkRequest&&passages.length)return {allowed:false,reason:'exact_link'};
 if(passages.length)return {allowed:true,scope:'grounded'};
 if(smallTalk(question))return {allowed:true,scope:'conversation'};
 if(!/(?:\bOOF\b|\bLaRA\b|standard|architecture|module|govern|authorit|methodolog|štandard|architekt|modul|metodik|autorita|riaden)/iu.test(question))return {allowed:true,scope:'conversation'};
 return {allowed:false,reason:'missing_evidence'};
}
module.exports={generationPolicy,protectedIntent,smallTalk};
