/* HOD-only task tracking visualizations. The API is authoritative for scoped totals. */
(()=>{'use strict';
 const $=selector=>document.querySelector(selector);
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const categories={
   working:['assigned','on_hold','correction_required'],
   reviewing:['verifying','awaiting_hod','manual_review'],
   approved:['approved'],unassigned:['unassigned']
 };
 const stageNames={unassigned:'Unassigned',assigned:'Working',on_hold:'On hold',
   correction_required:'Corrections needed',verifying:'Automated review',awaiting_hod:'HOD review',
   manual_review:'Manual review',approved:'Approved'};
 const eventNames={created:'Reference uploaded',assigned:'Assigned to staff',
   submitted:'Staff submission received',on_hold:'On hold',resumed:'Work resumed',
   approved:'Approved by HOD',correction_requested:'Corrections requested',
   deadline_changed:'Deadline changed',verification_finished:'Verification completed',
   reminder_sent:'Deadline reminder sent'};
 let data=null,request=null,queued=false,filter='all',page=0,lastExpanded=new Set(),searchTimer=null;
 const pageSize=50;
 const dateTime=value=>{
   if(!value)return 'Not yet recorded';
   const d=new Date(value);
   return Number.isFinite(+d)?d.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}):'Unavailable';
 };
 const dateKey=value=>{
   const d=new Date(value);
   return Number.isFinite(+d)?[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-'):'';
 };
 const eventLabel=event=>eventNames[event]||String(event||'Updated').replaceAll('_',' ');
 const category=(task,k)=>k==='all'||(k==='overdue'?task.overdue:categories[k]?.includes(task.state));
 const colors=['#F6872A','#0E2455','#087C59','#74859F','#D7E0EC'];
 const statDefs=[
  ['total','Total tasks','All department tasks'],
  ['working','Working / on hold','Staff assignments'],
  ['reviewing','Awaiting review','Verification and HOD'],
  ['approved','Approved','Final HOD decisions'],
  ['overdue','Overdue','Late open tasks']
 ];
 function cards(){
   const cards=$('#dashboard-metrics');
   cards.innerHTML=statDefs.map(([k,label,description])=>
     `<button type="button" data-dash-status="${k==='total'?'all':k}" aria-pressed="${filter===(k==='total'?'all':k)}">
        <span>${escape(label)}</span><strong>${Number(data.counts[k]||0).toLocaleString()}</strong><small>${escape(description)}</small></button>`
   ).join('');
 }
 function charts(){
   const overall=data.counts.total||0,states=[
     ['Working',data.counts.working||0,colors[0]],
     ['Awaiting review',data.counts.reviewing||0,colors[1]],
     ['Approved',data.counts.approved||0,colors[2]],
     ['Unassigned',data.counts.unassigned||0,colors[3]]
   ];
   let covered=0;
   const segments=states.map(([label,count,color])=>{
     const start=overall?covered/overall*100:0;covered+=count;
     return `${color} ${start}% ${overall?covered/overall*100:0}%`;
   });
   $('#dash-stage-chart').setAttribute('aria-label',states.map(([label,n])=>label+': '+n).join(', '));
   $('#dash-stage-chart').innerHTML=`<div class="stage-visual">
     <div class="stage-ring" style="background:${overall?'conic-gradient('+segments.join(',')+')':'#E8EEF5'}">
      <div class="stage-ring-inner"><strong>${overall.toLocaleString()}</strong><small>total tasks</small></div>
     </div><ul class="stage-legend">${states.map(([label,n,color])=>
       `<li><span class="stage-dot" style="background:${color}"></span><span>${label}</span><strong>${n}</strong></li>`).join('')}</ul>
     </div>`;
   const days=Array.from({length:14},(_,index)=>{
     const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()-13+index);
     return {day:dateKey(d),date:d,n:0};
   });
   // Server provides approvals across the entire department, not just the
   // most recently updated 500-task listing.
   const map=new Map(days.map(d=>[d.day,d]));
   for(const entry of data.daily_approvals||[]){
     const day=map.get(dateKey(entry.at));
     if(day)day.n++;
   }
   const max=Math.max(...days.map(d=>d.n),1);
   $('#dash-trend-chart').setAttribute('aria-label',days.map(d=>d.date.toLocaleDateString()+': '+d.n+' approvals').join('; '));
   $('#dash-trend-chart').innerHTML=`<div class="daily-chart">
     ${days.map(d=>`<div class="daily-column"><span class="daily-number">${d.n||''}</span>
       <span class="daily-bar" title="${escape(d.date.toDateString())}: ${d.n} approvals" style="height:${Math.max(d.n/max*122,d.n?6:2)}px"></span>
       <span class="daily-date">${escape(d.date.toLocaleDateString(undefined,{month:'short',day:'numeric'}))}</span>
       </div>`).join('')}
     </div><p class="subtle chart-caption">Recorded HOD approvals by date · displayed in your local timezone.</p>`;
 }
 function staffView(){
   const host=$('#dash-staff');
   if(!data.staff?.length){host.innerHTML='<p class="dashboard-empty">No tasks have been assigned to staff yet.</p>';return}
   host.innerHTML=data.staff.map(s=>{
     const base=Math.max(s.total,1);
     return `<button type="button" class="staff-load" data-staff="${s.id}">
       <span class="staff-head"><strong>${escape(s.name)}</strong><small>${s.total} tasks</small></span>
       <span class="load-bar" aria-label="${s.working} working, ${s.reviewing} reviewing, ${s.approved} approved">
         <span class="load-working" style="width:${100*s.working/base}%"></span>
         <span class="load-reviewing" style="width:${100*s.reviewing/base}%"></span>
         <span class="load-approved" style="width:${100*s.approved/base}%"></span>
       </span>
       <span class="staff-foot">${s.working} working · ${s.reviewing} in review · ${s.approved} approved${s.overdue?' · '+s.overdue+' overdue':''}</span>
     </button>`;
   }).join('');
 }
 function activity(){
   $('#dash-activity').innerHTML=(data.activity||[]).slice(0,12).map(e=>`
     <li><span class="activity-dot"></span><div>
       <strong>${escape(eventLabel(e.event))} · ${escape(e.file)}</strong>
       <p>${escape(e.actor)}${e.detail?' · '+escape(e.detail):''}</p>
       <time datetime="${escape(e.at)}">${escape(dateTime(e.at))}</time>
     </div></li>`).join('')||'<li class="dashboard-empty">No activity recorded. Updates will appear when staff and HODs work on tasks.</li>';
 }
 function history(t){
   if(!t.history?.length)return '<p class="dashboard-empty">No detailed historical events are available for this task. Its current status is recorded.</p>';
   return `<ol class="dash-history">${t.history.map(e=>`<li>
     <span class="history-time"><time datetime="${escape(e.at)}">${escape(dateTime(e.at))}</time></span>
     <div><strong>${escape(eventLabel(e.event))}</strong><span>${escape(e.actor)}</span>
     ${e.detail?'<p>'+escape(e.detail)+'</p>':''}</div></li>`).join('')}</ol>`;
 }
 function tasksView(){
   const container=$('#dash-tasks');
   lastExpanded=new Set([...container.querySelectorAll('details[open]')].map(node=>node.dataset.taskId));
   const shown=data.tasks||[],offset=Number(data.task_list_offset||0);
   const total=Number(data.task_list_total??shown.length);
   $('#dash-list-count').textContent=total+' matching tasks';
   $('#dash-page-label').textContent=total?(offset+1)+'–'+(offset+shown.length)+' of '+total+' tasks':'No matching tasks';
   $('#dash-prev').disabled=offset===0;
   $('#dash-next').disabled=offset+shown.length>=total;
   $('#dash-truncation').hidden=!data.task_list_truncated;
   if(!shown.length){container.innerHTML='<p class="dashboard-empty">No matching tasks yet. Choose another filter or assign a task to get started.</p>';return}
   container.innerHTML=shown.map(t=>`
     <details class="dashboard-task" data-task-id="${t.id}" ${lastExpanded.has(String(t.id))?'open':''}>
       <summary>
         <span class="track-file"><strong>${escape(t.file)}</strong><small>${escape(t.staff||'Not assigned')}</small></span>
         <span class="track-status ${escape(t.state)}">${escape(stageNames[t.state]||t.state)}${t.overdue?' · OVERDUE':''}</span>
         <span class="track-due"><small>Due date</small><time>${escape(t.deadline?dateTime(t.deadline):'Not set')}</time></span>
         <span class="track-details-label">View history <span aria-hidden="true">⌄</span></span>
       </summary>
       <div class="track-expanded">
         <div class="track-time-grid"><p>Assigned to staff<strong>${escape(dateTime((t.history||[]).find(e=>e.event==='assigned')?.at))}</strong></p>
           <p>Submitted by staff<strong>${escape(dateTime(t.submitted_at))}</strong></p>
           <p>Approved by HOD<strong>${escape(dateTime(t.approved_at))}</strong><small>${escape((t.history||[]).find(e=>e.event==='approved')?.actor||'')}</small></p>
           <p>Last updated<strong>${escape(dateTime(t.updated_at))}</strong></p></div>
         <h4>Activity timeline</h4>${history(t)}
       </div>
     </details>`).join('');
 }
 function options(){
   const target=$('#dash-staff-filter'),previous=target.value;
   target.innerHTML='<option value="all">All staff</option>'+(data.staff||[]).map(s=>
     `<option value="${s.id}">${escape(s.name)}</option>`).join('');
   target.value=[...target.options].some(o=>o.value===previous)?previous:'all';
 }
 function render(){
   cards();charts();staffView();activity();options();tasksView();
   $('#dash-filter').value=filter;
   $('#dash-synced').textContent='Updated '+dateTime(data.as_of);
 }
 async function reload(){
   if(request){queued=true;return request}
   request=(async()=>{
     try{
       const params=new URLSearchParams({offset:String(page*pageSize),limit:String(pageSize),status:filter});
       const search=$('#dash-search').value.trim();
       const staff=$('#dash-staff-filter').value;
       if(search)params.set('search',search);
       if(staff!=='all')params.set('staff_id',staff);
       const due=$('#dash-deadline').value,sort=$('#dash-sort').value;
       if(due!=='all')params.set('deadline_filter',due);
       if(sort!=='updated')params.set('sort',sort);
       if($('#dash-from').value)params.set('from_date',$('#dash-from').value);
       if($('#dash-to').value)params.set('to_date',$('#dash-to').value);
       const res=await fetch('/api/tasks/dashboard?'+params,{credentials:'same-origin',headers:{Accept:'application/json'}});
       if(!res.ok)throw Error('Tracking unavailable ('+res.status+').');
       data=await res.json();render();
     }catch(error){
       $('#dash-synced').textContent=error.message||'Dashboard temporarily unavailable';
     }finally{
       request=null;
       if(queued){queued=false;void reload()}
     }
   })();
   return request;
 }
 document.addEventListener('click',event=>{
   const card=event.target.closest('[data-dash-status]');
   if(card && data){filter=card.dataset.dashStatus;page=0;void reload();
     $('#dash-task-title').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth'});
   }
   const staff=event.target.closest('[data-staff]');
   if(staff && data){$('#dash-staff-filter').value=staff.dataset.staff;page=0;void reload();
     $('#dash-task-title').scrollIntoView({block:'start',behavior:'auto'});
   }
 });
 $('#dash-export').addEventListener('click',()=>{
   const params=new URLSearchParams({status:filter,sort:$('#dash-sort').value});
   const search=$('#dash-search').value.trim(),staff=$('#dash-staff-filter').value;
   const due=$('#dash-deadline').value;
   if(search)params.set('search',search);
   if(staff!=='all')params.set('staff_id',staff);
   if(due!=='all')params.set('deadline_filter',due);
   if($('#dash-from').value)params.set('from_date',$('#dash-from').value);
   if($('#dash-to').value)params.set('to_date',$('#dash-to').value);
   const link=document.createElement('a');
   link.href='/api/tasks/dashboard/export.csv?'+params.toString();
   link.hidden=true;document.body.append(link);link.click();link.remove();
 });
 $('#dash-refresh').addEventListener('click',reload);
 $('#dash-filter').addEventListener('change',e=>{filter=e.target.value;page=0;void reload()});
 $('#dash-staff-filter').addEventListener('change',()=>{page=0;void reload()});
 for(const id of ['#dash-deadline','#dash-from','#dash-to','#dash-sort'])
   $(id).addEventListener('change',()=>{page=0;void reload()});
 $('#dash-reset').addEventListener('click',()=>{
   filter='all';page=0;
   $('#dash-search').value='';$('#dash-filter').value='all';
   $('#dash-staff-filter').value='all';$('#dash-deadline').value='all';
   $('#dash-from').value='';$('#dash-to').value='';$('#dash-sort').value='updated';
   clearTimeout(searchTimer);void reload();
 });
 $('#dash-search').addEventListener('input',()=>{
   page=0;clearTimeout(searchTimer);searchTimer=setTimeout(()=>void reload(),260);
 });
 $('#dash-prev').addEventListener('click',()=>{if(page>0){page--;void reload()}});
 $('#dash-next').addEventListener('click',()=>{
   if(data && (page+1)*pageSize<Number(data.task_list_total||0)){page++;void reload()}
 });
 window.addEventListener('ncet-hod-tasks-refreshed',reload);
})();
