/* NCET portfolio tabs: server HTML remains fully readable without JS. */
(()=>{
'use strict';
const ids=['about','skills','projects','certifications','interests','links'];
const nav=document.querySelector('.resume-anchors');
const stage=document.getElementById('resume-tab-stage');
if(!nav||!stage)return;
const tabs=ids.map(id=>nav.querySelector('a[href="#'+id+'"]'));
const panels=ids.map(id=>document.getElementById(id));
if(tabs.some(t=>!t)||panels.some(p=>!p))return;
const reduce=window.matchMedia('(prefers-reduced-motion: reduce)');
const valid=()=>{const id=decodeURIComponent(location.hash.slice(1));return ids.includes(id)?id:'about'};
let active=null;
let heightReset=null;
nav.setAttribute('role','tablist');
nav.setAttribute('aria-label','Student portfolio sections');
for(let i=0;i<ids.length;i++){
 tabs[i].setAttribute('role','tab');
 tabs[i].setAttribute('aria-controls',ids[i]);
 tabs[i].setAttribute('aria-selected','false');
 tabs[i].tabIndex=-1;
 panels[i].setAttribute('role','tabpanel');
 panels[i].setAttribute('aria-labelledby',tabs[i].id);
 panels[i].tabIndex=0;
}
/* Styles only hide sections after JS has initialized: no-JS remains crawlable. */
function activate(id,{focus=false,animate=true}={}){
 if(!ids.includes(id)||active===id)return;
 const old=active;
 const previousHeight=stage.getBoundingClientRect().height;
 clearTimeout(heightReset);
 stage.style.height='';
 for(let i=0;i<ids.length;i++){
  const selected=ids[i]===id;
  tabs[i].setAttribute('aria-selected',String(selected));
  tabs[i].tabIndex=selected?0:-1;
  panels[i].hidden=!selected;
  tabs[i].classList.toggle('is-selected',selected);
 }
 active=id;
 stage.classList.remove('tab-animate');
 if(old&&animate&&!reduce.matches){
  stage.style.height=previousHeight+'px';
  const next=panels[ids.indexOf(id)];
  /* Force a height transition, without animating layout-affecting properties every frame. */
  void stage.offsetHeight;
  stage.classList.add('tab-animate');
  stage.style.height=next.scrollHeight+'px';
  next.classList.remove('tab-appearing');
  void next.offsetWidth;
  next.classList.add('tab-appearing');
  heightReset=setTimeout(()=>{stage.style.height='';stage.classList.remove('tab-animate');},260);
 }
 if(focus)tabs[ids.indexOf(id)].focus({preventScroll:true});
 tabs[ids.indexOf(id)].scrollIntoView({inline:'nearest',block:'nearest',behavior:'instant'});
}
for(let i=0;i<tabs.length;i++){
 const tab=tabs[i];
 tab.addEventListener('click',event=>{
  event.preventDefault();
  const id=ids[i];
  if(active!==id){history.pushState({studentTab:id},'', '#'+id);activate(id);}
 });
 tab.addEventListener('keydown',event=>{
  const key=event.key;
  let next;
  if(key==='ArrowRight')next=(i+1)%ids.length;
  else if(key==='ArrowLeft')next=(i+ids.length-1)%ids.length;
  else if(key==='Home')next=0;
  else if(key==='End')next=ids.length-1;
  else return;
  event.preventDefault();
  const id=ids[next];
  history.pushState({studentTab:id},'','#'+id);
  activate(id,{focus:true});
 });
}
window.addEventListener('popstate',()=>activate(valid(),{animate:!reduce.matches}));
window.addEventListener('hashchange',()=>activate(valid(),{animate:!reduce.matches}));
stage.classList.add('tabs-enhanced');
activate(valid(),{animate:false});
})();