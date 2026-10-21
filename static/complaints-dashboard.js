/* Department HOD only. Server returns authorized, filtered case summaries;
   full complaint bodies are loaded only when HOD opens a specific case. */
(()=>{'use strict';
 const $=id=>document.getElementById(id);
 const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const titles={submitted:'New submission',in_review:'In review',resolved:'Resolved',closed:'Closed'};
 const categoryTitles={academics:'Academics',faculty:'Faculty',examinations:'Examinations',facilities:'Facilities',fees:'Fees',documentation:'Documentation',request:'General request',other:'Other'};
 const colors={submitted:'is-new',in_review:'',resolved:'is-done',closed:'is-done'};
 const fmt=value=>{const d=new Date(value);return Number.isFinite(+d)?d.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}):'Not recorded'};
 let csrf='',selected=null,offset=0,latest=null,abort=null,searchTimer=null,sequence=0;
 const pageSize=20;
 function info(message,error=false){$('complaints-message').textContent=message;$('complaints-message').classList.toggle('is-error',error)}
 async function api(url,options={}){
   const headers={Accept:'application/json',...(options.headers||{})};
   if(options.method && options.method!=='GET') headers['X-CSRF-Token']=csrf;
   const res=await fetch(url,{credentials:'same-origin',cache:'no-store',...options,headers});
   const data=await res.json().catch(()=>({}));
   if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Request failed ('+res.status+').');
   return data;
 }
 function values(){
   const form=new FormData($('case-filters'));
   const params=new URLSearchParams({offset:String(offset),limit:String(pageSize)});
   for(const name of ['search','attention','status','category','from_date','to_date','sort']){
     const value=String(form.get(name)||'').trim();if(value && (value!=='all'||name==='status'||name==='category'))params.set(name,value);
   }
   return params;
 }
 function badge(status){return '<span class="case-pill '+esc(status)+'">'+esc(titles[status]||status)+'</span>'}
 function renderBars(host,entries,total){
   $(host).innerHTML=entries.map(([key,label,count])=>'<div class="case-bar-item '+(colors[key]||'')+'"><span><span>'+esc(label)+'</span><b>'+count+'</b></span><div class="case-bar-track" role="meter" aria-label="'+esc(label)+'" aria-valuemin="0" aria-valuemax="'+Math.max(total,1)+'" aria-valuenow="'+count+'"><i style="width:'+(total?100*count/total:0)+'%"></i></div></div>').join('')||'<p class="muted">No cases recorded.</p>';
 }
 function render(data){
   latest=data;
   $('complaints-workspace').hidden=false;
   info('');
   const count=Number(data.all_total||0),counts=data.counts||{},categories=data.categories||{};
   $('kpi-all').textContent=count.toLocaleString();
   for(const key of Object.keys(titles))$('kpi-'+key).textContent=Number(counts[key]||0).toLocaleString();
   const status=$('case-filters').elements.status.value,attention=$('case-filters').elements.attention.value;
   $('priority-count-waiting').textContent=Number(data.attention_counts?.awaiting_reply||0).toLocaleString();
   $('priority-count-aged').textContent=Number(data.attention_counts?.older_than_7d||0).toLocaleString();
   for(const button of document.querySelectorAll('[data-attention]'))button.setAttribute('aria-pressed',String(button.dataset.attention===attention));
   for(const card of document.querySelectorAll('.case-kpi'))card.setAttribute('aria-pressed',String(card.dataset.status===status));
   renderBars('case-status-bars',Object.keys(titles).map(k=>[k,titles[k],Number(counts[k]||0)]),count);
   renderBars('case-category-bars',Object.keys(categoryTitles).filter(k=>categories[k]).map(k=>[k,categoryTitles[k],Number(categories[k])]),count);
   $('case-count').textContent=data.total.toLocaleString()+' matching';
   $('case-pages-label').textContent=data.total?offset+1+'–'+(offset+data.items.length)+' of '+data.total:'No matching complaints';
   $('case-prev').disabled=offset===0;
   $('case-next').disabled=!data.has_more;
   const filters=values();
   $('filter-summary').textContent=filters.get('search')||status!=='all'||attention!=='all'||filters.get('category')!=='all'||filters.has('from_date')||filters.has('to_date')
     ?'Filtered department results':'Showing all department requests';
   $('list-updated').textContent='Updated '+fmt(new Date());
   $('case-results').innerHTML=data.items.length?data.items.map(c=>
     '<button type="button" class="complaint-row '+(c.status==='submitted'?'is-new':'')+(c.awaiting_reply?' needs-reply':'')+(c.older_than_7d?' is-aged':'')+'" data-ref="'+esc(c.reference)+'">'+
       '<span class="complaint-row-title"><strong>'+esc(c.subject)+'</strong>'+badge(c.status)+'</span>'+
       (c.awaiting_reply?'<span class="complaint-row-emphasis">Awaiting HOD reply</span>':c.older_than_7d?'<span class="complaint-row-emphasis">Open over 7 days</span>':'')+
       '<span class="complaint-row-meta"><span><b>Reference</b> '+esc(c.reference)+'</span>'+
       '<span><b>Student</b> '+esc(c.student?.name||'—')+'</span>'+
       '<span><b>Category</b> '+esc(categoryTitles[c.category]||c.category)+'</span>'+
       '<span><b>Received</b> '+esc(fmt(c.created_at))+'</span>'+
       '<span><b>Updated</b> '+esc(fmt(c.updated_at))+'</span></span></button>'
   ).join(''):'<div class="case-empty"><strong>No matching requests</strong><p>Adjust the filters or clear them to see other cases.</p></div>';
 }
 async function load(){
   const seq=++sequence;
   if(abort)abort.abort();
   abort=new AbortController();
   $('case-count').textContent='Loading…';
   try{
     const data=await api('/api/bca/cases?'+values(),{signal:abort.signal});
     if(seq!==sequence)return;
     render(data);
   }catch(err){
     if(err.name==='AbortError'||seq!==sequence)return;
     $('case-count').textContent='Unavailable';
     info(err.message,true);
   }
 }
 function refresh(){offset=0;void load()}
 async function openCase(ref,refreshOnly=false){
   selected=ref;
   if(!refreshOnly){
     $('detail-content').textContent='Loading request details…';
     $('case-dialog-message').textContent='';
   }
   if(!$('case-dialog').open)$('case-dialog').showModal();
   try{
     const item=await api('/api/bca/cases/'+encodeURIComponent(ref));
     if(selected!==ref)return;
     $('detail-heading').textContent=item.subject;
     $('detail-content').innerHTML='<div class="detail-meta">'+badge(item.status)+
       '<span>'+esc(item.reference)+'</span><span>'+esc(item.category)+'</span>'+
       '<span>Created: '+esc(fmt(item.created_at))+'</span><span>Updated: '+esc(fmt(item.updated_at))+'</span>'+
       '<span>Student: '+esc(item.student?.name||'')+' ('+esc(item.student?.usn||'')+')</span></div>'+
       '<div class="detail-body">'+esc(item.description)+'</div>'+
       '<h3>Conversation history</h3>'+
       '<div class="case-conversation">'+(item.messages||[]).map(m=>
         '<article><strong>'+esc(m.author)+'</strong><time datetime="'+esc(m.created_at)+'">'+esc(fmt(m.created_at))+
         '</time><p>'+esc(m.body)+'</p></article>').join('')+'</div>';
     $('case-actions').hidden=item.status==='closed';
     $('update-case-form').elements.status.value=item.status==='submitted'?'in_review':item.status;
     if(!refreshOnly)$('case-dialog-message').textContent=item.status==='closed'?'This request is closed. Past messages remain available for review.':'';
   }catch(err){$('detail-content').textContent=err.message;$('case-actions').hidden=true;}
 }
 function close(){selected=null;if($('case-dialog').open)$('case-dialog').close()}
 $('close-dialog').addEventListener('click',close);
 $('case-dialog').addEventListener('close',()=>{selected=null;});
 $('case-dialog').addEventListener('click',e=>{if(e.target===$('case-dialog'))close()});
 $('case-results').addEventListener('click',e=>{const row=e.target.closest('[data-ref]');if(row)void openCase(row.dataset.ref)});
 $('case-filters').addEventListener('submit',e=>{e.preventDefault();refresh()});
 $('case-filters').addEventListener('change',()=>{clearTimeout(searchTimer);refresh()});
 document.querySelectorAll('[data-attention]').forEach(button=>button.addEventListener('click',()=>{
   $('case-filters').elements.attention.value=button.dataset.attention;
   refresh();$('case-list-title').scrollIntoView({block:'start',behavior:'auto'});
 }));
 $('case-filters').elements.search.addEventListener('input',()=>{
   clearTimeout(searchTimer);searchTimer=setTimeout(refresh,300);
 });
 $('reset-filters').addEventListener('click',()=>{$('case-filters').reset();clearTimeout(searchTimer);refresh()});
 document.querySelectorAll('.case-kpi').forEach(b=>b.addEventListener('click',()=>{
   $('case-filters').elements.status.value=b.dataset.status;refresh();
   $('case-list-title').scrollIntoView({block:'start',behavior:'auto'});
 }));
 $('case-prev').addEventListener('click',()=>{offset=Math.max(0,offset-pageSize);void load()});
 $('case-next').addEventListener('click',()=>{if(latest?.has_more){offset+=pageSize;void load()}});
 $('refresh-complaints').addEventListener('click',()=>void load());
 async function mutate(form,url,options){
   const button=form.querySelector('[type=submit]');
   button.disabled=true;button.setAttribute('aria-busy','true');
   try{
     await api(url,options);
     const reference=selected;
     form.reset();
     await load();
     if(selected===reference){
       await openCase(reference,true);
       $('case-dialog-message').textContent='Saved successfully. The student has been notified.';
     }
   }catch(err){$('case-dialog-message').textContent=err.message}
   finally{button.disabled=false;button.removeAttribute('aria-busy')}
 }
 $('update-case-form').addEventListener('submit',e=>{
   e.preventDefault();if(!selected)return;
   const values=Object.fromEntries(new FormData(e.target));
   if(['resolved','closed'].includes(values.status)&&String(values.note||'').trim().length<5){
     $('case-dialog-message').textContent='Please enter at least five characters explaining the resolution.';return;
   }
   void mutate(e.target,'/api/bca/cases/'+encodeURIComponent(selected)+'/status',{
     method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});
 });
 $('reply-case-form').addEventListener('submit',e=>{
   e.preventDefault();if(!selected)return;
   const data=Object.fromEntries(new FormData(e.target));
   void mutate(e.target,'/api/bca/cases/'+encodeURIComponent(selected)+'/messages',{
     method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 });
 (async()=>{
   try{
     const session=await api('/api/auth/me');
     if(session.user?.role!=='hod'||!String(session.user.department||'').trim())
       throw Error('Only an authorized department HOD can manage private student requests.');
     const bcaDepartments=['bca','computer applications','bachelor of computer applications'];
     $('department-enrollment').hidden=!bcaDepartments.includes(String(session.user.department).trim().toLowerCase());
     csrf=session.csrf;await load();
   }catch(err){info(err.message,true);}
 })();
})();
