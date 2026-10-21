"""Student portal browser smoke for accurate department labels and requests."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

ROOT=Path(__file__).resolve().parents[1]
HTML=ROOT/'static'/'student-portal.html'
JS=ROOT/'static'/'student-portal.js'

MOCK=r"""() => {
 let signed=false,submitted=false;
 window.__requests=[];
 window.fetch=async(input,options={})=>{
  const url=String(input),method=options.method||'GET';let body={},status=200;
  if(url==='/api/auth/me'){
   if(!signed){status=401;body={detail:'Please sign in'};}
   else body={user:{role:'student',department:'Computer Science & Engineering'},csrf:'student-csrf'};
  }else if(url==='/api/auth/login'){
   signed=true;body={user:{role:'student'},csrf:'student-csrf'};
  }else if(url==='/api/bca/me')body={usn:'1NC24CSE901',branch:'Computer Science & Engineering',semester:5,must_change_password:false};
  else if(url.startsWith('/api/bca/cases?'))body={items:submitted?[{reference:'NCET-BCA-CSE001',subject:'CSE lab schedule review',category:'academics',status:'submitted',created_at:new Date().toISOString()}]:[],counts:{submitted:submitted?1:0,in_review:0,resolved:0,closed:0},all_total:submitted?1:0,total:submitted?1:0,has_more:false};
  else if(url==='/api/bca/showcase/me'&&method==='GET')body={usn:'1NC24CSE901',full_name:'Student CSE',department:'Computer Science & Engineering',mobile:'',email:'',about:'',interests:[],projects:[],skills:[],social_links:{},certificates:[],published:false,photo_available:false};
  else if(url==='/api/bca/cases'&&method==='POST'){
   const data=JSON.parse(options.body);window.__requests.push(data);submitted=true;body={reference:'NCET-BCA-CSE001',status:'submitted'};
  }else if(url==='/api/bca/cases/NCET-BCA-CSE001')body={reference:'NCET-BCA-CSE001',subject:'CSE lab schedule review',category:'academics',description:'Please review the updated Computer Science laboratory schedule.',status:'submitted',messages:[],created_at:new Date().toISOString(),updated_at:new Date().toISOString()};
  else{status=404;body={detail:'Unsupported mock request '+method+' '+url};}
  return new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
 };
}"""

def main():
 with sync_playwright() as playwright:
  browser=launch_chromium(playwright,headless=True)
  page=browser.new_page(viewport={'width':390,'height':844})
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  html=HTML.read_text(encoding='utf-8')
  html=html.replace('<link rel="stylesheet" href="/static/bca.css">','<style>'+ (ROOT/'static'/'bca.css').read_text(encoding='utf-8')+'</style>')
  html=html.replace('<link rel="stylesheet" href="/static/experience.css">','<style>'+ (ROOT/'static'/'experience.css').read_text(encoding='utf-8')+'</style>')
  html=html.replace('<link rel="stylesheet" href="/static/notifications.css">','')
  html=html.replace('<link rel="stylesheet" href="/static/responsive-upgrade.css?v=20261017">','<style>'+ (ROOT/'static'/'responsive-upgrade.css').read_text(encoding='utf-8')+'</style>')
  html=html.replace('<link rel="stylesheet" href="/static/student-redesign.css?v=20261017b">','<style>'+ (ROOT/'static'/'student-redesign.css').read_text(encoding='utf-8')+'</style>')
  html=html.replace('<link rel="stylesheet" href="/static/ncet-brand-system.css?v=20261017">','<style>'+ (ROOT/'static'/'ncet-brand-system.css').read_text(encoding='utf-8')+'</style>')
  html=html.replace('<script src="/static/student-portal.js?v=20261021-department" defer></script><script src="/static/notifications.js" defer></script><script src="/static/institutional-ui.js?v=20261017d" defer></script>','')
  page.set_content(html)
  page.evaluate(MOCK)
  page.add_script_tag(content=JS.read_text(encoding='utf-8'))
  page.locator('#login-usn').fill('1nc24cse901')
  page.locator('#login-password').fill('local-only-password')
  page.locator('#login-form button[type=submit]').click()
  page.locator('#workspace:not(.hidden)').wait_for()
  assert page.locator('#who').inner_text()=='1NC24CSE901 · Computer Science & Engineering · Semester 5'
  page.locator('[data-student-tab=profile]').click()
  assert page.locator('#showcase-dept').input_value()=='Computer Science & Engineering'
  page.locator('[data-student-tab=requests]').click()
  page.locator('#case-subject').fill('CSE lab schedule review')
  page.locator('#case-description').fill('Please review the updated Computer Science laboratory schedule.')
  page.locator('#new-case button[type=submit]').click()
  page.wait_for_function('window.__requests.length===1')
  assert 'your department HOD' in page.locator('#alert').inner_text()
  assert 'CSE lab schedule review' in page.locator('#case-list').inner_text()
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
  assert not errors,errors
  browser.close()
 print('STUDENT PORTAL UI PASS: CSE department labels, request submission, mobile layout')

if __name__=='__main__':main()
