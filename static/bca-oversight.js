'use strict';
const get=id=>document.getElementById(id);
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function refresh(){
 try{
  const res=await fetch('/api/bca/oversight',{credentials:'same-origin',cache:'no-store'});
  if(!res.ok)throw Error(res.status===403?'BCA HOD or Principal access required.':'Please sign in with your faculty account.');
  const data=await res.json();
  get('overview').classList.remove('hidden');get('oversight-error').textContent='';
  get('cases-total').textContent=data.cases_total+' requests in total';
  get('case-counts').innerHTML=Object.entries(data.cases_by_status).map(([name,count])=>'<p><strong>'+safe(count)+'</strong> '+safe(name.replace('_',' '))+'</p>').join('');
  get('projects-total').textContent=data.projects_total+' projects in total';
  get('project-counts').innerHTML='<p>'+safe(data.projects_open)+' open · '+safe(data.projects_closed)+' completed</p>';
  if(data.view==='department'){
   get('hod-manage').classList.remove('hidden');get('hod-recent').classList.remove('hidden');
   get('recent-cases').innerHTML=(data.cases||[]).map(c=>'<p><strong>'+safe(c.subject)+'</strong> · '+safe(c.status)+'</p>').join('')||'<p>No complaints have been submitted.</p>';
  }
 }catch(e){get('oversight-error').textContent=e.message;}
}
refresh();
