"""Frontend-only browser smoke with deterministic mock responses (real API is separately tested)."""
import base64
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
ROOT=Path(__file__).parents[1]
MOCK=r'''() => {
  const users=['admin','hod','staff','principal','iqac'];
  let signed=null;let csrf='fake_csrf';let rulebook={version:0,rules:[],history:[]};let docs=[];
  const now=()=>new Date().toISOString();
  window.fetch=async(url,opts={})=>{
    const path=String(url),method=opts.method||'GET';let response={ok:true},status=200;
    if(path==='/api/auth/me'){if(!signed){status=401;response={detail:'Please sign in'};}else response={user:{role:signed,name:'NCET '+signed,department:'Computer Science & Engineering',username:signed,id:users.indexOf(signed)+1},csrf};}
    else if(path==='/api/auth/login'){
      const req=JSON.parse(opts.body);if(!users.includes(req.username)||(req.role&&req.username!==req.role)){status=401;response={detail:'Invalid credentials'};}
      else{signed=req.username;response={user:{role:signed,name:'NCET '+signed,department:'Computer Science & Engineering',username:signed,id:users.indexOf(signed)+1},csrf};}
    }else if(path==='/api/auth/logout'){signed=null;}
    else if(path.startsWith('/api/documents?')){const view=docs.filter(d=>signed==='staff'||signed==='hod'||d.status==='approved');response={items:view,total:view.length};}
    else if(path==='/api/documents'&&method==='POST'){const form=opts.body,file=form.get('file');docs.push({id:'NCET-2026-BROWSER',title:form.get('title'),category:form.get('category'),year:form.get('year'),description:form.get('description'),department:'Computer Science & Engineering',status:'verifying',version:1,submitted:now(),author:'NCET staff',fileName:file.name,fileSize:file.size,hasLocalFile:true,history:[{kind:'submitted',note:'Verification queued',at:now(),by:'NCET staff'}],verification:{status:'queued',revision:1}});}
    else if(path==='/api/rules'){if(method==='PUT'){const b=JSON.parse(opts.body);rulebook={version:rulebook.version+1,rules:b.rules,history:[{version:rulebook.version+1,created:now()}]};response={ok:true,version:rulebook.version};}else response=rulebook;}
    else if(path.endsWith('/verification')){const d=docs[0];response={document_id:d.id,revision:1,policy_version:rulebook.version,status:d.status,report:{status:'needs_correction',rule_count:1,page_count:1,ai_used:false,summary:'Manual check needed',findings:[{rule_id:'heading',title:'Executive Summary',result:'issue',source:'deterministic',location:'Page 1',issue:'Required heading not found',correction:'Add the heading',confidence:1}]}};}
    else if(path.endsWith('/review')&&method==='POST'){const b=JSON.parse(opts.body);docs[0].status=b.decision;docs[0].history.push({kind:b.decision,by:'NCET hod',note:b.note,at:now()});}
    else if(path.endsWith('/resubmit')&&method==='POST'){docs[0].version++;docs[0].status='manual_review';}
    else if(path==='/api/users'){response={items:users.map((u,i)=>({id:i+1,username:u,name:'NCET '+u,role:u,department:'Computer Science & Engineering',active:true}))};}
    else if(path==='/api/academic/departments'){response={items:['Computer Applications','Commerce','Management','Science'].map((name,i)=>({code:'dept-'+i,name,active:true}))};}
    else if(path==='/api/admin/integrations'){response={configured:false,provider:null,model:null,deepseek_configured:false,openrouter_configured:false,key_stored:false};}
    else if(path==='/api/audit'){response={items:[]};}
    else if(path==='/api/auth/change-password'){response={ok:true};}
    else{status=404;response={detail:'Unknown request: '+path};}
    return new Response(JSON.stringify(response),{status,headers:{'content-type':'application/json'}});
  };
}'''
with sync_playwright() as p:
    browser=launch_chromium(p,headless=True)
    context=browser.new_context(viewport={'width':1440,'height':900})
    page=context.new_page();page.set_default_timeout(11000)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1" /></head><body><div id="app"></div></body></html>')
    css=(ROOT/'static/styles.css').read_text()+'\n'+(ROOT/'static/enterprise.css').read_text()
    js=(ROOT/'static/app.js').read_text()
    for suffix in ('ncet-brand.svg','ngi-brand.svg','naac-brand.svg','ncms-logo.webp','ncms-emblem.webp','ngi-logo.webp','ncet-crest.webp'):
        asset=ROOT/'static'/suffix
        if asset.exists():
            mime='image/svg+xml' if asset.suffix=='.svg' else 'image/webp'
            data=f'data:{mime};base64,'+base64.b64encode(asset.read_bytes()).decode()
            js=js.replace('/static/'+suffix,data)
    page.evaluate('(css)=>{const s=document.createElement("style");s.textContent=css;document.head.appendChild(s)}',css)
    page.evaluate(MOCK)
    page.add_script_tag(content=js)
    page.get_by_text('Welcome to NCET VerifyFlow').wait_for()
    assert page.locator('.roles .role-option').count()==0
    page.screenshot(path=str(ROOT/'tests/ui-login.png'),full_page=True)
    page.locator('#login-user').fill('unknown-user');page.locator('#login-pass').fill('wrong-password')
    page.locator('#login-form button[type=submit]').click()
    page.get_by_text('Invalid credentials').wait_for()
    assert page.locator('#login-user').input_value()=='unknown-user'
    assert page.locator('#login-pass').input_value()==''

    def signin(u):
        page.locator('#login-user').fill(u);page.locator('#login-pass').fill('test-pass')
        page.locator('#login-form button[type=submit]').click();page.locator('.sidebar-brand').wait_for()
    def signout():page.locator('[data-action=logout]').click();page.locator('#login-user').wait_for()
    signin('admin')
    page.locator('[data-page=users]').first.click();page.get_by_text('Provisioned accounts').wait_for()
    for department in ('Computer Applications','Commerce','Management','Science'):
        assert department in page.locator('#acc-dept').inner_text(),department
    assert 'Mechanical Engineering' not in page.locator('#acc-dept').inner_text()

    page.locator('[data-page=integrations]').first.click();page.get_by_text('DeepSeek AI settings').wait_for();assert page.locator('#deepseek-key').count()==1;assert page.get_by_text('New OpenRouter API key').count()==0
    page.screenshot(path=str(ROOT/'tests/ui-admin.png'),full_page=True)
    signout();signin('hod')
    # The CSE HOD can open the department-scoped complaints dashboard but not BCA oversight.
    assert page.locator('a[href="/bca/oversight"]').count()==0
    assert page.locator('a[href="/complaints"]').count()==1
    assert page.locator('a[href="/complaints"]').inner_text()=='Complaint management'
    assert page.locator('a[href="/tasks"]').count()==1
    page.locator('[data-page=rules]').first.click();page.locator('[data-action=add-rule]').click()
    page.locator('.rule-entry [name=title]').fill('Executive summary heading')
    page.locator('.rule-entry [name=value]').fill('Executive Summary')
    page.locator('#rule-form button[type=submit]').click();page.get_by_text('Version 1',exact=True).wait_for()
    page.screenshot(path=str(ROOT/'tests/ui-rules.png'),full_page=True)
    signout();signin('staff')
    page.locator('[data-page=upload]').first.click()
    page.locator('#doc-title').fill('NCET Annual Faculty Report')
    page.locator('#doc-category').select_option('Academic Audit')
    assert re.fullmatch(r'20\d{2}-\d{2}',page.locator('#doc-year').input_value())
    page.locator('#doc-desc').fill('Academic year department faculty annual documentation submission.')
    page.locator('#file-input').set_input_files({'name':'document.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.7\nTEST ONLY\n%%EOF'})
    page.locator('#submit-document button[type=submit]').click()
    page.get_by_text('NCET Annual Faculty Report').first.wait_for()
    page.locator('[data-open]').first.click();page.locator('[data-action=verification]').click()
    page.get_by_text('Verification report',exact=True).first.wait_for()
    page.screenshot(path=str(ROOT/'tests/ui-report.png'),full_page=True)
    page.locator('[data-action=close-modal]').first.click()
    signout();signin('principal')
    assert page.locator('a[href="/bca/oversight"]').count()==1
    assert page.locator('[data-page=users]').count()==0
    signout();signin('iqac')
    assert page.locator('[data-page=users]').count()==0
    mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    mp=mobile.new_page();mp.set_content('<html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/></head><body><div id="app"></div></body></html>')
    mp.evaluate('(css)=>{const s=document.createElement("style");s.textContent=css;document.head.appendChild(s)}',css)
    mp.evaluate(MOCK);mp.add_script_tag(content=js)
    mp.get_by_text('Welcome to NCET VerifyFlow').wait_for()
    mp.screenshot(path=str(ROOT/'tests/ui-mobile.png'),full_page=True)
    assert not errors,errors
    print('UI SMOKE PASS: 5 roles, Super Admin, HOD rules, Staff upload, verification report, Principal/IQAC isolation, mobile. JS errors:',errors)
    browser.close()
