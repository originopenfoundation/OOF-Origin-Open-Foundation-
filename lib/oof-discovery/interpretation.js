'use strict';
// Multilingual operational cues, not a methodology registry. Cues propose
// questions to investigate; they never attest architecture membership or edges.
const crypto=require('node:crypto');
const normal=s=>String(s||'').normalize('NFKC').normalize('NFD').replace(/[\u0300-\u036f]/g,'').normalize('NFC').toLowerCase();
const concepts={
 identity:/\bidentity\b|identit|identidad|identidade|identita|identite|身份|身分|アイデンティティ|신원|идентич|личност|पहचान|هوية/u,
 authority:/authori[sz]|permission|unauthor|opravnen|povoleni|berechtig|befug|autoris|autoriza|autorizz|权限|權限|授权|授權|権限|권한|разреш|полномоч|अनुमति|प्राधिक|صلاحية|إذن/u,
 autonomy:/agent|autonom|агент|автоном|代理|智能体|エージェント|자율|에이전트|एजेंट|स्वायत्त|وكيل|مستقل/u,
 behavior:/behavio[u]?r|chatbot|spravani|verhalten|comport|поведен|行为|行為|振る舞|動作|행동|व्यवहार|سلوك/u,
 energy:/energy|energi|power supply|strom|electric|eletric|energia|能源|电力|電力|エネルギー|에너지|энерги|ऊर्जा|طاقة/u,
 water:/water|vod[ay]|wasser|eau\b|agua|acqua|水|물|вод[аы]|जल|पानी|مياه|ماء/u,
 value:/token|asset|valuation|value|hodnot|wert|valeur|valor|valore|токен|актив|стоимост|价值|價值|資産|가치|자산|मूल्य|संपत्ति|قيمة|اصل/u,
 software:/software|softver|deploy|logiciel|ソフトウェア|软件|軟體|소프트웨어|программ|सॉफ्टवेयर|برمج/u,
 workplace:/workplace|qualification|kvalifik|pracovisk|arbeitsplatz|qualifik|competenc|qualific|职场|職場|資格|자격|рабоч|квалификац|योग्यता|कार्यस्थल|تاهيل|مؤهل/u,
 failure:/fail|incorrect|unexpected|unauthor|without|problem|nefung|neoprav|chyba|fehler|unerwart|unbefugt|ohne|erreur|echec|sans|non autoris|fallo|sin permiso|falha|sem permiss|errore|senza|失敗|故障|未经|未經|無断|無許可|실패|무단|ошиб|несанкц|сбой|विफल|बिना|فشل|دون|غير مصرح/u,
 changed:/^(?:new problem|different problem|change the problem|novy problem|iny problem|neues problem|autre probleme|nuevo problema|novo problema|nuovo problema|新问题|新問題|別の問題|새로운 문제|новая проблема|नई समस्या|مشكلة جديدة)/u,
 followup:/^(?:also|but|however|logs|evidence|actually|and|ale|dalsi|zistili|auch|aber|cependant|aussi|ademas|pero|tambem|mas|inoltre|pero|另外|但是|また|しかし|또한|하지만|также|однако|लेकिन|और|لكن|ايضا)/u
};
const archetypes={identity:'OBIDENITY',authority:'AGA',autonomy:'ASGA',behavior:'AIG',energy:'RSGA',water:'RSGA',value:'VFM',software:'SLGA',workplace:'AGA'};
const questions={identity:'Which actor or object is identified, and what establishes that identity?',authority:'Who may authorize the exact action, tool and operational scope?',autonomy:'What autonomous action crossed the specified operational boundary?',behavior:'Which AI behavior differed from the expected policy?',energy:'Which energy supply, demand and measurement boundary is affected?',water:'Which water resource and measurement boundary is affected?',value:'What asset, valuation and transaction evidence supports the value claim?',software:'Which software lifecycle change and assurance evidence are relevant?',workplace:'What qualification and task-specific authorization are established?'};
function interpret(text,{previous=null,language='en'}={}){
 const raw=String(text||'').slice(0,5000),n=normal(raw),changed=concepts.changed.test(n);
 const followup=!changed&&concepts.followup.test(n)&&previous;
 const contextual=followup?[...new Set([...(previous.concepts||[]),...Object.keys(archetypes).filter(k=>concepts[k].test(n))])]:Object.keys(archetypes).filter(k=>concepts[k].test(n));
 // Definitions stay ordinary lookup unless the visitor explicitly selects analysis.
 const simple=/^(?:what (?:is|are)|define|explain|co je|vysvetli|was ist|erklar|qu.est.ce|que es|o que e|cos.e|什么是|甚麼是|とは|무엇|что такое|क्या है|ما هو)/u.test(n)&&!concepts.failure.test(n);
 return {schema_version:'1.0',language,original:raw,digest:crypto.createHash('sha256').update(raw).digest('hex'),concepts:contextual,changed_problem:changed,followup:Boolean(followup),problem_signal:!simple&&contextual.length>0&&(concepts.failure.test(n)||Boolean(followup)),candidates:contextual.map(concept=>({concept,acronym:archetypes[concept],responsibility:questions[concept],basis:'OPERATIONAL_CUE_HYPOTHESIS'})),qualification:'User-language operational cues only; not verified evidence or canonical mapping.'};
}
module.exports={interpret,normal};
