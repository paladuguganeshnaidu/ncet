'use strict';
// Authenticated notification panel. Refreshes every twelve seconds while visible.
(()=>{
 const container=document.createElement('aside');container.id='ncet-alerts';container.hidden=true;
 container.innerHTML='<button id="alert-toggle" type="button" aria-expanded="false" aria-controls="alert-list">Notifications <span id="alert-count"></span></button><section id="alert-list" role="region" aria-label="In-app notifications" hidden><h2>Notifications</h2><div id="alert-items">Loading…</div><button id="alert-close" type="button">Close</button></section>';
 document.body.append(container);
 const toggle=container.querySelector('#alert-toggle'),panel=container.querySelector('#alert-list'),list=container.querySelector('#alert-items'),badge=container.querySelector('#alert-count');
 const esc=v=>String(v??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
 let csrf='',running=false;
 function open(show){panel.hidden=!show;toggle.setAttribute('aria-expanded',String(show));}
 toggle.addEventListener('click',()=>{open(panel.hidden);if(!panel.hidden)refresh()});
 container.querySelector('#alert-close').addEventListener('click',()=>open(false));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){open(false)}});
 async function refresh(){
  if(running||document.visibilityState==='hidden')return;running=true;
  try{
   const res=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});
   if(!res.ok){container.hidden=true;return}
   const me=await res.json();csrf=me.csrf;
   const response=await fetch('/api/alerts/inbox',{credentials:'same-origin',cache:'no-store'});
   if(!response.ok)throw Error('Unable to refresh notifications');
   const result=await response.json();
   container.hidden=false;badge.textContent=result.unread?'('+result.unread+' new)':'';
   list.innerHTML=result.items.length?result.items.map(n=>'<a class="alert-entry '+(n.seen?'':'alert-unread')+'" href="'+esc(n.link)+'" data-notice="'+esc(n.id)+'"><span>'+esc(n.category)+'</span><strong>'+esc(n.text)+'</strong><small>'+esc(new Date(n.at).toLocaleString())+'</small></a>').join(''):'<p>No new activity yet.</p>';
  }catch(e){if(!container.hidden)list.textContent='Notifications could not be refreshed.'}
  finally{running=false}
 }
 container.addEventListener('click',e=>{
  const link=e.target.closest('[data-notice]');if(!link)return;
  fetch('/api/alerts/'+encodeURIComponent(link.dataset.notice)+'/read',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':csrf}}).catch(()=>{});
 });
 document.addEventListener('visibilitychange',refresh);
 window.addEventListener('ncet:notifications-refresh',refresh);
 window.addEventListener('focus',refresh);
 setInterval(refresh,12000);
 refresh();
})();
