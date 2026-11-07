'use strict';
const crypto=require('node:crypto');
const {status,SEMANTICS}=require('../oof-evidence-status');
const {copy}=require('../oof-localization');
const digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
const norm=s=>String(s||'').normalize('NFC').replace(/\s+/g,' ').trim();
const kinds=new Set(['event','source_statement','methodological','registry_field','relationship']);
const origins=new Set(['user','model','knowledge','deterministic']);
const evidenceKinds=new Set(['direct','indirect','contextual_reference','user_reported_observation','unverified_allegation','contradictory','missing','methodological_rule']);
const trustedStates=new Set(['CANONICAL_AUTHORITATIVE','SUPPORTING_CITABLE']);
const followup=text=>/what evidence|what.*unverified|how.*test|invalidate|evidence|verification|dokaz|overi|beleg|nachweis|preuve|verifi|evidenc|verific|证据|證據|検証|証拠|증거|검증|साक्ष्य|सत्यापन|доказ|провер|دليل|تحقق/iu.test(String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,''));
function provenanceValid(p){return p&&p.sourcePath&&/^[a-f0-9]{40,64}$/.test(p.repositoryCommit||'')&&/^[a-f0-9]{64}$/.test(p.contentHash||'');}
function decompose(text){const raw=String(text||'').trim().slice(0,5000);const claims=[];for(const m of raw.matchAll(/[^.!?;\n]+[.!?]?/gu)){const exact=m[0].trim();if(exact)claims.push({proposition:exact,origin:'user',kind:'event',span:{start:m.index,end:m.index+m[0].length},requested_conclusion:exact.endsWith('?')});if(claims.length===8)break;}return claims;}
function createVerifier(index,{session_id=crypto.randomUUID()}={}){
 const secret=crypto.randomBytes(32),attestations=new Map();
 const resources=[...(index.resources||[]),...(index.historical_resources||[])],byId=index.byId||new Map(index.objects.map(o=>[o.id,o]));
 const sign=r=>{const{validation_receipt,...body}=r;return crypto.createHmac('sha256',secret).update(JSON.stringify(body)).digest('hex');};
 function attest(record){
  if(!record?.proposition||!['supports','contradicts'].includes(record.relation)||!evidenceKinds.has(record.kind)||!record.source_identity||!record.criterion?.description||record.criterion.executed!==true||!record.timestamp||!Number.isFinite(Date.parse(record.timestamp)))throw Error('Host attestation requires executed criterion and provenance');
  const id='receipt:'+crypto.randomBytes(24).toString('hex');attestations.set(id,clone({...record,session_id}));return id;
 }
 function source(sourceId,at){
  const matches=resources.filter(s=>s.resource_id===sourceId);if(matches.length!==1)return{error:matches.length?'AMBIGUOUS_SOURCE_ID':'UNKNOWN_SOURCE_ID'};
  const r=matches[0],o=r.object_id?byId.get(r.object_id):null;
  if(!provenanceValid(r.provenance)||!trustedStates.has(r.authority_state))return{error:'INVALID_SOURCE_PROVENANCE_OR_AUTHORITY'};
  let url;try{url=new URL(r.canonical_url);}catch{return{error:'INVALID_SOURCE_URL'};}
  if(url.origin!=='https://originopenfoundation.org'||url.username||url.password||o&&(o.visibility!=='public'||!o.allowedConsumers?.includes('LaRA')))return{error:'INELIGIBLE_SOURCE'};
  const historical=/superseded|withdrawn/i.test(o?.status||r.lifecycle_status||'');
  const period=r.validity;
  if(at){if(!Number.isFinite(Date.parse(at)))return{error:'INVALID_TIME_SCOPE'};if(!period?.from||!period?.until||r.historical_authority!==true||!Number.isFinite(Date.parse(period.from))||!Number.isFinite(Date.parse(period.until)))return{error:'HISTORICAL_AUTHORITY_NOT_ESTABLISHED'};if(Date.parse(at)<Date.parse(period.from)||Date.parse(at)>=Date.parse(period.until))return{error:'VERSION_TIME_MISMATCH'};}
  else if(historical)return{error:'SUPERSEDED_NOT_CURRENT'};
  if(o?.sourceAuthority?.validationResult==='CONFLICT')return{error:'CONFLICTING_SOURCE_AUTHORITY'};
  return{r,o,historical:Boolean(at)};
 }
 function assess(input={}){
  const started=performance.now();if(typeof input.text!=='string'||!input.text.trim()||input.text.length>5000)throw Error('Evidence text required');
  if(input.evidence&&!Array.isArray(input.evidence)||input.claims&&!Array.isArray(input.claims))throw Error('Invalid evidence input schema');
  if((input.evidence?.length||0)>24||(input.claims?.length||0)>8)throw Error('Evidence resource limit');
  const previous=input.previous;if(previous)validate(previous);
  const changed=require('../oof-discovery/interpretation').interpret(input.text).changed_problem;
  let selected=input.claims?.length?input.claims:previous&&!changed&&(input.evidence?.length||followup(input.text))?previous.claims.map(c=>({claim_id:c.claim_id,proposition:c.proposition,origin:c.origin,kind:c.kind,speech_act:c.speech_act,architecture_ids:c.architecture_ids,governed_space:c.governed_space,field:c.field,expected:c.expected,object_id:c.object_id,source_object_id:c.source_object_id,target_object_id:c.target_object_id,relationship_type:c.relationship_type,historical_at:c.historical_at})):decompose(input.text).filter((c,i,all)=>!c.requested_conclusion||all.every(x=>x.requested_conclusion));
  const claims=selected.slice(0,8).map((c,i)=>{if(!c.proposition||String(c.proposition).length>2000||c.kind&&!kinds.has(c.kind))throw Error('Invalid claim contract');const architecture_ids=[...new Set(c.architecture_ids||input.cross?.architectures?.map(a=>a.object_id)||[])];for(const id of architecture_ids)if(byId.get(id)?.artifactType!=='Architecture')throw Error('Fabricated architecture identifier');return{claim_id:c.claim_id||'claim:'+digest([c.proposition,c.kind||'event']).slice(0,20),proposition:String(c.proposition),origin:origins.has(c.origin)?c.origin:'user',kind:c.kind||'event',speech_act:c.speech_act==='request'||c.requested_conclusion?'request':'assertion',governed_space:c.governed_space||null,architecture_ids,span:c.span||null,field:c.field||null,expected:c.expected??null,object_id:c.object_id||null,source_object_id:c.source_object_id||null,target_object_id:c.target_object_id||null,relationship_type:c.relationship_type||null,historical_at:c.historical_at||input.historical_at||null,supporting_evidence:[],contradictory_evidence:[],contextual_evidence:[],missing_evidence:[],assumptions:[],authority_limitations:[],status:'NOT_ASSESSED'};});
  if(new Set(claims.map(c=>c.claim_id)).size!==claims.length)throw Error('Duplicate claim identity');
  const evidence=[],rejected=[],conflicts=[],refs=new Map();
  function add(record){if(evidence.length>=40)throw Error('Evidence output resource limit');const id='evidence:'+digest(record).slice(0,24);if(!evidence.some(e=>e.evidence_id===id))evidence.push({evidence_id:id,...record});return id;}
  const inputs=[...(previous&&!changed?previous.evidence.filter(e=>e.input_record).map(e=>e.input_record):[]),...(input.evidence||[])].slice(-24);
  for(const e of inputs){const claim=claims.find(c=>c.claim_id===e.claim_id);if(!claim){rejected.push({reference:String(e.source_id||e.receipt_id||'user-report').slice(0,180),reason:'UNKNOWN_CLAIM_ID'});continue;}
   const receipt=e.receipt_id&&attestations.get(e.receipt_id);
   if(e.receipt_id){if(!receipt||receipt.session_id!==session_id||norm(receipt.proposition)!==norm(claim.proposition)){rejected.push({reference:e.receipt_id,reason:'UNTRUSTED_OR_CROSS_SESSION_ATTESTATION'});continue;}const record={claim_id:claim.claim_id,classification:receipt.relation==='contradicts'?'contradictory':receipt.kind,scope_kind:receipt.kind,relation:receipt.relation,source_identity:receipt.source_identity,source_type:'authorized_verifier_receipt',digest:digest(receipt),timestamp:receipt.timestamp,authority_status:'HOST_ATTESTED_FOR_STATED_CRITERION',excerpt:receipt.excerpt||receipt.proposition,verification_state:'ATTESTED',criterion:receipt.criterion,receipt_id:e.receipt_id,applicable:!claim.historical_at||receipt.historical_at===claim.historical_at,input_record:clone(e)};add(record);continue;}
   if(!e.source_id){const text=String(e.text||'').slice(0,2000);if(!text){rejected.push({reference:'user-report',reason:'EMPTY_USER_EVIDENCE'});continue;}add({claim_id:claim.claim_id,classification:e.relation==='contradicts'?'unverified_allegation':'user_reported_observation',relation:e.relation==='contradicts'?'contradicts':'supports',source_identity:'session:'+digest([session_id,text]),source_type:'user_report',digest:digest(text),timestamp:null,authority_status:'UNVERIFIED_USER_REPORT',excerpt:text,verification_state:'USER_REPORTED',applicable:true,input_record:clone(e)});continue;}
   const found=source(e.source_id,claim.historical_at);if(found.error){rejected.push({reference:e.source_id,reason:found.error,claim_id:claim.claim_id});if(found.error==='VERSION_TIME_MISMATCH')conflicts.push({claim_id:claim.claim_id,kind:'VERSION_MISMATCH',source_ids:[e.source_id],resolution:'Use the authoritative source applicable to the requested period, not simply the newest.'});continue;}
   const{r,o}=found,excerpt=String(e.excerpt||'').trim();const body=(r.chunks||[]).map(c=>c.text).join('\n');
   if(!excerpt||excerpt.length>2000||!norm(body).includes(norm(excerpt))){rejected.push({reference:e.source_id,reason:'EXCERPT_NOT_IN_SOURCE',claim_id:claim.claim_id});continue;}
   const sentences=body.split(/(?<=[.!?])\s+|\n+/u).map(norm);
   const isRule=['ParentStandard','CoreModule','Architecture'].includes(o?.artifactType),literal=norm(claim.proposition)===norm(excerpt)&&sentences.includes(norm(excerpt)),eligible=claim.kind!=='event'&&literal;
   const record={claim_id:claim.claim_id,classification:isRule?'methodological_rule':eligible?'direct':'contextual_reference',relation:eligible?'supports':'context',source_identity:r.resource_id,source_type:'knowledge_representation',digest:r.provenance.contentHash,timestamp:r.provenance.generatedTimestamp||null,authority_status:r.authority_state,authority_domain:r.authority_domain||[],lifecycle_status:o?.status||r.lifecycle_status,excerpt,verification_state:'HASH_VERIFIED_SOURCE_AND_MATCHED_EXCERPT',applicable:true,provenance:r.provenance,historical_scope:claim.historical_at,input_record:clone(e)};add(record);
   refs.set(r.resource_id,{resource_id:r.resource_id,object_id:r.object_id,url:r.canonical_url,title:r.title,authority_state:r.authority_state,lifecycle_status:o?.status||r.lifecycle_status,provenance:r.provenance,historical_at:claim.historical_at});
   if(!eligible)rejected.push({reference:r.resource_id,claim_id:claim.claim_id,reason:claim.kind==='event'?'METHODOLOGY_IS_NOT_EVENT_PROOF':'SOURCE_DOES_NOT_ESTABLISH_EXACT_CLAIM'});
  }
  for(const claim of claims){
   if(claim.kind==='registry_field'){
    const o=byId.get(claim.object_id),allowed=['status','authorityState','canonicalName','version'];
    if(!o||!allowed.includes(claim.field)||!provenanceValid(o.provenance))throw Error('Invalid registry-field claim');
    const r=(index.resources||[]).find(r=>r.object_id===o.id),found=r&&source(r.resource_id,claim.historical_at);if(found&&!found.error){const relation=o[claim.field]===claim.expected?'supports':'contradicts';add({claim_id:claim.claim_id,classification:relation==='supports'?'direct':'contradictory',relation,source_identity:o.id,source_type:'registry_field',digest:o.provenance.contentHash,timestamp:o.provenance.generatedTimestamp||null,authority_status:o.authorityState,excerpt:JSON.stringify({field:claim.field,value:o[claim.field]}),verification_state:'REGISTRY_FIELD_MATCH',applicable:true,provenance:o.provenance});}
   }
   if(claim.kind==='relationship'){
    if(!byId.has(claim.source_object_id)||!byId.has(claim.target_object_id))throw Error('Fabricated relationship endpoint');
    const edges=(index.relationships||[]).filter(e=>e.sourceId===claim.source_object_id&&e.targetId===claim.target_object_id&&e.relationshipType===claim.relationship_type&&['AUTHORITATIVE','VALIDATED_AUTHORITATIVE'].includes(e.authorityState)&&e.status==='active'&&provenanceValid(e.provenance));
    for(const edge of edges){const endpoints=[edge.sourceId,edge.targetId].map(id=>byId.get(id));if(endpoints.some(o=>o.authorityState!=='CANONICAL_AUTHORITATIVE'||/draft|pending|in.progress|superseded|withdrawn/i.test(o.status||'')))continue;add({claim_id:claim.claim_id,classification:'methodological_rule',relation:'supports',source_identity:edge.id,source_type:'authoritative_relationship',digest:edge.provenance.contentHash,timestamp:edge.provenance.generatedTimestamp||null,authority_status:edge.authorityState,excerpt:JSON.stringify({source:edge.sourceId,target:edge.targetId,type:edge.relationshipType}),verification_state:'REGISTRY_RELATIONSHIP_MATCH',applicable:true,provenance:edge.provenance});}
   }
   const applicable=evidence.filter(e=>e.claim_id===claim.claim_id&&e.applicable),trusted=e=>['ATTESTED','REGISTRY_FIELD_MATCH','REGISTRY_RELATIONSHIP_MATCH','HASH_VERIFIED_SOURCE_AND_MATCHED_EXCERPT'].includes(e.verification_state)&&!(claim.kind==='event'&&['methodological_rule','contextual_reference','missing'].includes(e.scope_kind||e.classification)),support=applicable.filter(e=>e.relation==='supports'&&trusted(e)),contra=applicable.filter(e=>e.relation==='contradicts'&&trusted(e));
   claim.supporting_evidence=support.map(e=>e.evidence_id);claim.contradictory_evidence=contra.map(e=>e.evidence_id);claim.contextual_evidence=applicable.filter(e=>!support.includes(e)&&!contra.includes(e)).map(e=>e.evidence_id);
   const conflict=support.length>0&&contra.length>0;if(conflict)conflicts.push({claim_id:claim.claim_id,kind:'FACTUAL_CONTRADICTION',source_ids:[...support,...contra].map(e=>e.source_identity),resolution:'Retain both accounts; obtain an authorized scoped verification.'});
   const verified=support.some(e=>e.verification_state==='ATTESTED'&&e.criterion?.executed===true&&e.classification==='direct');
   claim.status=status({assessed:true,direct:support.some(e=>e.classification!=='indirect'),indirect:support.some(e=>e.classification==='indirect'),contradiction:contra.length>0,conflict,criterionExecuted:verified,authorizedReceipt:verified});
   if(claim.status!=='VERIFIED')claim.missing_evidence.push(claim.kind==='event'?'Independent scoped event records and an authorized executed criterion.':'Independent verification or complete applicable source support.');
   if(claim.kind==='event')claim.authority_limitations.push('Methodological rules are not evidence that this real-world event occurred.');
   claim.authority_limitations.push('No external action, canonical approval or source mutation is authorized.');
   if(claim.status==='PROVISIONAL')claim.assumptions.push('Indirect evidence is applicable to the exact actor, action, period and scope.');
  }
  const structuredRefs=evidence.filter(e=>e.source_type==='registry_field'||e.source_type==='authoritative_relationship').flatMap(e=>index.resources.filter(r=>r.object_id===e.source_identity||r.provenance.sourcePath===e.provenance?.sourcePath).slice(0,1).map(r=>r.resource_id));
  const contextIds=[...new Set([...structuredRefs,...(input.cross?.knowledge_references||[]).map(r=>r.resource_id),...(input.navigation_reference_ids||[])])].slice(0,12);
  for(const id of contextIds){const found=source(id,null);if(found.error)continue;const{r,o}=found;refs.set(r.resource_id,{resource_id:r.resource_id,object_id:r.object_id,url:r.canonical_url,title:r.title,authority_state:r.authority_state,lifecycle_status:o?.status||r.lifecycle_status,provenance:r.provenance,historical_at:null,qualification:'Contextual methodology, not event proof.'});}
  const plans=claims.map(c=>({plan_id:'plan:'+c.claim_id,claim_id:c.claim_id,objective:'Test the exact proposition: '+c.proposition,required_evidence:c.kind==='event'?['Authenticated actor/action/timestamp record','Effective permission and operational scope','Independent corroboration or contradictory outcome']:c.kind==='relationship'?['Exact active authoritative relationship record','Eligible endpoint identities, lifecycle and provenance']:['Exact source excerpt or structured field','Source digest, authority domain, lifecycle and applicable period'],evidence_acquisition:{method:'REQUEST_FROM_AUTHORIZED_RECORD_OWNER',source:c.kind==='event'?'System audit-log and permission-record owner':'Existing OOF registry and authorized source owner'},procedure:['Identify the precise actor/object, action/proposition, period and scope.','Check identity, digest, authority and temporal applicability of each record.','Compare supporting and contradictory records against the proposition.','Have an authorized verifier execute and record the stated criterion.'],acceptance_criteria:'Applicable independently attested support, executed criterion and no unresolved applicable contradiction.',failure_criteria:'An applicable attested contradiction, a mismatched scope, fabricated provenance, or insufficient required evidence.',contradictory_outcomes:c.contradictory_evidence,residual_uncertainty:c.missing_evidence,required_authority:'Authorized source/record owner and verifier; human approval before acquiring private records or external testing.',execution_status:'PROPOSED_NOT_EXECUTED',external_actions_authorized:false}));
  const result={schema_version:'1.0',session_reference:digest(session_id),input_digest:digest({text:input.text,claims:input.claims||null,evidence:input.evidence||[],previous:previous?.validation_receipt||null}),claims,evidence,conflicts,rejected_evidence:rejected,verification_plans:plans,knowledge_references:[...refs.values()],conclusion_limits:['Absence of evidence does not establish evidence of absence.','A citation is not proof that the source supports the proposition.','Proposed tests have not been executed.'],handoff_audit:input.handoff_context||null,metrics:{deterministic_ms:performance.now()-started,model_calls:0},authority_mutation:false,external_actions:false,registry_fingerprint:index.registry_fingerprint||null};
  result.validation_receipt=sign(result);validate(result);return result;
 }
 function validate(r){
  if(r?.schema_version!=='1.0'||r.session_reference!==digest(session_id)||r.registry_fingerprint!==(index.registry_fingerprint||null)||r.authority_mutation!==false||r.external_actions!==false||!r.validation_receipt||r.validation_receipt!==sign(r))throw Error('Invalid evidence output or cross-session receipt');
  for(const key of ['claims','evidence','conflicts','rejected_evidence','verification_plans','knowledge_references','conclusion_limits'])if(!Array.isArray(r[key]))throw Error('Missing evidence collection');
  if(r.claims.length>8||r.evidence.length>40||new Set(r.claims.map(c=>c.claim_id)).size!==r.claims.length)throw Error('Invalid evidence resource bound');
  for(const c of r.claims){if(!SEMANTICS[c.status]||!c.proposition||!origins.has(c.origin))throw Error('Invalid evidence claim');for(const id of [...c.supporting_evidence,...c.contradictory_evidence,...c.contextual_evidence])if(!r.evidence.some(e=>e.evidence_id===id&&e.claim_id===c.claim_id))throw Error('Fabricated evidence identity');}
  for(const e of r.evidence){if(!evidenceKinds.has(e.classification)||!e.source_identity||!e.source_type||!e.digest||!e.excerpt||!e.verification_state)throw Error('Invalid evidence provenance');if(e.source_type==='knowledge_representation'){const found=source(e.source_identity,e.historical_scope);if(found.error||found.r.provenance.contentHash!==e.digest||!norm(found.r.chunks.map(c=>c.text).join('\n')).includes(norm(e.excerpt)))throw Error('Invalid evidence source');}}
  for(const p of r.verification_plans)if(p.execution_status!=='PROPOSED_NOT_EXECUTED'||p.external_actions_authorized!==false||!r.claims.some(c=>c.claim_id===p.claim_id)||!p.required_evidence?.length||!p.required_authority)throw Error('Invalid verification plan');return r;
 }
 return Object.freeze({assess,validate,attest});
}
function explain(result,language='en',order=null){
 const t=copy(language);
 return t.evidence+'\n\n'+(order?order.map(id=>result.claims.find(c=>c.claim_id===id)):result.claims).map(c=>[
  `${c.speech_act==='request'?t.objective:t.claim}: ${c.proposition}`,t[c.status],
  `${t.supports}: ${c.supporting_evidence.length}`,`${t.contradicts}: ${c.contradictory_evidence.length}`,
  `${t.objective} ${c.proposition}`,
  `${t.missing}: ${c.status==='VERIFIED'?'-':t.gap}`,
  `${t.proposed}: ${c.kind==='event'?t.eventRecords:t.sourceRecords}`,
  t.procedure,`${t.acceptance}: ${t.acceptanceText}`,`${t.failure}: ${t.failureText}`,
  t.authorityText,`${t.residual}: ${c.status==='VERIFIED'?'-':t.residualText}`,t.notEventProof
 ].join('\n')).join('\n\n')+'\n\n'+(result.conflicts.length?t.conflict+'\n':'')+(result.rejected_evidence.length?t.rejectedText+'\n':'')+result.knowledge_references.map(r=>`${t.source}: ${r.title}\n${r.url}`).join('\n')+'\n'+t.followup;
}
module.exports={createVerifier,decompose,followup,explain,SEMANTICS};
