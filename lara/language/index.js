'use strict';
const fs=require('node:fs');const path=require('node:path');
const config=JSON.parse(fs.readFileSync(path.join(__dirname,'languages.json'),'utf8'));
// Only actual published website routes extend the existing communication settings.
try{const inventory=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../data/localization/lara-language-inventory.json'),'utf8'));for(const locale of inventory.languages){if(!config.languages[locale.code])config.languages[locale.code]={...(config.languages[locale.code.split('-')[0]]||config.languages.en),name:locale.language};}}catch{}
const LANGUAGES=Object.fromEntries(Object.entries(config.languages||{}).map(([id,value])=>[id,{...value}]));
const lexicon=Object.fromEntries(Object.entries(LANGUAGES).map(([id,value])=>[id,value.detection_keywords||[]]));
const aliases=Object.fromEntries(Object.entries(LANGUAGES).map(([id,value])=>[id,value.term_aliases||{}]));
function normalize(word){return String(word).toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');}
const stopWords=new Set((config.stop_words||[]).map(normalize));
const scripts=(config.script_detection||[]).map(x=>[x.language,new RegExp(x.pattern,'u')]);
function requestedLanguage(text){const match=String(text).toLowerCase().match(/(?:answer|respond|reply|switch|now|say.*)\s+(?:in|to)\s+(.+?)(?:[.!?]|$)/i)?.[1];if(match){for(const [id,locale] of Object.entries(LANGUAGES))if(match===locale.name.toLowerCase()||match===id)return id;try{const inventory=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../data/localization/lara-language-inventory.json'),'utf8'));return inventory.languages.find(l=>l.language.toLowerCase()===match)?.code||null;}catch{}}return null;}
function detect(text,preferred='auto'){
  if(preferred&&preferred!=='auto'&&LANGUAGES[preferred])return preferred;
  const requested=requestedLanguage(text);if(requested)return requested;
  if(/[\u0600-\u06ff]/u.test(text)&&LANGUAGES.ar)return 'ar';
  if(/[\u0900-\u097f]/u.test(text)&&LANGUAGES.hi)return 'hi';
  if(/[\u0400-\u04ff]/u.test(text)&&LANGUAGES.ru)return 'ru';
  const explicit=String(text).match(/(?:in|to|auf|po|v)\s+(english|slovak|german|deutsch|slovenčine|slovensky|anglicky|nemčine|nemecky)\b/iu)?.[1]?.toLowerCase();
  if(explicit)return /english|anglicky/.test(explicit)?'en':/slovak|sloven|slovensky/.test(explicit)?'sk':'de';
  if(/^(?:ahoj\b|dobrý deň|kto si\b|s čím\b|čo vieš\b|vysvetli\b)/iu.test(String(text).trim()))return 'sk';
  if(/^(?:hallo\b|guten tag\b|wer bist du\b|was kannst du\b|erkläre\b)/iu.test(String(text).trim()))return 'de';
  for(const [lang,re] of scripts)if(re.test(text))return lang;
  const lowered=String(text).toLocaleLowerCase();let best=Object.keys(LANGUAGES)[0]||'en',score=0;
  for(const [lang,words] of Object.entries(lexicon)){const n=words.reduce((sum,w)=>sum+(lowered.includes(w)?1:0),0);if(n>score){best=lang;score=n;}}
  return best;
}
function queryTerms(text,lang){
  const original=String(text);const lowered=original.toLocaleLowerCase();
  const names=[...original.matchAll(/\b[A-Z][A-Z0-9]{1,9}\b/g)].map(m=>m[0]);
  const words=lowered.match(/[\p{L}\p{N}™®-]{2,}/gu)||[];const knownAliases=aliases[lang]||{};
  const noise=new Set(['explain','describe','define','tell','please','briefly','simple','simpler','language','answer','question','seriously','professionally','odpovedz','vysvetli','slovensky','slovak','english','german','deutsch','erklare','bitte']);
  const subjects=new Set(['governance','architecture','authority','standard','module','knowledge']);
  const normalized=words.map(normalize).filter(w=>(!stopWords.has(w)||subjects.has(w))&&!noise.has(w));
  for(const [from,to] of Object.entries(knownAliases))if(lowered.includes(from.toLocaleLowerCase())&&!stopWords.has(normalize(to)))normalized.push(to);
  const terms=[...new Set([...names.map(normalize),...normalized])];
  return terms.length>1?terms.filter(w=>w!=='oof'):terms;
}
module.exports={LANGUAGES,lexicon,aliases,config,detect,queryTerms,requestedLanguage};
