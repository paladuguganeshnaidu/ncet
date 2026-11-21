'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const read=name=>fs.readFileSync(path.join(__dirname,'..','public',name),'utf8');
test('client script passes JavaScript syntax validation',()=>{
 const result=spawnSync(process.execPath,['--check',path.join(__dirname,'..','public','app.js')],{encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);
});
test('custom mouse cursor and pointer tracking are fully removed',()=>{
 const js=read('app.js'),html=read('index.html'),css=read('style.css');
 assert.doesNotMatch(js,/cursorDot|pointermove|mousemove|mouseenter|mouseleave/);
 assert.doesNotMatch(html,/cursor-dot|cursorDot/);
 assert.doesNotMatch(css,/\.cursor-dot\b/);
});
test('quick links, testing section and mobile navigation are available',()=>{
 const html=read('index.html');
 for(const id of ['home','studio','tests','toc','clearInput','menuToggle','nextStep','prevStep'])assert.match(html,new RegExp('id="'+id+'"'));
 assert.match(html,/mobile-dock/);
 assert.match(html,/hero-shortcuts/);
 assert.match(html,/aria-controls="nav"/);
});
test('3D visual pauses when hidden and honors reduced motion',()=>{
 const js=read('app.js');
 assert.match(js,/document\.hidden/);
 assert.match(js,/prefers-reduced-motion/);
 assert.match(js,/cancelAnimationFrame/);
 assert.match(js,/IntersectionObserver/);
});
