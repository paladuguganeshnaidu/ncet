"""Run with: python tests/browser_smoke.py (uses temporary test-only DB and port)."""
import os,subprocess,time,tempfile,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).parents[1]
with tempfile.TemporaryDirectory() as td:
 env=os.environ.copy()
 env.update({'PYTHONPATH':str(root),'DATABASE_URL':'sqlite:///'+str(Path(td)/'test.sqlite3'),
             'NCET_BOOTSTRAP_STAFF_PASSWORD':'BrowserSecurePass123!',
             'NCET_BOOTSTRAP_HOD_PASSWORD':'BrowserSecurePass123!',
             'NCET_BOOTSTRAP_PRINCIPAL_PASSWORD':'BrowserSecurePass123!',
             'NCET_BOOTSTRAP_IQAC_PASSWORD':'BrowserSecurePass123!',
             'PUBLIC_ORIGIN':'http://127.0.0.1:8778','APP_ENV':'development'})
 subprocess.check_call(['alembic','upgrade','head'],cwd=root,env=env,stdout=subprocess.DEVNULL)
 subprocess.check_call(['python','-m','app.bootstrap'],cwd=root,env=env,stdout=subprocess.DEVNULL)
 server=subprocess.Popen(['uvicorn','app.main:app','--host','127.0.0.1','--port','8778'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  time.sleep(1.5)
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
   context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
   page=context.new_page();page.set_default_timeout(7000);errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   def signin(username):
    page.locator('#login-user').fill(username)
    page.locator('#login-pass').fill('BrowserSecurePass123!')
    page.locator('#login-form button[type=submit]').click()
    page.locator('.sidebar-brand').wait_for()
   page.goto('http://127.0.0.1:8778/app')
   assert page.get_by_text('Welcome to NCMS VerifyFlow').is_visible()
   page.screenshot(path=str(root/'tests/login.png'),full_page=True)
   signin('staff')
   assert page.get_by_text('Faculty submissions').is_visible()
   page.locator('[data-page=upload]').first.click()
   page.locator('#doc-title').fill('End-to-end browser document')
   page.locator('#doc-category').select_option('Academic Audit')
   page.locator('#doc-desc').fill('A full end to end security tested document to be reviewed.')
   page.locator('#file-input').set_input_files({'name':'audit.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.7\nValid enough for signature test\n%%EOF'})
   page.locator('#submit-document button[type=submit]').click()
   page.get_by_text('End-to-end browser document').first.wait_for()
   page.screenshot(path=str(root/'tests/staff.png'),full_page=True)
   page.locator('[data-action=logout]').click()
   signin('hod')
   page.locator('[data-page=documents]').first.click()
   page.get_by_text('End-to-end browser document').first.wait_for()
   page.locator('[data-open]').first.click()
   page.locator('[data-action=review][data-decision=approved]').click()
   page.locator('#review-note').fill('Reviewed and approved by HOD.')
   page.locator('#review-form button[type=submit]').click()
   page.get_by_text('Document approved',exact=True).first.wait_for()
   page.screenshot(path=str(root/'tests/hod.png'),full_page=True)
   page.locator('[data-action=logout]').click()
   signin('principal')
   page.locator('[data-page=documents]').first.click()
   page.get_by_text('End-to-end browser document').first.wait_for()
   page.screenshot(path=str(root/'tests/principal.png'),full_page=True)
   page.locator('[data-page=users]').first.click()
   page.get_by_text('Provisioned accounts').wait_for()
   page.locator('[data-page=audit]').first.click()
   page.get_by_text('Security audit',exact=True).first.wait_for()
   page.locator('[data-action=logout]').click()
   signin('iqac')
   page.locator('[data-page=documents]').first.click()
   page.get_by_text('End-to-end browser document').first.wait_for()
   mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
   mp=mobile.new_page();mp.goto('http://127.0.0.1:8778/app')
   mp.get_by_text('Welcome to NCMS VerifyFlow').wait_for()
   mp.screenshot(path=str(root/'tests/mobile.png'),full_page=True)
   print('BROWSER WORKFLOW PASSED | JS ERRORS:',errors)
   assert not errors,errors
   browser.close()
 finally:
  server.terminate();server.wait(timeout=10)
