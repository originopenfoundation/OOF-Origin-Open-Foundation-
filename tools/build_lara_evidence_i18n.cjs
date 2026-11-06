'use strict';
const fs=require('node:fs'),path=require('node:path'),localization=require('../lib/oof-localization');
const labels=Object.fromEntries(localization.languages.map(language=>[language,{evidence:localization.copy(language).evidence}]));
fs.writeFileSync(path.resolve(__dirname,'../assets/lara/evidence-i18n.json'),JSON.stringify(labels,null,2)+'\n');
