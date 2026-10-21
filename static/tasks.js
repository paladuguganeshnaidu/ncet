/* NCET tasks: all data from authenticated, department-scoped APIs. No secret values in frontend. */
(()=>{'use strict';
const $=s=>document.querySelector(s), safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let me=null,csrf='',tasks=[],staff=[],role='',selected=new Set(),poll=null,checklistTemplates=[],selectedChecklistId='',checklistVersions=[],reviewingTaskId=null;
function say(text,error=false){const el=$('#toast');el.hidden=false;el.textContent=text;el.style.background=error?'#973e31':'#0e2455';clearTimeout(el._timer);el._timer=setTimeout(()=>{el.hidden=true},4800)}
async function api(path,options={}){const method=options.method||'GET';const h={...(options.headers||{})};if(method!=='GET')h['X-CSRF-Token']=csrf;const r=await fetch(path,{...options,headers:h,credentials:'same-origin'});const payload=await r.json().catch(()=>null);if(!r.ok)throw Error(typeof payload?.detail==='string'?payload.detail:`Request failed (${r.status})`);return payload}
const dueDate=value=>value?new Date(value).toLocaleString(undefined,{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'';
const localPickerDate=value=>{if(!value)return '';const d=new Date(value),pad=n=>String(n).padStart(2,'0');return Number.isNaN(d.getTime())?'':d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours())+':'+pad(d.getMinutes())};
function parseDeadline(value){
 if(!value)return null;
 const date=new Date(value);
 if(!Number.isFinite(date.getTime())||date.getTime()<=Date.now())throw Error('Choose a deadline later than the current time.');
 return date.toISOString();
}
function setMinDeadline(){
 const min=localPickerDate(new Date(Date.now()+60000).toISOString());
 $('#assignment-deadline').min=min;
 $('#edit-deadline').min=min;
}
const stateLabel=s=>({unassigned:'Unassigned',assigned:'Assigned',on_hold:'On hold',verifying:'Reviewing',awaiting_hod:'Awaiting HOD',manual_review:'Human review',correction_required:'Corrections needed',approved:'Approved'}[s]||s);
let drafts=new Map();
const RULE_TYPES=['required_heading','required_phrase','max_pages','min_pages','date_present','signature','formatting','grammar','semantic','other'];
function addManualRule(seed={},host=$('#manual-rules')){
  const row=document.createElement('fieldset');row.className='manual-rule';
  const title=document.createElement('legend');title.textContent='Checklist item';row.append(title);
  const titleLabel=document.createElement('label');titleLabel.textContent='Requirement';const titleInput=document.createElement('input');titleInput.type='text';titleInput.maxLength=110;titleInput.required=$('#rules-mode').value!=='ai';titleInput.placeholder='e.g. Include the department approval heading';titleInput.value=seed.title||'';titleLabel.append(titleInput);row.append(titleLabel);
  const typeLabel=document.createElement('label');typeLabel.textContent='Check type';const type=document.createElement('select');
  for(const kind of RULE_TYPES){const option=document.createElement('option');option.value=kind;option.textContent=kind.replaceAll('_',' ');type.append(option)}
  type.value=seed.type||'required_phrase';typeLabel.append(type);row.append(typeLabel);
  const valueLabel=document.createElement('label');valueLabel.textContent='Expected phrase / value (optional)';const value=document.createElement('input');value.type='text';value.maxLength=400;value.value=seed.value||'';valueLabel.append(value);row.append(valueLabel);
  const instructionsLabel=document.createElement('label');instructionsLabel.textContent='Instructions for reviewer (optional)';const instructions=document.createElement('input');instructions.type='text';instructions.maxLength=1300;instructions.value=seed.instructions||'';instructionsLabel.append(instructions);row.append(instructionsLabel);
  const requiredLabel=document.createElement('label');requiredLabel.className='rule-required';const required=document.createElement('input');required.type='checkbox';required.checked=seed.required!==false;requiredLabel.append(required,document.createTextNode(' Required for acceptance'));row.append(requiredLabel);
  const remove=document.createElement('button');remove.type='button';remove.className='btn secondary smallbtn';remove.textContent='Remove item';remove.addEventListener('click',()=>{if(host.children.length>1)row.remove();else{titleInput.value='';value.value='';instructions.value='';type.value='required_phrase';required.checked=true;titleInput.focus()}});row.append(remove);host.append(row);
}
function ruleDrafts(host){
 const rows=[...host.querySelectorAll('.manual-rule')];
 return rows.map((row,index)=>{const fields=row.querySelectorAll('input,select'),title=fields[0].value.trim(),type=fields[1].value,value=fields[2].value.trim(),instructions=fields[3].value.trim(),required=fields[4].checked;
  const id=(title.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'').slice(0,48)||'rule')+'_'+(index+1);
  return {id,title,type,required,value,instructions};
 });
}
function manualRules(host=$('#manual-rules')){
 return ruleDrafts(host).map((rule,index)=>{const {title}=rule;
  if(title.length<3)throw Error(`Checklist item ${index+1}: enter a requirement with at least 3 characters.`);
  return rule;
 });
}
let perFileRuleCache=new Map();
function capturePerFileRules(){
 $('#per-file-rules').querySelectorAll('.per-file-checklist').forEach(card=>perFileRuleCache.set(Number(card.dataset.taskId),ruleDrafts(card.querySelector('.task-rules'))));
}
function renderPerFileChecklists(){
 capturePerFileRules();const host=$('#per-file-rules');host.replaceChildren();
 const defaults=ruleDrafts($('#manual-rules'));
 for(const id of selected){
  const task=tasks.find(item=>item.id===id);if(!task)continue;
  const card=document.createElement('section');card.className='per-file-checklist';card.dataset.taskId=String(id);
  const heading=document.createElement('h4');heading.textContent=task.file;card.append(heading);
  const rules=document.createElement('div');rules.className='task-rules';rules.setAttribute('aria-label',`Checklist for ${task.file}`);
  const seeds=perFileRuleCache.has(id)?perFileRuleCache.get(id):defaults;
  if(seeds.length)seeds.forEach(seed=>addManualRule(seed,rules));else addManualRule({},rules);
  card.append(rules);
  const add=document.createElement('button');add.type='button';add.className='btn secondary';add.dataset.addPerFileRule=String(id);add.textContent='Add requirement';card.append(add);host.append(card);
 }
}
function updateAllocationChecklistUI(){
 const ai=$('#rules-mode').value==='ai';
 const toggleVisible=!ai&&selected.size>1;
 $('#per-file-toggle-label').hidden=!toggleVisible;
 if(!toggleVisible&&selected.size<2)$('#per-file-toggle').checked=false;
 const usePerFile=!ai&&toggleVisible&&$('#per-file-toggle').checked;
 $('#per-file-help').hidden=!usePerFile;$('#per-file-rules').hidden=!usePerFile;
 $('#manual-rules').hidden=ai||usePerFile;$('#manual-actions').hidden=ai||usePerFile;
 $('#manual-help').hidden=ai||usePerFile;$('#checklist-template-tools').hidden=ai||usePerFile;
 $('#rules-mode').required=true;$('#review-confirm').required=ai;
 $('#manual-rules').querySelectorAll('.manual-rule input[type="text"]').forEach(input=>{if(input.closest('.manual-rule').querySelector('label').contains(input))input.required=!ai&&!usePerFile});
 $('#per-file-rules').querySelectorAll('.manual-rule input[type="text"]').forEach(input=>{if(input.closest('.manual-rule').querySelector('label').contains(input))input.required=usePerFile});
 if(ai)renderDrafts();
}
function setRulesMode(){const ai=$('#rules-mode').value==='ai';$('#ai-rules').hidden=!ai;updateAllocationChecklistUI();}
function renderDrafts(){
  const host=$('#draft-preview');if(!host)return;
  const selectedTasks=[...selected].map(id=>tasks.find(t=>t.id===id)).filter(Boolean);
  if(!selectedTasks.length){host.innerHTML='<p class="subtle">Select the unassigned PDF rows to review their AI-generated rules.</p>';$('#review-confirm').checked=false;$('#review-confirm').disabled=true;return;}
  const ready=selectedTasks.every(t=>drafts.get(t.id)?.state==='ready' && drafts.get(t.id)?.rules?.length);
  host.innerHTML=selectedTasks.map(t=>{
    const d=drafts.get(t.id),state=d?.state||'queued';
    const details=state==='ready'?('<ul>'+d.rules.map(r=>'<li><strong>'+safe(r.title)+'</strong> · '+safe(r.type.replaceAll('_',' '))+(r.value?' · '+safe(r.value):'')+
        (r.instructions?'<p class="subtle">'+safe(r.instructions)+'</p>':'')+'</li>').join('')+'</ul>'):
      '<p class="subtle">'+safe(d?.error || (state==='processing'?'DeepSeek is analyzing the PDF…':state==='queued'?'Awaiting AI analysis.':'Awaiting analysis.'))+'</p>';
    return '<details class="draft-card" '+(selectedTasks.length===1?'open':'')+'><summary><strong>'+safe(t.file)+'</strong> · '+safe(state)+' · '+(d?.rules?.length||0)+' proposals</summary>'+
        (d?.summary?'<p>'+safe(d.summary)+'</p>':'')+details+'</details>';
  }).join('');
  $('#review-confirm').disabled=!ready;
  $('#review-confirm').checked=false;
  $('#review-label').textContent=ready?'I reviewed the AI-suggested rules for all selected PDFs.':'Wait for every PDF to finish AI analysis before assigning.';
}
async function loadDrafts(){
  if(role!=='hod')return;
  const data=await api('/api/tasks/rules/drafts');
  const latest=new Map((data.items||[]).map(x=>[x.task_id,x]));
  if(JSON.stringify([...latest])!==JSON.stringify([...drafts])){drafts=latest;renderDrafts();}
}

function renderChecklistTemplates(preferredId=''){
 const select=$('#checklist-template'),keep=preferredId||select.value;
 select.innerHTML='<option value="">Choose a saved checklist</option>'+checklistTemplates.map(x=>`<option value="${safe(x.id)}">${safe(x.name)} · v${x.version}</option>`).join('');
 selectedChecklistId=checklistTemplates.some(x=>x.id===keep)?keep:'';
 select.value=selectedChecklistId;
 const template=checklistTemplates.find(x=>x.id===selectedChecklistId);
 $('#revise-checklist-template').disabled=!template;$('#archive-checklist-template').disabled=!template;
 if(!template){checklistVersions=[];$('#checklist-template-version-select').innerHTML='<option value="">Select a template first</option>';$('#checklist-template-version-select').disabled=true}
 $('#checklist-template-version').textContent=template?`${template.name} · latest version ${template.version} · updates create a new version`: 'Templates and their versions are private to this department.';
}
async function loadChecklistTemplates(preferredId=''){
 if(role!=='hod')return;
 const response=await api('/api/tasks/checklist-templates');
 checklistTemplates=response.items||[];renderChecklistTemplates(preferredId);
}
$('#checklist-template').addEventListener('change',()=>{
 const template=checklistTemplates.find(x=>x.id===$('#checklist-template').value);
 renderChecklistTemplates(template?.id||'');
 if(!template)return;
 void loadChecklistVersions(template.id,template.version);
});
function applyChecklistVersion(version){
 const saved=checklistVersions.find(x=>x.version===Number(version));if(!saved)return;
 $('#manual-rules').replaceChildren();saved.rules.forEach(rule=>addManualRule(rule));
 $('#checklist-template-version').textContent=`${saved.name} · loaded version ${saved.version} · new edits will save as a new version`;
 say(`Loaded ${saved.name} version ${saved.version}. Review the rules before assigning.`);
}
async function loadChecklistVersions(id,preferredVersion){
 const select=$('#checklist-template-version-select');select.disabled=true;select.innerHTML='<option value="">Loading versions…</option>';
 try{
  const response=await api(`/api/tasks/checklist-templates/${encodeURIComponent(id)}/versions`);
  if(id!==selectedChecklistId)return;
  checklistVersions=response.items||[];
  select.innerHTML=checklistVersions.map(x=>`<option value="${x.version}">Version ${x.version} · ${safe(new Date(x.created_at).toLocaleDateString())}</option>`).join('');
  select.disabled=!checklistVersions.length;select.value=String(preferredVersion||checklistVersions[0]?.version||'');
  applyChecklistVersion(select.value);
 }catch(error){select.innerHTML='<option value="">Could not load versions</option>';$('#checklist-template-version').textContent=error.message;say(error.message,true)}
}
$('#checklist-template-version-select').addEventListener('change',event=>applyChecklistVersion(event.target.value));
$('#save-checklist-template').addEventListener('click',async()=>{
 if(role!=='hod')return;
 const name=prompt('Name this department checklist (3–100 characters):');if(name===null)return;
 try{
  const rules=manualRules();
  const template=await api('/api/tasks/checklist-templates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,rules})});
  await loadChecklistTemplates(template.id);await loadChecklistVersions(template.id,template.version);say(`Saved ${template.name} as version 1.`);
 }catch(error){say(error.message,true)}
});
$('#revise-checklist-template').addEventListener('click',async()=>{
 const current=checklistTemplates.find(x=>x.id===selectedChecklistId);if(!current)return;
 if(!confirm(`Save the current checklist as version ${current.version+1} of “${current.name}”? Existing task rules and earlier versions stay unchanged.`))return;
 try{
  const result=await api(`/api/tasks/checklist-templates/${encodeURIComponent(current.id)}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:current.name,rules:manualRules()})});
  await loadChecklistTemplates(result.id);await loadChecklistVersions(result.id,result.version);say(`Saved ${result.name} version ${result.version}.`);
 }catch(error){say(error.message,true)}
});
$('#archive-checklist-template').addEventListener('click',async()=>{
 const current=checklistTemplates.find(x=>x.id===selectedChecklistId);if(!current)return;
 if(!confirm(`Archive “${current.name}”? Existing tasks keep their saved rules.`))return;
 try{
  await api(`/api/tasks/checklist-templates/${encodeURIComponent(current.id)}`,{method:'DELETE'});
  checklistTemplates=checklistTemplates.filter(x=>x.id!==current.id);renderChecklistTemplates();say('Checklist template archived.');
 }catch(error){say(error.message,true)}
});

$('#add-rule').addEventListener('click',()=>addManualRule());
$('#rules-mode').addEventListener('change',setRulesMode);
$('#per-file-toggle').addEventListener('change',()=>{if($('#per-file-toggle').checked)renderPerFileChecklists();updateAllocationChecklistUI()});
$('#per-file-rules').addEventListener('click',event=>{
 const button=event.target.closest('[data-add-per-file-rule]');if(!button)return;
 const card=$(`#per-file-rules [data-task-id="${Number(button.dataset.addPerFileRule)}"]`);
 if(card)addManualRule({},card.querySelector('.task-rules'));
});
addManualRule();setRulesMode();

function actions(t){let html=`<button class="btn secondary smallbtn" data-op="reference" data-id="${t.id}">PDF</button>`;if(role==='staff'&&['assigned','correction_required'].includes(t.state))html+=`<button class="btn smallbtn" data-op="submit" data-id="${t.id}">Submit</button>`;if(role==='hod'&&['assigned','on_hold'].includes(t.state))html+=`<button class="btn secondary smallbtn" data-op="hold" data-id="${t.id}" data-value="${t.state==='assigned'}">${t.state==='assigned'?'Hold':'Release'}</button>`;if(role==='hod'&&t.assigned_staff_id&&!['unassigned','approved'].includes(t.state))html+=`<button class="btn secondary smallbtn" data-op="deadline" data-id="${t.id}">Edit deadline</button>`;if(role==='hod'&&['awaiting_hod','manual_review'].includes(t.state))html+=`<button class="btn smallbtn" data-op="decide" data-id="${t.id}">Decide</button>`;if(t.report?.summary||t.report?.findings?.length)html+=`<button class="btn secondary smallbtn" data-op="report" data-id="${t.id}">Report</button>`;return html;}
function table(){
 const body=$('#tasks');$('#queue-count').textContent=tasks.length+' tasks';
 $('#check-header').hidden=role!=='hod';
 const rows=tasks.map(t=>{
  const due=t.deadline?dueDate(t.deadline):'Not set';
  const expired=Boolean(t.overdue) && t.state!=='approved';
  const dateCell=t.deadline
    ?`<time datetime="${safe(t.deadline)}" title="${safe(due)}">${safe(due)}</time>${expired?'<span class="deadline-overdue">Overdue</span>':'<span class="deadline-scheduled">Scheduled</span>'}`
    :'<span class="subtle">Not set</span>';
  return `<tr class="${expired?'task-overdue':''}">
    <td ${role==='hod'?'':'hidden'}>${role==='hod'&&t.state==='unassigned'?`<input type="checkbox" aria-label="Select ${safe(t.file)}" data-select="${t.id}" ${selected.has(t.id)?'checked':''}>`:''}</td>
    <td><strong title="${safe(t.file)}">${safe(t.file)}</strong><span class="subtle">${safe(t.department)}</span><span class="task-next-action"><strong>Next:</strong> ${safe(t.next_action||'Open the task to review its current status.')}</span>${role==='hod'&&t.state==='unassigned'?'<span class="subtle"> · Optional AI suggestions; manual checklist is ready now.</span>':''}</td>
    <td>${safe(t.assigned_to||'—')}</td>
    <td><span class="state ${safe(t.state)}">${safe(stateLabel(t.state))}</span></td>
    <td class="deadline-cell">${dateCell}</td>
    <td>${t.score===null?'—':safe(t.score)+'%'}</td><td>${actions(t)}</td>
  </tr>`
 }).join('');
 body.innerHTML=rows||'<tr><td colspan="7">No documents to display.</td></tr>';
 $('#selected-ids').textContent=selected.size?`${selected.size} unassigned PDFs selected`:'Select unassigned PDF rows below.';
}

function metrics(){const count=s=>tasks.filter(t=>t.state===s).length;const cards=[['Total tasks',tasks.length],['Working / on hold',count('assigned')+count('on_hold')],['Awaiting review',count('awaiting_hod')+count('manual_review')+count('verifying')],['Approved',count('approved')],['Overdue',tasks.filter(t=>t.overdue).length]];$('#metrics').innerHTML=cards.map(([label,value])=>`<div class="metric"><small>${safe(label)}</small><strong>${value}</strong></div>`).join('');}
async function loadInbox(){const data=await api('/api/tasks/notifications/inbox');$('#unread').textContent=`${data.unread} unread`;$('#inbox').innerHTML=data.items.slice(0,14).map(n=>`<article><strong>${safe(n.text)}</strong><p>${safe(new Date(n.at).toLocaleString())}</p>${n.seen?'':`<button class="ghost" data-notification="${n.id}">Mark read</button>`}</article>`).join('')||'<p class="subtle">No notifications yet.</p>';}
async function loadInsights(){if(!['admin','hod','principal','iqac'].includes(role))return;const data=await api('/api/tasks/insights/summary');$('#oversight').hidden=false;$('#leaderboard').innerHTML=`<table><thead><tr><th>Staff member</th><th>Approved</th><th>In progress</th><th>In review</th><th>Quality</th></tr></thead><tbody>${data.staff.map(x=>`<tr><td>${safe(x.staff)}</td><td>${x.approved}</td><td>${x.active}</td><td>${x.in_review}</td><td>${x.average_quality===null?'—':safe(x.average_quality)+'%'}</td></tr>`).join('')||'<tr><td colspan="5">No approved work yet.</td></tr>'}</tbody></table>`;}
async function loadDigests(){if(role!=='hod')return;try{const d=await api('/api/insights/discussions');$('#discussion-digests').hidden=false;$('#digest-list').innerHTML=d.items.slice(0,5).map(x=>`<article><strong>${safe(x.slot)} · ${safe(x.status)}</strong><p>${safe(x.summary)}</p><small>${x.posts} posts · ${x.comments} comments · ${x.review_flags.length} moderation flags</small>${x.review_flags.length?`<p>Needs HOD review: ${safe(x.review_flags.join('; '))}</p>`:''}</article>`).join('')||'<p class="subtle">No recent department discussions to summarize.</p>';}catch(e){/* Other department HOD has no access. */}}
async function refresh(){try{const data=await api('/api/tasks');tasks=data.items||[];const previous=[...selected].sort((a,b)=>a-b);selected=new Set(previous.filter(id=>tasks.some(t=>t.id===id&&t.state==='unassigned')));const selectionChanged=previous.length!==selected.size;if(selectionChanged&&$('#per-file-toggle').checked)renderPerFileChecklists();updateAllocationChecklistUI();table();metrics();await loadDrafts();await loadInbox();await loadInsights();await loadDigests();if(role==='hod')window.dispatchEvent(new CustomEvent('ncet-hod-tasks-refreshed',{detail:{role:'hod'}}));$('#connection').textContent=`Signed in as ${me.name} · ${role.toUpperCase()} · ${me.department}`;}catch(e){say(e.message,true)}}
async function start(){try{const data=await api('/api/auth/me');me=data.user;role=me.role;csrf=data.csrf;$('#app').hidden=false;$('#heading').textContent=role==='staff'?'My assigned work':role==='hod'?'HOD department dashboard':'Institutional work overview';$('#hod-section').hidden=role!=='hod';$('#metrics').hidden=role==='hod';$('#hod-dashboard').hidden=role!=='hod';$('#admin-ai').hidden=role!=='admin';$('#queue-title').textContent=role==='staff'?'My assigned documents':'Task allocation and review';if(role==='hod'){setMinDeadline();const s=await api('/api/tasks/staff');staff=s.items;$('#staff-id').innerHTML='<option value="">Choose staff</option>'+staff.map(x=>`<option value="${x.id}">${safe(x.name)} (${safe(x.username)})</option>`).join('');await loadChecklistTemplates()};if(role==='admin'){const c=await api('/api/tasks/ai/status');$('#ai-state').textContent=c.configured?`${c.provider} · ${c.model}`:'Not configured'}await refresh();poll=setInterval(refresh,20000);}catch(e){$('#connection').textContent='Please sign in through the NCET workspace to continue.';say(e.message,true);$('#app').hidden=true}}
$('#refresh').addEventListener('click',refresh);
$('#ai-brief').addEventListener('click',async()=>{
  const btn=$('#ai-brief'),host=$('#ai-brief-content');btn.disabled=true;host.textContent='Preparing aggregate workflow suggestions…';
  try {
    const result=await api('/api/tasks/insights/ai-brief',{method:'POST'});
    const article=document.createElement('article'),heading=document.createElement('strong');heading.textContent=result.summary;article.append(heading);
    for(const value of result.recommendations||[]){const p=document.createElement('p');p.textContent=value;article.append(p)}
    const note=document.createElement('small');note.textContent='Advisory recommendations · '+result.model;article.append(note);host.replaceChildren(article);
  } catch(err){host.textContent=err.message;say(err.message,true)}finally{btn.disabled=false}
});

$('#batch-files').addEventListener('change',e=>{$('#selected-count').textContent=`${e.target.files.length} files selected`});
$('#batch-form').addEventListener('submit',async e=>{e.preventDefault();const list=$('#batch-files').files;if(!list.length)return say('Select PDF reference files.',true);if(list.length>50)return say('Maximum 50 PDFs per batch.',true);const total=[...list].reduce((a,f)=>a+f.size,0);if(total>60*1024*1024)return say('Split batches exceeding 60 MB.',true);const b=e.target.querySelector('button[type=submit]');b.disabled=true;try{const form=new FormData();form.set('title',$('#batch-title').value);for(const f of list)form.append('files',f);const result=await api('/api/tasks/batches',{method:'POST',body:form});say(`${result.count} PDFs received.`);e.target.reset();await refresh()}catch(err){say(err.message,true)}finally{b.disabled=false}});
$('#assign-form').addEventListener('submit',async e=>{e.preventDefault();if(!selected.size)return say('Tick the PDF rows you want to assign.',true);const staff_id=Number($('#staff-id').value);if(!staff_id)return say('Choose a staff member.',true);try{
 const deadline=parseDeadline($('#assignment-deadline').value),useAI=$('#rules-mode').value==='ai';
 let rules=[],rules_by_task={};
 if(useAI){if(!$('#review-confirm').checked)return say('Review the AI rule drafts for every selected PDF first.',true)}
 else if($('#per-file-toggle').checked){
  for(const card of $('#per-file-rules').querySelectorAll('.per-file-checklist'))rules_by_task[Number(card.dataset.taskId)]=manualRules(card.querySelector('.task-rules'));
  if(Object.keys(rules_by_task).length!==selected.size)return say('Add and complete a checklist for every selected PDF.',true);
 }else rules=manualRules();
 const ids=[...selected];
 const result=await api('/api/tasks/assign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_ids:ids,staff_id,notes:$('#notes').value,use_generated_rules:useAI,confirmed_task_ids:useAI?ids:[],rules,rules_by_task,deadline})});
 selected.clear();$('#assignment-deadline').value='';
 say(`${result.assigned} assignments sent to staff inbox.`);await refresh();
}catch(err){say(err.message,true)}});

let editingDeadlineTask=null;
$('#deadline-cancel').addEventListener('click',()=>$('#deadline-dialog').close());
$('#deadline-form').addEventListener('submit',async event=>{
 event.preventDefault();
 if(role!=='hod'||editingDeadlineTask===null)return;
 const button=event.target.querySelector('[type=submit]');button.disabled=true;
 try{
  const deadline=parseDeadline($('#edit-deadline').value);
  const result=await api(`/api/tasks/${editingDeadlineTask}/deadline`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({deadline})});
  $('#deadline-dialog').close();editingDeadlineTask=null;
  say(result.changed?'Deadline saved and staff notified.':'No deadline change.');await refresh();
 }catch(err){say(err.message,true)}finally{button.disabled=false}
});
$('#deadline-dialog').addEventListener('close',()=>{editingDeadlineTask=null});

$('#retry-rules').addEventListener('click',async()=>{
  if(!selected.size)return say('Choose one or more unassigned reference PDFs.',true);
  const button=$('#retry-rules');button.disabled=true;
  try{const data=await api('/api/tasks/rules/retry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_ids:[...selected]})});
    say(data.queued+' PDFs queued for optional AI suggestions. A configured provider is required.');await refresh();
  }catch(err){say(err.message,true)}finally{button.disabled=false}
});

$('#ai-form').addEventListener('submit',async e=>{e.preventDefault();if(!confirm('Replace the stored DeepSeek API key?'))return;const key=$('#ai-key').value;try{await api('/api/tasks/ai/key',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})});e.target.reset();say('DeepSeek key securely stored.');const s=await api('/api/tasks/ai/status');$('#ai-state').textContent=s.model}catch(err){say(err.message,true)}});
document.addEventListener('change',e=>{if(e.target.matches('[data-select]')){const id=Number(e.target.dataset.select);e.target.checked?selected.add(id):selected.delete(id);$('#selected-ids').textContent=`${selected.size} unassigned PDFs selected`;if($('#per-file-toggle').checked)renderPerFileChecklists();updateAllocationChecklistUI();renderDrafts()}});
document.addEventListener('click',async e=>{const btn=e.target.closest('[data-op],[data-notification]');if(!btn)return;
try{if(btn.dataset.notification){await api(`/api/tasks/notifications/${Number(btn.dataset.notification)}/read`,{method:'POST'});return refresh()}
const id=Number(btn.dataset.id),t=tasks.find(t=>t.id===id);if(!t)return;
if(btn.dataset.op==='reference'){window.location.href=`/api/tasks/${id}/reference`;return}
if(btn.dataset.op==='report'){const info=t.report||{};const lines=(info.findings||[]).map(x=>`${x.title||x.rule_id}: ${x.result||'uncertain'}${x.issue?' — '+x.issue:''}`).join('\n');const history=(t.decisions||[]).map(x=>`${x.decision}: ${x.note}`).join('\n');return alert(`${info.summary||'Review summary'}\nScore: ${t.score===null?'Awaiting review':t.score+'%'}\n\n${lines||'No individual findings yet.'}\n\nHOD decisions:\n${history||'Pending decision'}`)}
if(btn.dataset.op==='deadline'){
 if(role!=='hod')return;
 editingDeadlineTask=id;$('#deadline-task-name').textContent=t.file;
 setMinDeadline();
 $('#edit-deadline').value=localPickerDate(t.deadline);
 $('#deadline-dialog').showModal();
 return;
}
if(btn.dataset.op==='hold'){await api(`/api/tasks/${id}/hold?hold=${btn.dataset.value}`,{method:'POST'});say('Task status updated.');return refresh()}
if(btn.dataset.op==='submit'){const input=document.createElement('input');input.type='file';input.accept='.pdf,application/pdf';input.onchange=async()=>{const file=input.files?.[0];if(!file)return;const data=new FormData();data.set('file',file);try{await api(`/api/tasks/${id}/submit`,{method:'POST',body:data});say('Submitted. Automated checks will run when available; the HOD can review the result.');refresh()}catch(err){say(err.message,true)}};input.click();return}
if(btn.dataset.op==='decide'){
 reviewingTaskId=id;
 const isApproval=t.state==='awaiting_hod';
 $('#task-review-title').textContent=isApproval?'Approve submitted work':'Request a correction';
 $('#task-review-description').textContent=`${t.file} · ${t.id}. This decision is recorded in the department task history.`;
 $('#task-review-note').value='';$('#task-review-note').placeholder=isApproval?'Explain the approval decision and any follow-up.':'Describe the specific correction the staff member should make.';
 $('#task-review-note-hint').textContent=isApproval?'A clear note helps the department retain a useful record.':'A specific correction is required (at least 10 characters).';
 $('#task-review-error').hidden=true;$('#task-review-submit').textContent=isApproval?'Approve task':'Send correction request';
 $('#task-review-submit').className=isApproval?'btn':'btn orange';$('#task-review-dialog').showModal();$('#task-review-note').focus();return
}
}catch(err){say(err.message,true)}});

$('#task-review-cancel').addEventListener('click',()=>$('#task-review-dialog').close());
$('#task-review-dialog').addEventListener('close',()=>{reviewingTaskId=null;$('#task-review-error').hidden=true});
$('#task-review-form').addEventListener('submit',async event=>{
 event.preventDefault();if(role!=='hod'||reviewingTaskId===null)return;
 const task=tasks.find(item=>item.id===reviewingTaskId);if(!task)return;
 const note=$('#task-review-note').value.trim();
 if(note.length<10){$('#task-review-error').textContent='Enter a review note with at least 10 characters.';$('#task-review-error').hidden=false;$('#task-review-note').focus();return}
 const button=$('#task-review-submit');button.disabled=true;
 try{
  const decision=task.state==='awaiting_hod'?'approved':'needs_correction';
  await api(`/api/tasks/${task.id}/decide`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,note})});
  $('#task-review-dialog').close();say(decision==='approved'?'Task approved and recorded.':'Correction request sent to staff.');await refresh();
 }catch(error){$('#task-review-error').textContent=error.message;$('#task-review-error').hidden=false}
 finally{button.disabled=false}
});
start();})();
