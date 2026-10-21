'use strict';
const $=id=>document.getElementById(id);const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let csrf='',role='',selected=null,rosterRows=[],departments=[],removalAllowed=false;
const selectedStudentUsns=new Set();let removalPreview=null,removalBusy=false;
function show(id,yes){$(id).classList.toggle('hidden',!yes)}
function notify(t,error=false){$('alert').textContent=t;$('alert').className=error?'error':'success'}
function setRoleCopy(branch=''){const footer=document.querySelector('footer .footer-content > div > p.small');const directory=document.querySelector('footer .footer-content > div:nth-child(2) a[href="/students"]');if(role==='admin'){document.title='Student Administration | NCET VerifyFlow';document.querySelector('.brand small').textContent='All departments';document.querySelector('.shell-head .eyebrow').textContent='STUDENT SERVICES · ALL DEPARTMENTS';document.querySelector('.shell-head p.muted').textContent='Manage enrollment and student records across academic departments.';footer.textContent='Nagarjuna College of Engineering and Technology · Student administration';directory.textContent='Student directory';return;}document.title='Department Student Desk | NCET VerifyFlow';document.querySelector('.brand small').textContent=branch||'Department desk';document.querySelector('.shell-head .eyebrow').textContent='STUDENT SERVICES · '+(branch||'YOUR DEPARTMENT').toUpperCase();document.querySelector('.shell-head p.muted').textContent='Manage enrollment and student records for your department.';footer.textContent='Nagarjuna College of Engineering and Technology · Department student portal';directory.textContent='Student directory';}
async function api(url,options={}){const headers={...(options.headers||{})};if(options.method&&options.method!=='GET')headers['X-CSRF-Token']=csrf;const r=await fetch(url,{credentials:'same-origin',cache:'no-store',...options,headers});const data=await r.json().catch(()=>({}));if(!r.ok){let d=data.detail;if(Array.isArray(d))d=d.map(e=>e.msg).join(', ');throw new Error(typeof d==='string'?d:'Request unsuccessful.')}return data}
function download(name,content){const blob=new Blob([content],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');const u=URL.createObjectURL(blob);a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000)}
const csvCell=t=>'"'+String(t).replaceAll('"','""')+'"';
$('template').addEventListener('click',()=>download('NCET_student_import_template.csv','usn,full_name,branch,semester\r\n'));
async function init(){try{let r=await api('/api/auth/me');csrf=r.csrf;role=r.user.role;if(!['staff','hod','admin'].includes(role))throw Error('Not authorized');if(role==='admin'){setRoleCopy();await loadDepartments();show('admin-departments',true)}else{const catalog=(await api('/api/academic/departments')).items;const assigned=catalog.find(d=>d.code.toLowerCase()===String(r.user.department||'').toLowerCase()||d.name.toLowerCase()===String(r.user.department||'').toLowerCase());if(!assigned)throw Error('Your assigned department is not active in the academic catalog.');departments=[assigned];setRoleCopy(assigned.name);renderBranchPicker()}removalAllowed=role==='admin'||role==='hod'&&departments[0]?.name==='Computer Applications';await loadRoster();$('staff-name').textContent=r.user.name;show('desk',true);show('student-removal-panel',removalAllowed);$('permanent-delete-option').disabled=role!=='admin';if(role==='hod'){show('hod-queue',true);$('management-complaints').hidden=false;await loadCases()}}catch(e){show('denied',true);notify(e.message||'Sign in with an authorized department account.',true)}}
function downloadCredentials(x){const rows=['usn,full_name,branch,semester,temporary_password',...x.credentials.map(c=>[c.usn,c.name,c.branch,c.semester,c.temporary_password].map(csvCell).join(','))];download('NCET_ONETIME_credentials.csv',rows.join('\r\n')+'\r\n');}
function renderRoster(){
 const term=$('roster-search').value.trim().toLowerCase();
 const rows=rosterRows.filter(x=>($('show-disabled-students').checked||x.active)&&(x.name.toLowerCase().includes(term)||x.usn.toLowerCase().includes(term)||(x.branch_name||x.branch||'').toLowerCase().includes(term)));
 $('roster-count').textContent=rows.length+' visible of '+rosterRows.length+' enrolled students';
 $('selected-student-count').textContent=selectedStudentUsns.size+' selected';
 $('review-student-removal').disabled=!selectedStudentUsns.size||removalBusy;
 const opts=student=>role==='admin'
   ? '<select name="branch" required>'+(!student.branch||!departments.some(d=>d.code===student.branch)?'<option value="" selected disabled>Select a department</option>':'')+departments.map(d=>'<option value="'+esc(d.code)+'" '+(student.branch===d.code?'selected':'')+' '+(!d.active&&student.branch!==d.code?'disabled':'')+'>'+esc(d.name)+(d.active?'':' (inactive)')+'</option>').join('')+'</select>'
   : (student.branch?'<input type="hidden" name="branch" value="'+esc(student.branch)+'">':'')+'<span class="small muted">'+esc(student.branch_name||student.branch||'Department not set')+'</span>';
 $('roster').innerHTML=rows.length?rows.map(x=>`<div class="entry"><div class="row">${removalAllowed?'<label class="select-student-label"><input type="checkbox" class="select-student" data-usn="'+esc(x.usn)+'" aria-label="Select '+esc(x.name)+' ('+esc(x.usn)+')" '+(selectedStudentUsns.has(x.usn)?'checked':'')+'> Select</label>':''}<strong>${esc(x.name)}</strong><span class="small muted">${esc(x.usn)} · ${esc(x.branch_name||x.branch||'Department not set')} · Semester ${esc(x.semester)} · ${x.active?'Active':'Disabled'}</span></div><details><summary>Edit student details</summary><form class="edit-student-form" data-usn="${esc(x.usn)}"><label>Full name <input name="full_name" value="${esc(x.name==='Registration pending'?'':x.name)}" minlength="3" maxlength="130" required></label><label>Branch ${opts(x)}</label><label>Semester <input name="semester" type="number" min="1" max="8" value="${esc(x.semester)}" required></label><button class="btn" type="submit">Save details</button></form></details></div>`).join(''):'<p class="muted">'+(term?'No students match your search.':'No students enrolled yet.')+'</p>';
}

async function loadRoster(){
 $('roster-count').textContent='Loading students…';
 let response=await api('/api/bca/students');
 rosterRows=response.items;
 selectedStudentUsns.clear();
 discardRemovalPreview();
 renderRoster();
}

$('import-form').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);let btn=e.target.querySelector('button[type=submit]');btn.disabled=true;try{let file=f.get('file');let endpoint=file?.name.toLowerCase().endsWith('.xlsx')?'/api/bca/students/import-excel':'/api/bca/students/import';let x=await api(endpoint,{method:'POST',body:f});downloadCredentials(x);notify(`${x.created} students enrolled. The one-time credentials file has been downloaded. Store it securely.`);e.target.reset();await loadRoster()}catch(err){notify(err.message,true)}finally{btn.disabled=false}});
async function loadCases(){try{let r=await api('/api/bca/cases');$('cases').innerHTML=r.items.length?r.items.map(x=>`<button class="entry" type="button" data-case="${esc(x.reference)}"><span class="row"><strong>${esc(x.subject)}</strong><span class="status ${esc(x.status)}">${esc(x.status.replaceAll('_',' '))}</span></span><span class="muted small">${esc(x.reference)} · ${esc(x.category)}</span></button>`).join(''):'<p class="muted">No cases awaiting review.</p>';for(const b of $('cases').querySelectorAll('[data-case]'))b.addEventListener('click',()=>openCase(b.dataset.case))}catch(err){notify(err.message,true)}}
async function openCase(ref){try{const d=await api('/api/bca/cases/'+encodeURIComponent(ref));selected=ref;show('selected-case',true);$('case-title').textContent=d.subject;$('case-details').innerHTML=`<p class="muted small">${esc(d.reference)} · ${esc(d.student?.name)} · ${esc(d.student?.usn)} · ${esc(d.status.replaceAll('_',' '))}</p><p>${esc(d.description)}</p><h3>Replies</h3>${d.messages.map(m=>`<div class="thread"><strong>${esc(m.author)}</strong><span class="muted small"> ${esc(new Date(m.created_at).toLocaleString())}</span><p>${esc(m.body)}</p></div>`).join('')||'<p class="muted">No replies yet.</p>'}`;show('case-update',d.status!=='closed');show('message-form',d.status!=='closed');$('selected-case').scrollIntoView({behavior:'smooth'})}catch(err){notify(err.message,true)}}
$('close-case').addEventListener('click',()=>{selected=null;show('selected-case',false)});
$('case-update').addEventListener('submit',async e=>{e.preventDefault();if(!selected)return;const body=Object.fromEntries(new FormData(e.target));try{await api('/api/bca/cases/'+encodeURIComponent(selected)+'/status',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});notify('Case status updated.');e.target.reset();await openCase(selected);await loadCases()}catch(err){notify(err.message,true)}});
$('message-form').addEventListener('submit',async e=>{e.preventDefault();if(!selected)return;try{await api('/api/bca/cases/'+encodeURIComponent(selected)+'/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:new FormData(e.target).get('message')})});e.target.reset();notify('Reply sent.');await openCase(selected)}catch(err){notify(err.message,true)}});
$('logout').addEventListener('click',async()=>{try{await api('/api/auth/logout',{method:'POST'})}catch{}location.replace('/app')});
init();


function renderBranchPicker(){
 const el=$('enroll-branch');const current=el.value;
 el.innerHTML='<option value="">Choose a department</option>'+departments.filter(x=>x.active).map(x=>'<option value="'+esc(x.code)+'">'+esc(x.name)+'</option>').join('');
 if(departments.some(x=>x.code===current&&x.active))el.value=current;
 else if(role!=='admin'&&departments.length===1)el.value=departments[0].code;
 renderRoster();
}
function renderDepartments(){
 $('department-list').innerHTML=departments.map(d=>'<form class="department-edit-form" data-code="'+esc(d.code)+'"><label>Department name <input name="name" value="'+esc(d.name)+'" minlength="2" maxlength="160" required></label><span class="small muted">Internal ID: '+esc(d.code)+'</span><label class="department-toggle"><input type="checkbox" name="active" '+(d.active?'checked':'')+'> Active for registration</label><button type="submit" class="btn">Save department</button></form>').join('');
}
async function loadDepartments(){
 const r=await api('/api/academic/departments');
 departments=r.items;
 renderBranchPicker();
 if(role==='admin')renderDepartments();
}
$('new-department-form').addEventListener('submit',async e=>{
 e.preventDefault();if(role!=='admin')return;
 const btn=e.target.querySelector('[type=submit]');btn.disabled=true;
 try{await api('/api/admin/departments',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:new FormData(e.target).get('name')})});
  e.target.reset();await loadDepartments();notify('Department added successfully.')}catch(err){notify(err.message,true)}finally{btn.disabled=false}
});
$('department-list').addEventListener('submit',async e=>{
 const form=e.target.closest('.department-edit-form');if(!form)return;
 e.preventDefault();if(role!=='admin')return;
 const btn=form.querySelector('[type=submit]');btn.disabled=true;
 const body={name:new FormData(form).get('name'),active:form.querySelector('[name=active]').checked};
 try{await api('/api/admin/departments/'+encodeURIComponent(form.dataset.code),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  await loadDepartments();await loadRoster();notify('Department settings updated. Existing students retain their records.')}
 catch(err){notify(err.message,true)}finally{btn.disabled=false}
});
async function enrollRecords(records,form){
 const btn=form.querySelector('[type=submit]');btn.disabled=true;btn.setAttribute('aria-busy','true');
 try{const result=await api('/api/bca/students/enroll',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({students:records})});
  downloadCredentials(result);notify(result.created+' students registered. Store downloaded credentials securely.');
  form.reset();await loadRoster()}
 catch(err){notify(err.message,true)}finally{btn.disabled=false;btn.removeAttribute('aria-busy')}
}
$('quick-enroll').addEventListener('submit',async e=>{
 e.preventDefault();const values=new FormData(e.target);
 const row={usn:String(values.get('usn')||'').trim(),full_name:String(values.get('full_name')||'').trim(),
  branch:String(values.get('branch')||''),semester:Number(values.get('semester'))};
 if(!row.usn||!row.full_name||!row.branch||!Number.isInteger(row.semester)||row.semester<1||row.semester>8)
  return notify('USN, Name, Branch and Sem are all required.',true);
 await enrollRecords([row],e.target);
});
$('batch-enroll').addEventListener('submit',async e=>{
 e.preventDefault();
 const lines=$('enroll-list').value.split(/[\n;]+/).map(x=>x.trim()).filter(Boolean);
 if(!lines.length||lines.length>100)return notify('Enter 1–100 student rows.',true);
 const rows=[];
 for(const line of lines){
  const p=line.split(',').map(x=>x.trim());
  if(p.length!==4||p.some(x=>!x))return notify('Every row requires USN, Name, Branch, Sem.',true);
  const semester=Number(p[3]);
  if(!Number.isInteger(semester)||semester<1||semester>8)return notify('Semester must be between 1 and 8.',true);
  rows.push({usn:p[0],full_name:p[1],branch:p[2],semester});
 }
 await enrollRecords(rows,e.target);
});
$('roster').addEventListener('submit',async e=>{
 const form=e.target.closest('.edit-student-form');if(!form)return;e.preventDefault();
 const data=new FormData(form);
 try{
  await api('/api/bca/students/'+encodeURIComponent(form.dataset.usn),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({full_name:data.get('full_name'),branch:data.get('branch'),semester:Number(data.get('semester'))})});
  notify('Student details updated. If a public profile existed, the student must republish it.');await loadRoster();
 }catch(err){notify(err.message,true)}
});

$('roster-search').addEventListener('input',renderRoster);

$('show-disabled-students').addEventListener('change',renderRoster);

function discardRemovalPreview(){
 removalPreview=null;
 $('student-removal-review').classList.add('hidden');
 $('student-removal-confirm-form').reset();
 $('student-removal-alert').classList.add('hidden');
 $('student-removal-alert').textContent='';
}
function selectionChanged(){
 discardRemovalPreview();
 $('selected-student-count').textContent=selectedStudentUsns.size+' selected';
 $('review-student-removal').disabled=selectedStudentUsns.size===0;
 $('student-removal-selection').textContent=selectedStudentUsns.size
   ?[...selectedStudentUsns].sort().join(', '):'No students selected.';
}
function removalError(message){
 $('student-removal-alert').textContent=message;
 $('student-removal-alert').classList.remove('hidden');
 $('student-removal-alert').scrollIntoView({block:'nearest'});
}
$('roster').addEventListener('change',event=>{
 const checkbox=event.target.closest('.select-student');
 if(!checkbox)return;
 const usn=checkbox.dataset.usn;
 if(checkbox.checked){
   if(selectedStudentUsns.size>=50){checkbox.checked=false;return removalError('Select at most 50 students per action.')}
   selectedStudentUsns.add(usn);
 }else selectedStudentUsns.delete(usn);
 selectionChanged();
});
$('select-visible-students').addEventListener('click',()=>{
 const visible=[...$('roster').querySelectorAll('.select-student')];
 for(const checkbox of visible){
   if(selectedStudentUsns.size>=50)break;
   checkbox.checked=true;selectedStudentUsns.add(checkbox.dataset.usn);
 }
 selectionChanged();
 if(visible.length>50)removalError('Selected the first 50 visible students. Use a smaller search filter for other accounts.');
});
$('clear-student-selection').addEventListener('click',()=>{
 selectedStudentUsns.clear();for(const box of $('roster').querySelectorAll('.select-student'))box.checked=false;
 selectionChanged();
});
$('removal-mode').addEventListener('change',()=>discardRemovalPreview());
$('cancel-student-removal').addEventListener('click',discardRemovalPreview);

$('review-student-removal').addEventListener('click',async()=>{
 if(removalBusy||selectedStudentUsns.size===0)return;
 const mode=$('removal-mode').value,usns=[...selectedStudentUsns].sort();
 removalBusy=true;$('review-student-removal').disabled=true;
 try{
  const preview=await api('/api/bca/students/removal/preview',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({usns,mode})
  });
  if(preview.mode!==mode||preview.items.length!==usns.length)throw Error('Invalid preview response.');
  removalPreview={preview,usns,mode};
  $('removal-phrase').textContent=preview.confirmation;
  $('removal-review-summary').innerHTML='<p><strong>'+preview.count+' accounts selected</strong> · '+preview.blocked+' deletion blockers</p>'+
    '<p class="small muted">'+esc(preview.note)+'</p>'+
    '<ul class="removal-impact-list">'+preview.items.map(item=>'<li><strong>'+esc(item.name)+'</strong> · '+esc(item.usn)+
      ' · '+esc(item.department)+' · '+(item.active?'Active':'Already inactive')+
      (item.published?' · Public profile will be hidden':'')+
      (item.deletion_blockers.length?' <span class="removal-block">BLOCKED: '+esc(item.deletion_blockers.join(', '))+'</span>':'')+'</li>').join('')+'</ul>';
  $('student-removal-confirm-form').reset();
  $('removal-backup-label').classList.toggle('hidden',mode!=='delete');
  $('execute-student-removal').disabled=!!preview.blocked;
  $('execute-student-removal').textContent=mode==='delete'?'Permanently delete selected':'Remove selected access';
  $('student-removal-review').classList.remove('hidden');
  $('student-removal-alert').classList.add('hidden');
  $('student-removal-review').scrollIntoView({block:'nearest'});
 }catch(err){discardRemovalPreview();removalError(err.message)}
 finally{removalBusy=false;$('review-student-removal').disabled=selectedStudentUsns.size===0;}
});
$('student-removal-confirm-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!removalPreview||removalBusy)return;
 const {preview,usns,mode}=removalPreview,form=event.target,data=new FormData(form);
 const payload={mode,usns,preview_token:preview.preview_token,
    confirmation:String(data.get('confirmation')||''),
    current_password:String(data.get('current_password')||''),
    reason:String(data.get('reason')||'').trim(),
    backup_confirmed:data.get('backup_confirmed')==='on'};
 if(payload.confirmation!==preview.confirmation)return removalError('Type the exact confirmation phrase.');
 if(mode==='delete'&&!payload.backup_confirmed)return removalError('Verify a recoverable offline backup before deletion.');
 removalBusy=true;$('execute-student-removal').disabled=true;
 try{
  const result=await api('/api/bca/students/removal/execute',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  selectedStudentUsns.clear();discardRemovalPreview();
  if(result.action==='disable')$('show-disabled-students').checked=false;
  await loadRoster();
  notify(result.affected+' student account'+(result.affected===1?'':'s')+' '+(result.action==='delete'?'permanently deleted.':'disabled; sessions revoked and public portfolios hidden. Historical records retained.'));
 }catch(err){removalError(err.message);if(err.message.includes('Preview again')||err.message.includes('Selection or record state'))discardRemovalPreview();}
 finally{removalBusy=false;$('execute-student-removal').disabled=false;form.querySelector('[name=current_password]').value='';}
});

$('export-roster').addEventListener('click',()=>{
 if(!rosterRows.length)return notify('No enrolled students to export.',true);
 const safe=v=>{const str=String(v??'');return csvCell(['=','+','-','@','\t','\r'].includes(str.charAt(0))?"'"+str:str)};
 const data=['usn,full_name,branch,semester,active',...rosterRows.map(x=>[x.usn,x.name,x.branch_name||x.branch||'Department not set',x.semester,x.active?'yes':'no'].map(safe).join(','))].join('\r\n')+'\r\n';
 download('NCET_student_roster_without_passwords.csv',data);
 notify('Enrollment roster downloaded. No passwords or private contact details were included.');
});
