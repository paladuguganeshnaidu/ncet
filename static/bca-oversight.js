'use strict';
const get=id=>document.getElementById(id);
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function refresh(){
 try{
  const res=await fetch('/api/bca/oversight',{credentials:'same-origin',cache:'no-store'});
  if(!res.ok)throw Error(res.status===403?'This oversight view is not available for your department.':'Please sign in with your faculty account.');
  const data=await res.json();
  get('overview').classList.remove('hidden');get('oversight-error').textContent='';
  if(data.view==='department'){
   get('page-title').textContent='Department oversight';
   get('page-description').textContent='Computer Applications student request and project status';
   get('privacy-note').textContent='This view is scoped to the Computer Applications department. Other HODs can use their department task and complaint dashboards.';
  }
  get('cases-total').textContent=data.cases_total+' requests in total';
  get('case-counts').innerHTML=Object.entries(data.cases_by_status).map(([name,count])=>'<p><strong>'+safe(count)+'</strong> '+safe(name.replace('_',' '))+'</p>').join('');
  get('projects-total').textContent=data.projects_total+' projects in total';
  get('project-counts').innerHTML='<p>'+safe(data.projects_open)+' open · '+safe(data.projects_closed)+' completed</p>';
  if(data.view==='department'){
   get('hod-manage').classList.remove('hidden');get('hod-recent').classList.remove('hidden');
   get('recent-cases').innerHTML=(data.cases||[]).map(c=>'<p><strong>'+safe(c.subject)+'</strong> · '+safe(c.status)+'</p>').join('')||'<p>No complaints have been submitted.</p>';
  }else{
   get('department-summary').classList.remove('hidden');
   get('department-rows').innerHTML=(data.departments||[]).map(row=>'<tr><th scope="row">'+safe(row.department)+'</th><td>'+safe(row.cases_total)+'</td><td>'+safe((row.cases_by_status?.submitted||0)+(row.cases_by_status?.in_review||0))+'</td><td>'+safe(row.projects_total)+'</td><td>'+safe(row.projects_open)+'</td></tr>').join('')||'<tr><td colspan="5">No department requests or projects have been recorded.</td></tr>';
  }
 }catch(e){get('oversight-error').textContent=e.message;}
}
refresh();
