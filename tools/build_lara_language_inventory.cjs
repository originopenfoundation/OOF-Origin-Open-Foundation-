'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function discover(root){
 const policy=JSON.parse(fs.readFileSync(path.join(root,'data/localization/localization-policy.json'),'utf8'));
 const home=fs.readFileSync(path.join(root,'index.html'),'utf8');
 const reps=JSON.parse(fs.readFileSync(path.join(root,'data/knowledge/representations.json'),'utf8')).representations;
 const candidates=[{prefix:'',code:'en',english:'English'},...policy.languages];
 return {version:'2.0',policy:'Published access language is not evidence of model quality or translated canonical methodology.',languages:candidates.flatMap(locale=>{
  const file=locale.prefix?locale.prefix+'/index.html':'index.html',full=path.join(root,file);if(!fs.existsSync(full))return [];
  const html=fs.readFileSync(full,'utf8'),htmlLang=html.match(/<html[^>]*lang="([^"]+)"/i)?.[1],url='https://originopenfoundation.org/'+(locale.prefix?locale.prefix+'/':'');
  const published=htmlLang?.toLowerCase()===locale.code.toLowerCase()&&home.includes('hreflang="'+locale.code+'"')&&home.includes('href="'+url+'"');
  if(!published)return [];
  return [{language:locale.english,code:locale.prefix||'en',html_language:htmlLang,route:'/'+(locale.prefix?locale.prefix+'/':''),translation_availability:locale.prefix?'published_access_page':'canonical_english',canonical_definitions_translated:false,knowledge_sources:reps.filter(r=>String(r.language).toLowerCase()===locale.code.toLowerCase()||String(r.language).toLowerCase()===(locale.prefix||'en')).length,model_capability:'NOT_VERIFIED',tested_quality:'BLOCKED',activation_status:'evaluation_required',source:file,source_sha256:crypto.createHash('sha256').update(html.replace(/\r\n/g,'\n')).digest('hex'),quality_warning:/\?{3,}/.test(html)?'Existing page contains placeholder-like question marks; translation quality not certified.':null}];
 })};
}
if(require.main===module){const root=path.resolve(__dirname,'..'),report=discover(root),file=path.join(root,'data/localization/lara-language-inventory.json');fs.writeFileSync(file,JSON.stringify(report,null,2)+'\n');console.log(report.languages.map(l=>l.code).join(', '));}
module.exports={discover};
