'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');const js=fs.readFileSync(path.join(root,'assets/lara/lara.js'),'utf8');const css=fs.readFileSync(path.join(root,'assets/lara/lara.css'),'utf8');
test('2D avatar declares bounded accessible states and honours reduced motion',()=>{for(const state of ['idle','listening','thinking','speaking','success','error','sleeping'])assert.match(js,new RegExp(`['\\\"]${state}['\\\"]`));assert.match(js,/lara-avatar-2d/);assert.match(js,/aria-live/);assert.match(css,/prefers-reduced-motion/);});
test('listening state is driven by browser speech start, not simulated microphone text',()=>{assert.match(js,/rec\.onstart=\(\)=>\{setAvatar\('listening'\)/);assert.doesNotMatch(js,/simulat(?:e|ed) listening/i);});
