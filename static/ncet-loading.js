/* NCET lightweight loading state: delayed until a request actually takes time.
   Nothing blocks painting or artificially delays submission. */
(()=>{'use strict';
 if(window.__ncetLoadingInstalled)return;window.__ncetLoadingInstalled=true;
 // The document workspace already manages its own async forms and notifications.
 // A second global popup obscures the signed-in dashboard and can outlive login.
 if(/^\/app\/?$/.test(window.location.pathname))return;
 const originalFetch=window.fetch.bind(window);
 let pending=0,showTimer=0,loader=null;
 const MAX_INDICATOR_MS=2000;
 const skip=url=>/\/api\/(?:auth\/me|alerts|notifications)/.test(url);
 function ensure(){
  if(loader)return loader;
  if(!document.body)return null;
  loader=document.createElement('div');
  loader.className='ncet-network-loader';
  loader.setAttribute('role','status');
  loader.setAttribute('aria-live','polite');
  loader.setAttribute('aria-label','Loading');
  loader.hidden=true;
  const mark=document.createElement('span');
  mark.className='ncet-loader-dot';mark.setAttribute('aria-hidden','true');
  const label=document.createElement('span');label.textContent='Working on your request…';
  loader.append(mark,label);document.body.append(loader);
  return loader;
 }
 function sync(){
  if(showTimer){clearTimeout(showTimer);showTimer=0}
  const node=ensure();if(!node)return;
  if(!pending){node.hidden=true;return}
  if(node.hidden)showTimer=setTimeout(()=>{
    showTimer=0;
    if(pending && ensure())loader.hidden=false;
  },420);
 }
 function start(){pending++;sync()}
 function finish(){pending=Math.max(0,pending-1);sync()}
 window.fetch=function(...args){
  const request=args[0];const init=args[1]||{};
  const url=typeof request==='string'?request:request?.url||'';
  const method=String(init.method||(request instanceof Request?request.method:'GET')).toUpperCase();
  // Background GET polling must never hold a page-wide loading toast open.
  // The action button or form owns any extended processing state.
  const active=!skip(url)&&!['GET','HEAD','OPTIONS'].includes(method);
  if(!active)return originalFetch(...args);
  start();
  let completed=false,watchdog=0;
  const release=()=>{
   if(completed)return;
   completed=true;clearTimeout(watchdog);finish();
  };
  watchdog=setTimeout(release,MAX_INDICATOR_MS);
  try{
   return Promise.resolve(originalFetch(...args)).finally(release);
  }catch(error){release();throw error}
 };
 // Show loading feedback on traditional form navigation only if a request is slow.
 document.addEventListener('submit',event=>{
  if(event.defaultPrevented)return;
  queueMicrotask(()=>{
   if(event.defaultPrevented)return;
   start();
   const form=event.target;form.dataset.ncetNavigating='true';
   setTimeout(()=>{delete form.dataset.ncetNavigating;finish()},2000);
  });
 },true);
 window.addEventListener('pageshow',()=>{
  pending=0;if(showTimer)clearTimeout(showTimer);
  showTimer=0;if(loader)loader.hidden=true;
 });
})();

