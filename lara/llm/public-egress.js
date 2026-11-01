'use strict';
// Public activation approval and visitor data consent are independent gates.
// This function grants neither canonical authority nor deployment permission.
function publicEgressPolicy({publicRequest,provider,consent}){
 if(!publicRequest)return {allowed:true};
 if(consent!==true)return {allowed:false,reason:'provider_consent_required'};
 if(provider!=='groq')return {allowed:false,reason:'public_provider_not_approved'};
 return {allowed:true,data_classification:'public'};
}
module.exports={publicEgressPolicy};
