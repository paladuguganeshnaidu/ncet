"""End-to-end browser: actual FastAPI, SQLite, OCR-capable worker, no OpenRouter calls."""
import os
import subprocess
import tempfile
import time
from pathlib import Path
import fitz
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parents[1]
PORT='8779'
BASE='http://127.0.0.1:'+PORT

def pdf_blob(heading):
    doc=fitz.open();page=doc.new_page();page.insert_text((65,80),heading,fontsize=17)
    page.insert_text((65,110),'NCET Faculty Verification Test',fontsize=14)
    raw=doc.tobytes();doc.close();return raw

with tempfile.TemporaryDirectory() as td:
    env=os.environ.copy();env.update({'PYTHONPATH':str(ROOT),'APP_ENV':'development','DATABASE_URL':'sqlite:///'+str(Path(td)/'browser.sqlite3'),
          'STORAGE_BACKEND':'database','PUBLIC_ORIGIN':BASE,
          **{f'NCET_BOOTSTRAP_{role.upper()}_PASSWORD':'BrowserTest2026Secure!' for role in ('admin','hod','staff','principal','iqac')}})
    subprocess.check_call(['alembic','upgrade','head'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
    subprocess.check_call(['python','-m','app.bootstrap'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
    server=subprocess.Popen(['uvicorn','app.main:app','--host','127.0.0.1','--port',PORT],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    worker=subprocess.Popen(['python','-m','app.worker'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
        page=context.new_page();page.set_default_timeout(12000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/app');page.get_by_text('Welcome to NCMS VerifyFlow').wait_for()
        page.screenshot(path=str(ROOT/'tests/screen-login.png'),full_page=True)
        def signin(username):
            page.locator('#login-user').fill(username)
            page.locator('#login-pass').fill('BrowserTest2026Secure!')
            page.locator('#login-form button[type=submit]').click()
            page.locator('.sidebar-brand').wait_for()
        def signout():page.locator('[data-action=logout]').click();page.locator('#login-user').wait_for()
        signin('admin')
        page.locator('[data-page=users]').first.click()
        page.get_by_text('Provisioned accounts').wait_for()
        assert page.get_by_text('NCET staff').first.is_visible()
        page.locator('[data-page=integrations]').first.click()
        page.get_by_text('AI model configuration').wait_for()
        assert page.get_by_text('API key not yet configured').is_visible()
        page.screenshot(path=str(ROOT/'tests/screen-admin.png'),full_page=True)
        signout();signin('hod')
        page.locator('[data-page=rules]').first.click()
        page.locator('[data-action=add-rule]').click()
        page.locator('.rule-entry [name=title]').fill('Executive summary requirement')
        page.locator('.rule-entry [name=value]').fill('Executive Summary')
        page.locator('#rule-form button[type=submit]').click()
        page.get_by_text('Version 1', exact=True).wait_for()
        page.screenshot(path=str(ROOT/'tests/screen-hod-rules.png'),full_page=True)
        signout();signin('staff')
        page.locator('[data-page=upload]').first.click()
        page.locator('#doc-title').fill('NCET Annual Faculty Report')
        page.locator('#doc-category').select_option('Academic Audit')
        page.locator('#doc-desc').fill('Prepared for the automated document verification workflow.')
        page.locator('#file-input').set_input_files({'name':'faculty-report.pdf','mimeType':'application/pdf','buffer':pdf_blob('Incorrect introduction')})
        page.locator('#submit-document button[type=submit]').click()
        page.get_by_text('NCET Annual Faculty Report').first.wait_for()
        page.reload()
        page.locator('.sidebar-brand').wait_for()
        page.wait_for_function("() => document.body.innerText.includes('Needs correction')",timeout=25000)
        page.locator('[data-open]').first.click()
        page.locator('[data-action=verification]').click()
        page.get_by_text('Verification report',exact=True).first.wait_for()
        assert page.get_by_text('Required heading not found',exact=False).count()>=1
        page.screenshot(path=str(ROOT/'tests/screen-report.png'),full_page=True)
        page.locator('[data-action=close-modal]').first.click()
        page.locator('[data-open]').first.click()
        page.locator('[data-action=resubmit]').click()
        page.locator('#revision-note').fill('Added the mandatory Executive Summary heading and corrected content.')
        page.locator('#revision-file').set_input_files({'name':'revised.pdf','mimeType':'application/pdf','buffer':pdf_blob('Executive Summary')})
        page.locator('#revision-form button[type=submit]').click()
        page.wait_for_function("() => document.body.innerText.includes('Manual review')",timeout=25000)
        page.screenshot(path=str(ROOT/'tests/screen-staff.png'),full_page=True)
        signout();signin('hod')
        page.locator('[data-page=documents]').first.click()
        page.locator('[data-open]').first.click()
        page.locator('[data-action=review][data-decision=approved]').click()
        page.locator('#review-note').fill('Heading checked, final human verification complete.')
        page.locator('#review-form button[type=submit]').click()
        page.get_by_text('Document approved',exact=True).first.wait_for()
        page.screenshot(path=str(ROOT/'tests/screen-hod.png'),full_page=True)
        signout();signin('principal')
        page.locator('[data-page=documents]').first.click()
        page.get_by_text('NCET Annual Faculty Report').first.wait_for()
        assert page.locator('[data-page=users]').count()==0
        page.screenshot(path=str(ROOT/'tests/screen-principal.png'),full_page=True)
        signout();signin('iqac')
        page.locator('[data-page=documents]').first.click()
        page.get_by_text('NCET Annual Faculty Report').first.wait_for()
        page.screenshot(path=str(ROOT/'tests/screen-iqac.png'),full_page=True)
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        mp=mobile.new_page();mp.goto(BASE+'/app');mp.get_by_text('Welcome to NCMS VerifyFlow').wait_for()
        mp.screenshot(path=str(ROOT/'tests/screen-mobile.png'),full_page=True)
        assert not errors,errors
        print('REAL BROWSER E2E PASS: admin, rules, staff upload, verification, revise, HOD approval, principal, IQAC, mobile; JS errors=',errors)
        browser.close()
    finally:
        for proc in (worker,server):
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill()
