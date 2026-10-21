/* Progressive enhancement for NCET. No scroll-jacking, blocking overlays or dependencies. */
(()=>{
'use strict';
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
function init(){
 document.documentElement.classList.add('ncet-motion-ready');
 // The official college photo source can be temporarily unavailable.
 // Show the verified transparent institutional wordmark instead of a broken image.
 document.querySelectorAll('.ncet-campus-photo img,.about-photo img').forEach(img=>{
  const fallback=()=>{
   if(img.dataset.ncetFallback)return;
   img.dataset.ncetFallback='1';
   img.classList.add('ncet-campus-fallback');
   img.src='/static/ncet-brand.svg';
   img.alt='Nagarjuna College of Engineering and Technology official emblem';
  };
  img.addEventListener('error',fallback,{once:true});
  if(img.complete && img.naturalWidth===0)fallback();
 });
 // On scroll, reveal content with a one-time lightweight transform (never hidden).
 if('IntersectionObserver' in window && !reduced.matches){
  const io=new IntersectionObserver(entries=>{
   for(const entry of entries)if(entry.isIntersecting){
    entry.target.classList.add('ncet-enter');io.unobserve(entry.target);
   }
  },{rootMargin:'0px 0px -40px 0px',threshold:.08});
  document.querySelectorAll('main > section:not(.experience-hero), .service-card, .guide-grid details, .campus-journey-card, .institutional-counter').forEach(el=>{
   el.classList.add('ncet-reveal');io.observe(el);
  });
 }
 // Visual counters begin when they are first on screen. Original value remains HTML-readable.
 const numbers=document.querySelectorAll('[data-ncet-count]');
 function count(el){
  const target=Number(el.getAttribute('data-ncet-count'));
  if(!Number.isInteger(target)||target<0||target>999999)return;
  const suffix=el.getAttribute('data-ncet-suffix')||'';
  const final=target.toLocaleString('en-IN')+suffix;
  if(reduced.matches||!('requestAnimationFrame' in window)){el.textContent=final;return}
  const length=850;const begin=performance.now();
  function frame(now){
   if(!el.isConnected)return;
   const fraction=Math.min(1,(now-begin)/length);
   const easing=1-Math.pow(1-fraction,3);
   el.textContent=Math.round(target*easing).toLocaleString('en-IN')+suffix;
   if(fraction<1)requestAnimationFrame(frame);
   else el.textContent=final;
  }
  requestAnimationFrame(frame);
 }
 if('IntersectionObserver' in window){
  const counts=new IntersectionObserver(entries=>{
   for(const item of entries)if(item.isIntersecting){
    counts.unobserve(item.target);count(item.target);
   }
  },{threshold:.35});
  numbers.forEach(el=>counts.observe(el));
 }else numbers.forEach(count);
 // Keyboard-friendly accordion: the native details elements do the real work.
 // Mobile nav: progressive button controls a nav already visible without JS.
 const nav=document.querySelector('.topnav .navlinks');
 const header=nav?.closest('.topnav');
 if(nav && header && nav.querySelectorAll('a').length>=3){
  const button=document.createElement('button');
  button.type='button';button.className='ncet-menu-toggle';button.setAttribute('aria-expanded','false');
  button.setAttribute('aria-controls','ncet-mobile-links');
  button.setAttribute('aria-label','Open navigation menu');
  button.innerHTML='<span aria-hidden="true" class="ncet-menu-lines"><i></i><i></i><i></i></span><span>Menu</span>';
  nav.id='ncet-mobile-links';
  header.querySelector('.nav-inner')?.appendChild(button);
  header.classList.add('ncet-menu-enhanced');
  const setOpen=open=>{
   button.setAttribute('aria-expanded',String(open));
   button.setAttribute('aria-label',open?'Close navigation menu':'Open navigation menu');
   header.classList.toggle('ncet-nav-open',open);
  };
  button.addEventListener('click',()=>setOpen(button.getAttribute('aria-expanded')!=='true'));
  nav.addEventListener('click',e=>{if(e.target.closest('a'))setOpen(false)});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&header.classList.contains('ncet-nav-open')){setOpen(false);button.focus()}});
  document.addEventListener('pointerdown',e=>{if(header.classList.contains('ncet-nav-open')&&!header.contains(e.target))setOpen(false)});
  const query=window.matchMedia('(min-width: 701px)');
  query.addEventListener?.('change',e=>{if(e.matches)setOpen(false)});
 }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
else init();
})();