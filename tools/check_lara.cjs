'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
function files(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name)):e.name.endsWith('.js')?[path.join(dir,e.name)]:[]);}
for(const file of [...files(path.join(root,'lara')),...files(path.join(root,'lib'))]){const result=spawnSync(process.execPath,['--check',file],{encoding:'utf8'});if(result.status!==0){process.stderr.write(result.stderr);process.exit(1);}}
for(const file of ['reports/lara-read-only-consumer-contract.json','reports/lara-integration-readiness.json','objects-core.json','representations.json','relationships.json'])JSON.parse(fs.readFileSync(path.join(root,'data/knowledge',file),'utf8'));
JSON.parse(fs.readFileSync(path.join(root,'schemas/oof-problem-discovery.v1.schema.json'),'utf8'));
console.log('LaRA syntax and required registry JSON checks passed. Runtime readiness and model quality require separate tests.');
