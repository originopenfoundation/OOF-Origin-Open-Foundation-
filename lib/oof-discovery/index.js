'use strict';
// Evidence reasoning core. No transport, persistence, UI or model dependency.
const crypto=require('node:crypto');
const clean=s=>String(s||'').trim().slice(0,5000);
const norm=s=>clean(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const statuses=new Set(['VALIDATED','PROVISIONAL','UNRESOLVED','CONTRADICTED']);
const kinds=new Set(['verified','user_claim','reference','inference']);
function wantsDiscovery(text,mode='auto',previous){
 if(mode==='discovery')return true;
 if(mode!=='auto')return false;
 if(/^(?:what is|define|explain|co je|čo je|vysvetli)\b/iu.test(text))return false;
 return /new problem|different problem|novy problem|problem discovery|root cause|diagnos|analy[sz]e.*problem|pricin|nefunguje|unexpected|unexplained|incorrect|unauthorized|without.*(?:cause|permission)|(?:software|deployment|our|my|system).*failure|interruption|consumption.*increase|qualification.*uncertain|unresolved.*value/i.test(norm(text))||Boolean(previous&&/^(?:expected:|observed:|boundary:|goal:|also|but|however|logs?|evidence|actually|and|the test|meranie|ale|dalsi|zistili)/i.test(norm(text)));
}
const rules=[
 {id:'authorization',terms:/payment|unauthor|permission|qualification|workplace|platb|opravnen/,query:'payment authorization authority',hypotheses:['An authorization boundary may be missing or incorrectly enforced.','The action may be permitted under a policy not yet supplied.'],test:'Compare the effective permission and qualification records with the exact action, actor and timestamp.'},
 {id:'software',terms:/software|deploy|slga|server|chatbot|incorrect.*governance|softver/,query:'software lifecycle SLGA',hypotheses:['A configuration or software change may explain the behavior.','The failure may originate in an independent dependency or source-data mismatch.'],test:'Compare a redacted failure trace and configuration diff with a known working version; use an isolated reproduction.'},
 {id:'energy',terms:/energy|power|electric|interruption|energi/,query:'energy infrastructure',hypotheses:['An upstream supply event may explain the interruption.','A local protection or measurement fault may explain the interruption.'],test:'Compare independent timestamped supply and protection records without changing live infrastructure.'},
 {id:'water',terms:/water|consumption|voda|spotreb/,query:'water resource',hypotheses:['A real demand change or loss may explain the increase.','A meter or reporting-period mismatch may explain the apparent increase.'],test:'Compare meter readings over equivalent periods against an independent measurement and operational activity.'},
 {id:'value',terms:/token|asset|real.world|value claim/,query:'asset tokenization value lifecycle',hypotheses:['The asserted asset-to-value relationship may lack sufficient evidence.','The valuation may depend on an unprovided methodology or boundary.'],test:'Inspect the asset identity, valuation date, methodology and independently verifiable supporting records.'},
 {id:'behavior',terms:/autonom|unexpected|agent|system/,query:'autonomous system behavioral governance',hypotheses:['The operational boundary or control may differ from the expected behavior.','The observed action may reflect an input, dependency or interpretation not yet examined.'],test:'Compare the action trace, expected policy, inputs and authorized operational boundary.'}
];
function validate(result){
 if(result?.schema_version!=='1.0'||!statuses.has(result.problem?.status)||!result.problem.stated||!result.problem.candidate_root)throw Error('Invalid discovery state');
 const fields=['observations','assumptions','hypotheses','supporting_evidence','contradictory_evidence','evidence_gaps','verification_actions','knowledge_references','provenance'];
 for(const key of fields)if(!Array.isArray(result[key]))throw Error('Missing discovery collection: '+key);
 const ids=new Set();for(const p of result.provenance){if(!p.id||!p.source||!kinds.has(p.kind)||ids.has(p.id))throw Error('Invalid provenance');ids.add(p.id);}
 const findings=[...result.observations,...result.assumptions,...result.hypotheses,...result.supporting_evidence,...result.contradictory_evidence,...result.evidence_gaps,...result.verification_actions];
 const findingIds=new Set();for(const f of findings){if(!f.id||findingIds.has(f.id)||!f.text||!f.provenance_ids?.length||f.provenance_ids.some(id=>!ids.has(id)))throw Error('Untraceable finding');findingIds.add(f.id);}
 for(const a of result.assumptions)if(!['SUPPORTED','CONTRADICTED','UNVERIFIED','NOT_ASSESSABLE'].includes(a.status)||!Array.isArray(a.evidence_ids)||a.evidence_ids.some(id=>!findingIds.has(id)))throw Error('Invalid assumption state');
 for(const h of result.hypotheses)if(!h.verification_test||!h.confidence||!['supporting_ids','contradictory_ids','missing_ids'].every(k=>Array.isArray(h[k])&&h[k].every(id=>findingIds.has(id))))throw Error('Invalid hypothesis');
 if(result.problem.status==='VALIDATED'&&(!result.validation?.criteria||!result.validation?.evidence_ids?.length||result.validation.evidence_ids.some(id=>!result.supporting_evidence.some(e=>e.id===id&&e.kind==='verified'))))throw Error('Validation needs verified evidence and criteria');
 for(const r of result.knowledge_references){let url;try{url=new URL(r.url);}catch{throw Error('Invalid reference URL');}if(url.origin!=='https://originopenfoundation.org'||!r.provenance?.contentHash||!['CANONICAL_AUTHORITATIVE','SUPPORTING_CITABLE'].includes(r.authority_state)||(['draft','in-progress','pending','published-pending'].includes(r.lifecycle_status)&&r.authority_state!=='SUPPORTING_CITABLE'))throw Error('Invalid Knowledge reference');}
 return result;
}
function discover({text,previous=null,evidence=[],verifyEvidence=()=>false,criterion=null}={}){
 const started=performance.now(),question=clean(text);if(!question)throw Error('Problem text required');
 // A changed problem must not silently inherit the previous case evidence.
 const changed=/^(?:new problem|different problem|change (?:the )?problem|novy problem|iny problem)/i.test(norm(question));
 const continuing=previous&&!changed;const turns=continuing?[...previous.turns,question].slice(-6):[question];
 const stated=turns[0],context=turns.join('\n'),domain=rules.find(r=>r.terms.test(norm(context)));
 const provenance=turns.map((t,i)=>({id:'u'+i,kind:'user_claim',source:'current ephemeral session turn '+(i+1),digest:crypto.createHash('sha256').update(t).digest('hex')}));
 provenance.push({id:'engine',kind:'inference',source:'oof-discovery deterministic rules v1.0'});
 const observations=turns.map((t,i)=>({id:'o'+i,text:t,type:/\d|log|measur|meran/i.test(t)?'reported_measurement':'reported_observation',kind:'user_claim',provenance_ids:['u'+i]}));
 const supporting=[],contradictory=[];
 for(const [i,e] of evidence.slice(0,20).entries()){
  if(!e?.text||!['supports','contradicts'].includes(e.relation)||!e.source)throw Error('Evidence requires text, source and relation');
  // Only an application-supplied verifier can attest evidence; HTTP text cannot.
  const verified=Boolean(e.receipt&&verifyEvidence(e)===true),kind=verified?'verified':'user_claim',pid='e'+i;
  provenance.push({id:pid,kind,source:clean(e.source),digest:crypto.createHash('sha256').update(clean(e.text)).digest('hex')});
  (e.relation==='supports'?supporting:contradictory).push({id:'f'+i,text:clean(e.text),kind,provenance_ids:[pid]});
 }
 // Contradiction signals in prose remain reported claims, never verified tests.
 turns.forEach((t,i)=>{if(/however|contradict|predates|before.*deploy|not caused|ale |proti|pred nasaden/i.test(norm(t)))contradictory.push({id:'c'+i,text:t,kind:'user_claim',provenance_ids:['u'+i]});});
 const gaps=['Expected outcome, observed outcome and operational boundary need corroboration.','Independent evidence discriminating between the candidate explanations is missing.'].map((text,i)=>({id:'g'+i,text,provenance_ids:['engine']}));
 const explicitAssumptions=turns.flatMap((t,i)=>[...t.matchAll(/(?:because|caused by|must be|i assume|predpokladam|pretoze|pricinou je)\s+([^.!?]+)/gi)].map(m=>({text:m[1],pid:'u'+i})));
 const assumptions=(explicitAssumptions.length?explicitAssumptions:[{text:'The reported symptom identifies the root problem.',pid:'u0'}]).slice(0,8).map((a,i)=>({id:'a'+i,text:a.text,status:'UNVERIFIED',evidence_ids:[],provenance_ids:[a.pid,'engine']}));
 evidence.slice(0,20).forEach((e,i)=>{const a=assumptions.find(a=>a.id===e.assumption_id);if(a){a.evidence_ids.push('f'+i);const record=[...supporting,...contradictory].find(f=>f.id==='f'+i);if(record.kind==='verified')a.status=e.relation==='contradicts'?'CONTRADICTED':a.status==='CONTRADICTED'?'CONTRADICTED':'SUPPORTED';}});
 for(const a of assumptions)if(/unknown|not assessable|cannot assess/i.test(a.text))a.status='NOT_ASSESSABLE';
 const hypotheses=(domain?.hypotheses||['The reported behavior may have a cause within the stated operational boundary.','The report may omit a dependency, measurement issue or relevant context.']).map((text,i)=>({id:'h'+i,text,confidence:'UNVERIFIED_CANDIDATE',supporting_ids:[],contradictory_ids:[],missing_ids:gaps.map(g=>g.id),verification_test:domain?.test||'Establish the expected behavior, timestamps and an independent reproducible observation.',provenance_ids:['engine','u0']}));
 hypotheses[0].contradictory_ids.push(...contradictory.filter(c=>c.id.startsWith('c')).map(c=>c.id));
 // Evidence is tied to a named hypothesis, not indiscriminately attached to every candidate.
 evidence.slice(0,20).forEach((e,i)=>{const h=hypotheses.find(h=>h.id===e.hypothesis_id);if(h)h[e.relation==='supports'?'supporting_ids':'contradictory_ids'].push('f'+i);});
 const chosen=hypotheses[0];let status='UNRESOLVED',validation=null;
 const verifiedSupport=supporting.filter(e=>e.kind==='verified'&&chosen.supporting_ids.includes(e.id));
 const verifiedContra=contradictory.filter(e=>e.kind==='verified'&&chosen.contradictory_ids.includes(e.id));
 if(verifiedContra.length)status='CONTRADICTED';else if(verifiedSupport.length)status='PROVISIONAL';
 if(status==='PROVISIONAL'&&criterion?.description&&typeof criterion.evaluate==='function'&&criterion.evaluate({hypothesis:chosen,evidence:verifiedSupport})===true){status='VALIDATED';validation={criteria:clean(criterion.description),evidence_ids:verifiedSupport.map(e=>e.id)};chosen.confidence='EVIDENCE_VALIDATED';}
 if(status==='CONTRADICTED')chosen.confidence='CONTRADICTED_BY_VERIFIED_EVIDENCE';
 const actions=[{id:'v0',text:domain?.test||hypotheses[0].verification_test,provenance_ids:['engine']},{id:'v1',text:'What outcome was expected, and what independent record would distinguish these explanations?',provenance_ids:['engine']}];
 const field=label=>context.match(new RegExp('(?:^|[\\n;])\\s*(?:'+label+'):\\s*([^\\n;]+)','i'))?.[1]||null;
 const result={schema_version:'1.0',problem:{stated,candidate_root:chosen.text,status,objective:field('objective|goal')||'Establish the evidence-supported problem before selecting a solution.',affected_system:domain?.id||'unspecified',boundary:field('boundary')||'Not independently established',expected_outcome:field('expected'),observed_outcome:field('observed')||'User-reported observations below; not independently verified',symptom_not_root:true},observations,assumptions,hypotheses,supporting_evidence:supporting,contradictory_evidence:contradictory,evidence_gaps:gaps,verification_actions:actions,knowledge_references:[],provenance,validation,report_only:true,metrics:{processing_ms:performance.now()-started,additional_model_calls:0}};
 // Search hints are resolved by the existing navigator, never asserted as
 // registry membership or architecture relationships. No domain means no handoff.
 const hints=domain?.id==='water'||domain?.id==='energy'?'RSGA resource infrastructure':domain?.id==='value'?'VFM asset value lifecycle':domain?.id==='authorization'&&/qualification|workplace/i.test(context)?'AGA qualification authority':domain?.id==='authorization'?'ASGA agent payment permission':domain?.id==='software'&&/chatbot/i.test(context)?'AIG behavioral governance':domain?.query;
 validate(result);return {result,state:{turns},navigation_query:domain?`${hints} ${stated}`:'',changed_problem:changed};
}
function explain(result,language='en'){
 const sk=language==='sk';
 return `${sk?'Analýza problému':'Problem Discovery'} - ${result.problem.status}\n\n${sk?'Uvádzaný problém':'Stated problem'}: ${result.problem.stated}\n\n${sk?'Príznaky (tvrdenia používateľa)':'Symptoms (user reports)'}:\n${result.observations.map(o=>'- '+o.text).join('\n')}\n\n${sk?'Predpoklady - neoverené':'Assumptions - unverified'}:\n${result.assumptions.map(a=>'- '+a.text).join('\n')}\n\n${sk?'Možné vysvetlenia, nie potvrdené príčiny':'Candidate explanations, not confirmed causes'}:\n${result.hypotheses.map(h=>'- '+h.text).join('\n')}\n\n${sk?'Protichodné záznamy - overenie podľa označenia':'Contradictory records - see evidence classification'}:\n${result.contradictory_evidence.map(c=>'- '+c.text+' ['+c.kind+']').join('\n')||'- None supplied / neposkytnuté'}\n\n${sk?'Chýbajúce dôkazy':'Evidence gaps'}:\n${result.evidence_gaps.map(g=>'- '+g.text).join('\n')}\n\n${sk?'Ďalšie overenie':'Next verification'}: ${result.verification_actions[0].text}\n${result.verification_actions[1].text}`;
}
module.exports={discover,validate,explain,wantsDiscovery};
