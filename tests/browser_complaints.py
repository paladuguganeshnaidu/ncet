"""Lightweight complaints dashboard smoke: private cases, server filters and mobile usability."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

BASE=Path(__file__).resolve().parents[1]/'static'

MOCK=r"""() => {
 const items=[
 {reference:'NCET-BCA-CASE001',subject:'Lab class arrangements',category:'facilities',status:'submitted',created_at:'2026-10-17T07:00:00Z',updated_at:'2026-10-17T07:00:00Z',student:{name:'Student One',usn:'1NC24BCA001'}},
 {reference:'NCET-BCA-CASE002',subject:'Semester examination',category:'examinations',status:'in_review',created_at:'2026-10-16T07:00:00Z',updated_at:'2026-10-17T08:00:00Z',student:{name:'Student Two',usn:'1NC24BCA002'}},
 {reference:'NCET-BCA-CASE003',subject:'Fees receipt',category:'fees',status:'resolved',created_at:'2026-10-15T07:00:00Z',updated_at:'2026-10-16T07:00:00Z',student:{name:'Student Three',usn:'1NC24BCA003'}}
 ];
 window.__messages=[];
 window.fetch=async(input,opts={})=>{
  const url=String(input),method=opts.method||'GET';
  let body={},status=200;
  if(url==='/api/auth/me')body={user:{role:'hod',department:window.__department||'Computer Applications'},csrf:'test-csrf'};
  else if(url.startsWith('/api/bca/cases?')){
   const params=new URL(url,'https://ncet.test').searchParams;
   let selected=items.filter(x=>(params.get('status')==='all'||!params.get('status')||x.status===params.get('status')) &&
        (params.get('category')==='all'||!params.get('category')||x.category===params.get('category')) &&
        (!params.get('search')||(x.subject+x.reference).toLowerCase().includes(params.get('search').toLowerCase())) &&
        (params.get('attention')!=='awaiting_reply'||['submitted','in_review'].includes(x.status)) &&
        (params.get('attention')!=='older_than_7d'));
   if(params.get('sort')==='oldest')selected.reverse();
   const offset=Number(params.get('offset')||0),limit=Number(params.get('limit')||20);
   body={items:selected.slice(offset,offset+limit),offset,limit,total:selected.length,all_total:items.length,has_more:offset+limit<selected.length,
     counts:{submitted:items.filter(x=>x.status==='submitted').length,in_review:items.filter(x=>x.status==='in_review').length,
             resolved:items.filter(x=>x.status==='resolved').length,closed:0},
     attention_counts:{awaiting_reply:items.filter(x=>x.status==='submitted'||x.status==='in_review').length,older_than_7d:0},
     categories:{facilities:1,fees:1,examinations:1}};
  }else if(url.startsWith('/api/bca/cases/') && method==='GET'){
   const ref=decodeURIComponent(url.split('/').pop()),item=items.find(x=>x.reference===ref);
   body={...item,description:'Confidential student request. <img src=x onerror=alert(1)>',messages:[{author:'Student',body:'Please help <svg onload=alert(1)>',created_at:item.created_at}]};
  }else if(url.startsWith('/api/bca/cases/') && (method==='PATCH'||method==='POST')){
   window.__messages.push({url,method,body:opts.body});
   if(method==='PATCH'){const item=items.find(x=>x.reference===url.split('/')[4]);if(item)item.status=JSON.parse(opts.body).status;}
   body={ok:true};
  }else{status=404;body={detail:'Unsupported mock request '+url};}
  return new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
 };
}"""

def main():
 with sync_playwright() as playwright:
  browser=launch_chromium(playwright,headless=True)
  for department in ('Computer Applications','Computer Science & Engineering'):
   for width in (320,390,768,1366):
    page=browser.new_page(viewport={'width':width,'height':850})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    html=(BASE/'complaints-dashboard.html').read_text(encoding='utf-8')
    html=html.replace('<link rel="stylesheet" href="/static/bca.css">','<style>'+ (BASE/'bca.css').read_text(encoding='utf-8')+'</style>')
    html=html.replace('<link rel="stylesheet" href="/static/complaints-dashboard.css?v=20261018a">','<style>'+ (BASE/'complaints-dashboard.css').read_text(encoding='utf-8')+'</style>')
    html=html.replace('<script defer src="/static/complaints-dashboard.js?v=20261021-department"></script>','')
   page.set_content(html)
   page.evaluate('(department)=>window.__department=department',department)
   page.evaluate(MOCK)
   page.add_script_tag(content=(BASE/'complaints-dashboard.js').read_text(encoding='utf-8'))
   page.locator('#kpi-all').get_by_text('3',exact=True).wait_for()
   assert page.locator('#department-enrollment').is_visible()==(department=='Computer Applications')
   assert page.locator('#case-results .complaint-row').count()==3
   assert page.locator('#kpi-submitted').inner_text()=='1'
   assert page.locator('#priority-count-waiting').inner_text()=='2'
   assert page.locator('#case-status-bars .case-bar-item').count()==4
   page.locator('#priority-waiting').click()
   page.wait_for_function("document.querySelectorAll('#case-results .complaint-row').length===2")
   assert page.locator('#priority-waiting').get_attribute('aria-pressed')=='true'
   page.locator('#reset-filters').click()
   page.wait_for_function("document.querySelectorAll('#case-results .complaint-row').length===3")
   page.locator('[data-status=submitted]').click()
   page.wait_for_function("document.querySelectorAll('#case-results .complaint-row').length===1")
   assert page.locator('#case-results .complaint-row').count()==1
   assert 'Lab class' in page.locator('#case-results').inner_text()
   page.locator('#reset-filters').click()
   page.locator('#case-results .complaint-row').first.wait_for()
   page.locator('#case-filters [name=search]').fill('Semester')
   page.wait_for_function("document.querySelectorAll('#case-results .complaint-row').length===1 && document.querySelector('#case-results').textContent.includes('Semester examination')")
   page.locator('#case-results .complaint-row').click()
   assert page.locator('#case-dialog').is_visible()
   page.get_by_text('Confidential student request.',exact=False).wait_for()
   assert page.locator('#detail-content img, #detail-content svg').count()==0
   page.locator('#close-dialog').click()
   assert page.locator('#case-dialog').is_hidden()
   page.locator('#case-filters [name=search]').fill('')
   page.wait_for_function("document.querySelectorAll('#case-results .complaint-row').length===3")
   page.locator('#case-results .complaint-row').first.click()
   page.locator('#reply-case-form [name=message]').fill('We are reviewing your request.')
   page.locator('#reply-case-form button[type=submit]').click()
   page.wait_for_function('window.__messages.length===1')
   page.get_by_text('Saved successfully. The student has been notified.',exact=True).wait_for()
   assert page.locator('#case-dialog').is_visible()
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'),(department,width)
   assert not errors,errors
   page.close()
  browser.close()
 print('DEPARTMENT COMPLAINT DASHBOARD UI PASS: BCA/CSE roles, desktop/mobile, search, status, details, reply')

if __name__=='__main__':main()
