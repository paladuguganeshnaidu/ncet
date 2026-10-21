'use strict';
const $=id=>document.getElementById(id);
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let queryRevision=0,offset=0,currentQuery='';
const PAGE_SIZE=18;
const initials=name=>name.trim().split(/\s+/).slice(0,2).map(s=>s[0]||'').join('').toUpperCase();
async function loadDirectory(q='',pageOffset=0){
 const revision=++queryRevision;
 currentQuery=q;offset=pageOffset;
 $('directory-results').setAttribute('aria-busy','true');
 $('directory-status').textContent='Finding published students…';
 try{
  const params=new URLSearchParams({q,limit:String(PAGE_SIZE),offset:String(offset)});
  const response=await fetch('/api/bca/directory?'+params,{credentials:'omit',cache:'no-store'});
  if(!response.ok)throw Error('Published student directory is temporarily unavailable.');
  const data=await response.json();if(revision!==queryRevision)return;
  const items=data.items||[];
  $('directory-results').innerHTML=items.map(p=>{
   const photo=p.photo_url
    ?'<img class="profile-card-avatar" src="'+escapeHtml(p.photo_url)+'" width="64" height="64" alt="'+escapeHtml(p.name)+' profile photo" loading="lazy">'
    :'<span class="profile-card-initial" aria-hidden="true">'+escapeHtml(initials(p.name))+'</span>';
   return '<article class="profile-card">'+photo+
    '<h2><a href="/students/profile/'+encodeURIComponent(p.usn)+'">'+escapeHtml(p.name)+'</a></h2>'+
    '<p><strong>'+escapeHtml(p.usn)+'</strong> · '+escapeHtml(p.department||'Department unavailable')+'</p>'+
    '<p>'+ (p.skills?.length?'Skills: '+p.skills.slice(0,4).map(escapeHtml).join(', '):'Explore this student portfolio')+'</p>'+
    '<a class="btn" href="/students/profile/'+encodeURIComponent(p.usn)+'">View profile →</a></article>';
  }).join('');
  const total=Number(data.total??items.length)||0;
  const displayed=items.length ? (offset===0&&items.length===total ? 'Showing '+total+' published profiles' : 'Showing '+(offset+1)+'–'+(offset+items.length)+' of '+total+' published profiles') : 'No published profiles match your search.';
  $('directory-status').textContent=displayed;
  const pager=$('directory-pagination');
  if(pager){
   pager.innerHTML=(offset>0?'<button type="button" class="btn" data-dir="prev">← Previous</button>':'')+
    (offset+items.length<total?'<button type="button" class="btn" data-dir="next">Next students →</button>':'');
   pager.hidden=total<=PAGE_SIZE;
  }
  // Avoid duplicate cards when the full server-rendered fallback is also present.
  const fallback=document.querySelector('.server-profile-links ul');
  if(fallback)fallback.hidden=true;
 }catch(err){if(revision===queryRevision){
  $('directory-results').replaceChildren();
  $('directory-status').textContent=err.message;
 }}finally{if(revision===queryRevision)$('directory-results').setAttribute('aria-busy','false')}
}
$('search-profiles').addEventListener('submit',e=>{e.preventDefault();loadDirectory($('student-search').value.trim(),0)});
$('clear-search').addEventListener('click',()=>{$('student-search').value='';loadDirectory('',0)});
$('directory-pagination')?.addEventListener('click',e=>{
 const button=e.target.closest('[data-dir]');if(!button)return;
 loadDirectory(currentQuery,Math.max(0,offset+(button.dataset.dir==='next'?PAGE_SIZE:-PAGE_SIZE)));
});
const search=new URLSearchParams(location.search).get('q')||'';
$('student-search').value=search.slice(0,60);
loadDirectory(search.slice(0,60),0);
