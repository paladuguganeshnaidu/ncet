'use strict';
let csrf='', selected=null;
const $=id=>document.getElementById(id);
const escapeHtml=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function show(id,yes){$(id).classList.toggle('hidden',!yes)}
function notify(text,error=false){$('alert').className=error?'error':'success';$('alert').textContent=text;$('alert').classList.remove('hidden')}
async function api(url,opts={}){const headers={...(opts.headers||{})};if(csrf&&opts.method&&opts.method!=='GET')headers['X-CSRF-Token']=csrf;let response=await fetch(url,{credentials:'same-origin',cache:'no-store',...opts,headers});let body=await response.json().catch(()=>({}));if(!response.ok){let detail=body.detail;if(Array.isArray(detail))detail=detail.map(x=>x.msg).join('; ');throw new Error(typeof detail==='string'?detail:'Request failed. Try again.')}return body}
async function start(){try{const me=await api('/api/auth/me');if(me.user.role!=='student')throw new Error('Use a registered student account.');csrf=me.csrf;let profile=await api('/api/bca/me');$('who').textContent=[profile.usn,profile.branch,'Semester '+profile.semester].filter(Boolean).join(' · ');show('sign-in',false);show('logout',true);show('change-password',profile.must_change_password);show('workspace',!profile.must_change_password);if(!profile.must_change_password){await loadCases();await loadShowcase()}}catch{show('sign-in',true);show('workspace',false);show('change-password',false);show('logout',false)}}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();let fd=new FormData(e.target);let usn=String(fd.get('usn')||'').trim().toLowerCase();try{let login=await api('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:usn,password:fd.get('password'),role:'student'})});if(login.user.role!=='student')throw new Error('Not a student account.');csrf=login.csrf;e.target.reset();notify('Signed in.');await start()}catch(err){notify(err.message,true);$('login-password').value=''}});
$('logout').addEventListener('click',async()=>{try{await api('/api/auth/logout',{method:'POST'})}catch{}csrf='';selected=null;location.replace('/students/portal')});
$('password-form').addEventListener('submit',async e=>{e.preventDefault();const fd=new FormData(e.target);const button=e.target.querySelector('button[type=submit]');button.disabled=true;button.setAttribute('aria-busy','true');try{await api('/api/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({old_password:fd.get('old_password'),new_password:fd.get('new_password')})});e.target.reset();notify('Password updated. You can now submit requests.');await start()}catch(err){notify(err.message,true)}finally{button.disabled=false;button.removeAttribute('aria-busy')}});
let studentCaseOffset=0,studentCaseTimer=null,studentCaseRequest=0,studentCaseTotal=0;
async function loadCases(){
 const request=++studentCaseRequest,query=new URLSearchParams({offset:String(studentCaseOffset),limit:'12'});
 for(const [key,value] of new FormData($('student-case-filters'))){
  if(String(value).trim())query.set(key,String(value).trim());
 }
 $('student-case-page').textContent='Loading…';
 try{
  const x=await api('/api/bca/cases?'+query);
  if(request!==studentCaseRequest)return;
  const stats=x.counts||{},total=Number(x.all_total||0);
  studentCaseTotal=x.total;
  $('student-case-stats').textContent=total+' total · '+(stats.submitted||0)+' new · '+(stats.in_review||0)+' in review · '+(stats.resolved||0)+' resolved · '+(stats.closed||0)+' closed';
  const activeStatus=new FormData($('student-case-filters')).get('status')||'all';
  $('student-case-metrics').innerHTML=[['all','All requests',total],['submitted','New',stats.submitted||0],['in_review','In review',stats.in_review||0],['resolved','Resolved',stats.resolved||0],['closed','Closed',stats.closed||0]].map(([key,label,count])=>`<button type="button" data-case-status="${key}" aria-pressed="${String(activeStatus===key)}"><span>${label}</span><strong>${count}</strong></button>`).join('');
  $('student-case-page').textContent=x.total?(studentCaseOffset+1)+'–'+(studentCaseOffset+x.items.length)+' of '+x.total:'No matching requests';
  $('student-case-prev').disabled=studentCaseOffset===0;
  $('student-case-next').disabled=!x.has_more;
  $('case-list').innerHTML=x.items.map(item=>`<button type="button" class="entry student-case-entry" data-ref="${escapeHtml(item.reference)}"><span class="row"><strong>${escapeHtml(item.subject)}</strong><span class="status ${escapeHtml(item.status)}">${escapeHtml(item.status.replaceAll('_',' '))}</span></span><span class="small muted">${escapeHtml(item.reference)} · ${escapeHtml(item.category)} · Updated ${escapeHtml(new Date(item.updated_at).toLocaleDateString())}</span><span class="case-next-step"><strong>Next step:</strong> ${escapeHtml(item.next_step||'Open this request for the latest status.')}</span>${item.latest_hod_reply?`<span class="case-latest-reply"><strong>Latest HOD reply</strong><span>${escapeHtml(item.latest_hod_reply)}${item.latest_hod_reply.length>=240?'…':''}</span>${item.latest_hod_reply_at?`<small>${escapeHtml(new Date(item.latest_hod_reply_at).toLocaleString())}</small>`:''}</span>`:''}</button>`).join('')||'<p class="muted">No matching requests. Change your filters or submit a new request.</p>';
  for(const btn of $('case-list').querySelectorAll('[data-ref]'))btn.addEventListener('click',()=>openCase(btn.dataset.ref));
 }catch(err){if(request===studentCaseRequest)notify(err.message,true)}
}
function resetStudentCases(){studentCaseOffset=0;void loadCases()}
$('student-case-metrics').addEventListener('click',event=>{
 const button=event.target.closest('[data-case-status]');if(!button)return;
 $('student-case-filters').elements.status.value=button.dataset.caseStatus;resetStudentCases();
});
$('student-case-filters').addEventListener('submit',e=>{e.preventDefault();resetStudentCases()});
$('student-case-filters').addEventListener('change',resetStudentCases);
$('student-case-filters').elements.search.addEventListener('input',()=>{
 clearTimeout(studentCaseTimer);studentCaseTimer=setTimeout(resetStudentCases,300);
});
$('student-case-clear').addEventListener('click',()=>{
 $('student-case-filters').reset();clearTimeout(studentCaseTimer);resetStudentCases();
});
$('student-case-prev').addEventListener('click',()=>{studentCaseOffset=Math.max(0,studentCaseOffset-12);void loadCases()});
$('student-case-next').addEventListener('click',()=>{if(studentCaseOffset+12<studentCaseTotal){studentCaseOffset+=12;void loadCases()}});

$('new-case').addEventListener('submit',async e=>{e.preventDefault();let data=Object.fromEntries(new FormData(e.target));let button=e.target.querySelector('button[type=submit]');button.disabled=true;button.setAttribute('aria-busy','true');try{let result=await api('/api/bca/cases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});notify(`Request ${result.reference} submitted to your department HOD.`);e.target.reset();await loadCases();await openCase(result.reference);window.dispatchEvent(new Event('ncet:notifications-refresh'))}catch(err){notify(err.message,true)}finally{button.disabled=false;button.removeAttribute('aria-busy')}});
async function openCase(ref){try{let c=await api('/api/bca/cases/'+encodeURIComponent(ref));selected=ref;show('case-detail',true);$('case-heading').textContent=c.subject;$('case-info').innerHTML=`<p><span class="status ${escapeHtml(c.status)}">${escapeHtml(c.status.replaceAll('_',' '))}</span> <span class="muted small">${escapeHtml(ref)} · ${escapeHtml(c.category)}</span></p><p>${escapeHtml(c.description)}</p><h3>Conversation</h3>${c.messages.map(m=>`<div class="thread"><strong>${escapeHtml(m.author)}</strong> <span class="small muted">${escapeHtml(new Date(m.created_at).toLocaleString())}</span><p>${escapeHtml(m.body)}</p></div>`).join('')||'<p class="muted">No replies yet.</p>'}`;$('case-receipt-print').innerHTML=`<p class="receipt-label">NCET VerifyFlow · Student request receipt</p><h1>${escapeHtml(c.subject)}</h1><p class="receipt-reference">${escapeHtml(c.reference)}</p><p><strong>Status:</strong> ${escapeHtml(c.status.replaceAll('_',' '))}</p><p><strong>Category:</strong> ${escapeHtml(c.category)}</p><p><strong>Submitted:</strong> ${escapeHtml(new Date(c.created_at).toLocaleString())}</p><h2>Request details</h2><div class="receipt-description">${escapeHtml(c.description)}</div><p class="receipt-label">Private student record · generated ${escapeHtml(new Date().toLocaleString())}</p>`;show('message-form',c.status!=='closed');$('case-detail').scrollIntoView({behavior:'smooth'});}catch(err){notify(err.message,true)}}
$('print-receipt').addEventListener('click',()=>{document.body.classList.add('printing-receipt');window.print()});
window.addEventListener('afterprint',()=>document.body.classList.remove('printing-receipt'));
$('close-case').addEventListener('click',()=>{show('case-detail',false);selected=null});
$('message-form').addEventListener('submit',async e=>{e.preventDefault();if(!selected)return;try{await api('/api/bca/cases/'+encodeURIComponent(selected)+'/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:new FormData(e.target).get('message')})});e.target.reset();notify('Reply sent.');await openCase(selected)}catch(err){notify(err.message,true)}});
start();

async function loadShowcase(){
 try{
  const p=await api('/api/bca/showcase/me');
  $('showcase-name').value=p.full_name;
  $('showcase-dept').value=p.department||'Department not set';
  $('showcase-mobile').value=p.mobile;
  $('showcase-email').value=p.email;
  $('showcase-about').value=p.about;
  $('showcase-interests').value=(p.interests||[]).join(', ');
  $('showcase-projects').replaceChildren();
  for(const project of (p.projects||[]))addProjectEditor(project);
  $('showcase-skills').value=p.skills.join(', ');
  for(const input of document.querySelectorAll('.social-link'))input.value=p.social_links?.[input.name]||'';
  updateSkillCount();
  $('showcase-certs').value=p.certificates.map(c=>[c.title,c.issuer,c.proof_url].join(' | ')).join('\n');
  $('showcase-public').checked=p.published;
  setProfilePhoto(Boolean(p.photo_available));
  show('my-public-profile',p.published);
  $('my-public-profile').href='/students/profile/'+encodeURIComponent(p.usn);
 }catch(err){notify(err.message,true)}
}
$('showcase-form').addEventListener('submit',async e=>{
 e.preventDefault();
 const skills=$('showcase-skills').value.trim().replace(/^\{|\}$/g,'').split(',').map(s=>s.trim()).filter(Boolean);
 if(skills.length>100)return notify('You can publish up to 100 skills. Remove '+(skills.length-100)+' and try again.',true);
 const social_links=Object.fromEntries([...document.querySelectorAll('.social-link')].filter(el=>el.value.trim()).map(el=>[el.name,el.value.trim()]));
 const certText=$('showcase-certs').value.trim();
 const certificates=[];
 if(certText){
  for(const line of certText.split('\n')){
   if(!line.trim())continue;
   const parts=line.split('|').map(s=>s.trim());
   if(parts.length!==3)return notify('Each certificate requires title | issuer | public HTTPS URL.',true);
   certificates.push({title:parts[0],issuer:parts[1],proof_url:parts[2]});
  }
 }
 const interests=$('showcase-interests').value.split(',').map(x=>x.trim()).filter(Boolean);
 if(interests.length>20)return notify('Use up to 20 interests.',true);
 const projects=[...document.querySelectorAll('#showcase-projects .resume-edit-project')].map(row=>({
  title:row.querySelector('[name=title]').value.trim(),
  description:row.querySelector('[name=description]').value.trim(),
  technologies:row.querySelector('[name=technologies]').value.split(',').map(x=>x.trim()).filter(Boolean),
  github_url:row.querySelector('[name=github_url]').value.trim(),
  live_url:row.querySelector('[name=live_url]').value.trim(),
 })).filter(x=>x.title||x.description||x.github_url||x.live_url);
 if(projects.some(x=>!x.title))return notify('Every project requires a title.',true);
 const body={full_name:$('showcase-name').value,mobile:$('showcase-mobile').value,
  email:$('showcase-email').value,about:$('showcase-about').value,
  skills,certificates,social_links,interests,projects,publish:$('showcase-public').checked};
 const btn=e.target.querySelector('button[type=submit]');btn.disabled=true;btn.setAttribute('aria-busy','true');
 try{
  const response=await api('/api/bca/showcase/me',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  notify(response.published?'Public profile published. Private contact information is hidden.':'Profile saved privately.');
  await loadShowcase();
 }catch(err){notify(err.message,true)}finally{btn.disabled=false;btn.removeAttribute('aria-busy')}
});

function updateSkillCount(){
 const values=$('showcase-skills').value.trim().replace(/^\{|\}$/g,'').split(',').map(x=>x.trim()).filter(Boolean);
 $('skill-count').textContent=values.length+' / 100 skills. '+(values.length>100?'Please remove '+(values.length-100)+' skills.':'Single-letter skills such as C and R are supported.');
 $('skill-count').className=values.length>100?'error':'small muted';
}
$('showcase-skills').addEventListener('input',updateSkillCount);


function selectStudentTab(name){
 const active=name==='profile'?'profile':'requests';
 for(const tab of ['requests','profile']){
  const visible=tab===active;
  show('student-tab-'+tab,visible);
  const button=$('student-tab-'+tab+'-button');
  button.classList.toggle('active',visible);
  button.setAttribute('aria-selected',String(visible));
  button.tabIndex=visible?0:-1;
 }
}
for(const tab of document.querySelectorAll('[data-student-tab]')){
 tab.addEventListener('click',()=>selectStudentTab(tab.dataset.studentTab));
 tab.addEventListener('keydown',e=>{
  if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight')return;
  e.preventDefault();
  const next=tab.dataset.studentTab==='requests'?'profile':'requests';
  selectStudentTab(next);
  $('student-tab-'+next+'-button').focus();
 });
}
function setProfilePhoto(available){
 const img=$('showcase-photo-preview');
 if(available){
  img.src='/api/bca/showcase/me/photo?ts='+Date.now();
  img.alt='Your saved student profile photo';
 }else{
  img.src='/static/ncet-brand.svg';
  img.alt='NCET emblem placeholder for your profile photo';
 }
 show('remove-showcase-photo',available);
 show('showcase-photo-fallback',!available);
}
$('showcase-photo-form').addEventListener('submit',async e=>{
 e.preventDefault();
 const file=$('showcase-photo').files[0];
 if(!file)return notify('Choose a photo to upload.',true);
 const acceptable=['image/png','image/jpeg','image/webp'];
 if(!acceptable.includes(file.type))return notify('Use JPEG, PNG or WebP.',true);
 if(file.size===0 || file.size>=150000)return notify('Choose a photo strictly under 150 KB.',true);
 const btn=e.target.querySelector('[type=submit]');
 btn.disabled=true;btn.setAttribute('aria-busy','true');
 $('photo-upload-status').textContent='Uploading and optimizing photo…';
 try{
  const data=new FormData();data.set('file',file);
  await api('/api/bca/showcase/me/photo',{method:'PUT',body:data});
  $('showcase-photo').value='';
  setProfilePhoto(true);
  $('photo-upload-status').textContent='Photo saved. It appears publicly only while your profile is published.';
  notify('Profile photo uploaded.');
 }catch(err){$('photo-upload-status').textContent=err.message;notify(err.message,true)}
 finally{btn.disabled=false;btn.removeAttribute('aria-busy')}
});
$('remove-showcase-photo').addEventListener('click',async ()=>{
 if(!confirm('Remove your saved profile photo?'))return;
 const btn=$('remove-showcase-photo');
 btn.disabled=true;btn.setAttribute('aria-busy','true');
 try{
  await api('/api/bca/showcase/me/photo',{method:'DELETE'});
  setProfilePhoto(false);
  $('photo-upload-status').textContent='Photo removed.';
  notify('Photo removed from your student profile.');
 }catch(err){notify(err.message,true)}
 finally{btn.disabled=false;btn.removeAttribute('aria-busy')}
});

function addProjectEditor(project={}){
 const list=$('showcase-projects');
 if(list.children.length>=8)return notify('Maximum 8 projects per portfolio.',true);
 const wrapper=document.createElement('div');
 wrapper.className='resume-edit-project';
 const n=list.children.length+1;
 wrapper.innerHTML=`<div class="resume-edit-project-heading"><strong>Project ${n}</strong><button type="button" class="btn" data-remove-project>Remove</button></div>
 <div class="field"><label>Project title <input name="title" minlength="3" maxlength="105" placeholder="e.g. Campus Verification Portal"></label></div>
 <div class="field"><label>Description <textarea name="description" maxlength="550" rows="2" placeholder="Problem, approach and outcome"></textarea></label></div>
 <div class="field"><label>Technologies (comma separated) <input name="technologies" maxlength="650" placeholder="Python, React, PostgreSQL"></label></div>
 <div class="split">
  <div class="field"><label>GitHub repository <input name="github_url" type="url" maxlength="400" placeholder="https://github.com/username/repo"></label></div>
  <div class="field"><label>Live demo / website <input name="live_url" type="url" maxlength="400" placeholder="https://example.com"></label></div>
 </div>`;
 for(const field of ['title','description','technologies','github_url','live_url']){
  const input=wrapper.querySelector('[name='+field+']');
  const value=field==='technologies'?(project.technologies||[]).join(', '):(project[field]||'');
  input.value=value;
 }
 wrapper.querySelector('[data-remove-project]').addEventListener('click',()=>{
  wrapper.remove();
  [...list.children].forEach((x,i)=>x.querySelector('strong').textContent='Project '+(i+1));
 });
 list.appendChild(wrapper);
}
$('add-showcase-project').addEventListener('click',()=>addProjectEditor());
