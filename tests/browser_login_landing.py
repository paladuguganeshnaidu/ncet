"""Browser regression: successful faculty login navigates to /tasks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'static'
BASE='http://ncet.test'
ROLES=('admin','hod','staff','principal','iqac')


def main():
    with sync_playwright() as playwright:
        browser=launch_chromium(playwright,headless=True)
        errors=[]
        page=browser.new_page(viewport={'width':1280,'height':850})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_default_timeout(10000)
        state={'role':None,'authenticated':False}

        def serve(route):
            from urllib.parse import urlsplit
            request=route.request
            path=urlsplit(request.url).path
            if path=='/app':
                state['authenticated']=False
                route.fulfill(status=200,body=(STATIC/'index.html').read_text(encoding='utf-8'),
                              headers={'content-type':'text/html; charset=utf-8'})
            elif path=='/api/auth/me':
                if state['authenticated']:
                    role=state['role']
                    route.fulfill(status=200,json={'csrf':'browser-test-csrf','user':{
                        'role':role,'name':'NCET '+role,'department':'Computer Science & Engineering'}})
                else:route.fulfill(status=401,json={'detail':'Please sign in'})
            elif path=='/api/auth/login':
                import json
                body=json.loads(request.post_data or '{}')
                assert body.get('username')==state['role']
                state['authenticated']=True
                route.fulfill(status=200,json={'csrf':'browser-test-csrf','user':{
                    'role':state['role'],'name':'NCET '+state['role'],
                    'department':'Computer Science & Engineering'}})
            elif path=='/tasks':
                assert state['authenticated'], 'The task route was reached without a completed login.'
                route.fulfill(status=200,body='<!doctype html><html><body><h1>Task management</h1></body></html>',
                              headers={'content-type':'text/html; charset=utf-8'})
            elif path.startswith('/static/'):
                asset=(STATIC/path.removeprefix('/static/')).resolve()
                if asset.is_relative_to(STATIC.resolve()) and asset.is_file():
                    mime={'.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml',
                          '.webp':'image/webp','.png':'image/png'}.get(asset.suffix.lower(),'application/octet-stream')
                    route.fulfill(status=200,body=asset.read_bytes(),headers={'content-type':mime})
                else:route.fulfill(status=404,body='Not found')
            else:route.fulfill(status=404,body='Not found')

        page.route(BASE+'/**',serve)
        for role in ROLES:
            state['role']=role
            page.goto(BASE+'/app')
            page.get_by_text('Welcome to NCET VerifyFlow').wait_for()
            page.locator('#login-user').fill(role)
            page.locator('#login-pass').fill('temporary-test-password')
            page.locator('#login-form button[type=submit]').click()
            page.wait_for_url(BASE+'/tasks')
            assert page.get_by_role('heading',name='Task management').is_visible(),role

        assert not errors,errors
        browser.close()
        print('Faculty login landing passed for admin, HOD, staff, principal and IQAC.')


if __name__=='__main__':main()
