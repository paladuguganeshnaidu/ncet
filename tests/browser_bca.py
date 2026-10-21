"""Chromium smoke checks for BCA public/student/member-only pages.

UI checks use static resources with mocked API responses. Authorization is
tested separately in FastAPI integration tests; no real production accounts used.
"""
from pathlib import Path
import base64
import re
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'


def load_page(page, html_file, script=None, mock_denied=False):
    page.goto('about:blank')  # reset the previous page's global JavaScript scope
    html = (STATIC / html_file).read_text(encoding='utf-8')
    for asset in ('ncet-brand.svg','ngi-brand.svg','naac-brand.svg',
                  'ncet-official.webp','ncms-emblem.webp','ngi-logo.webp'):
        image = STATIC / asset
        if image.is_file():
            mime = 'image/svg+xml' if asset.endswith('.svg') else ('image/png' if asset.endswith('.png') else 'image/webp')
            uri = 'data:' + mime + ';base64,' + base64.b64encode(image.read_bytes()).decode()
            html = re.sub(r'/static/' + re.escape(asset) + r'(?:\?v=[a-zA-Z0-9_-]+)?', lambda _match: uri, html)
    for css in ('bca.css', 'community.css','experience.css','responsive-upgrade.css',
                'student-redesign.css','ncet-brand-system.css','homepage-polish.css','institutional-ui.css','home-revamp.css'):
        file=STATIC/css
        if not file.is_file():continue
        html=re.sub(r'<link rel="stylesheet" href="/static/' + re.escape(css) + r'(?:\?v=[a-zA-Z0-9_-]+)?"\s*/?>',
                    lambda _m: '<style>' + file.read_text(encoding='utf-8') + '</style>', html)
    html = re.sub(r'<script src="/static/[^"]+" defer></script>', '', html)
    page.set_content(html, wait_until='load')
    if mock_denied:
        page.evaluate("""() => {
          window.fetch = async (url) => new Response(
            JSON.stringify({detail: 'Not authorized'}),
            {status:401, headers:{'Content-Type':'application/json'}}
          );
        }""")
    if script:
        page.add_script_tag(content=(STATIC / script).read_text(encoding='utf-8'))


def main():
    with sync_playwright() as pw:
        browser = launch_chromium(pw,headless=True)
        errors = []
        desktop = browser.new_page(viewport={'width':1440,'height':900})
        desktop.on('pageerror', lambda e: errors.append(str(e)))
        desktop.set_default_timeout(8000)

        load_page(desktop, 'public-home.html', 'public-home.js')
        assert desktop.locator('h1').inner_text().startswith('Your campus.')
        assert desktop.locator('.identity-crest').evaluate('(img) => img.naturalWidth') > 0
        assert desktop.locator('.film-frames').count() == 0
        assert desktop.locator('#toggle-animation').count() == 0
        assert desktop.locator('.service-card').count() == 3
        assert desktop.locator('.service-card[href="/students/directory"]').count() == 1
        desktop.locator('#homepage-search').fill('1NC24BCA001')
        assert desktop.locator('form[role="search"]').get_attribute('action') == '/students/directory'
        desktop.locator('.guide-grid summary').first.click()
        assert desktop.locator('.guide-grid details').first.get_attribute('open') == ''
        assert desktop.locator('header a[href="/students"]').inner_text().strip() == 'Student Portal'
        assert desktop.locator('header a[href="/app"]').count() == 0
        assert desktop.locator('header small').count() == 1

        load_page(desktop, 'student-services.html')
        assert 'EVERYTHING STUDENTS NEED' in desktop.locator('main').inner_text().upper()
        assert 'RAISE ACADEMIC REQUESTS' in desktop.locator('main').inner_text().upper()
        assert desktop.locator('a[href="/students/portal"]').count() > 0

        load_page(desktop,'student-directory.html')
        desktop.evaluate("""() => {
          window.fetch=async() => new Response(JSON.stringify({items:[
            {name:'Published CSE Student',usn:'1NC24BCA388',
             department:'Computer Science & Engineering',skills:['Python','HTML']}
          ]}),{status:200,headers:{'Content-Type':'application/json'}});
        }""")
        desktop.add_script_tag(content=(STATIC/'student-directory.js').read_text(encoding='utf-8'))
        desktop.get_by_text('Published CSE Student').wait_for()
        assert 'Computer Science & Engineering' in desktop.locator('#directory-results').inner_text()
        assert desktop.locator('a[href="/students/profile/1NC24BCA388"]').count()==2
        assert 'private@example.org' not in desktop.locator('main').inner_text()
        desktop.locator('#student-search').fill('1NC24BCA388')
        desktop.locator('#search-profiles button[type=submit]').click()
        desktop.get_by_text('Showing 1 published profiles').wait_for()

        load_page(desktop, 'student-portal.html','student-portal.js',mock_denied=True)
        assert desktop.locator('#showcase-form').count() == 1
        assert desktop.locator('#showcase-mobile[type=tel]').count()==1
        assert desktop.locator('#showcase-public[type=checkbox]').count()==1
        desktop.locator('#login-usn').fill('1NC24BCA001')
        desktop.locator('#login-password').fill('incorrect-pass')
        desktop.locator('#login-form button[type=submit]').click()
        desktop.get_by_text('Not authorized').first.wait_for()
        assert desktop.locator('#login-password').input_value() == ''

        load_page(desktop, 'bca-management.html','bca-management.js',mock_denied=True)
        desktop.locator('#denied').wait_for(state='visible')
        assert desktop.locator('#quick-enroll').count()==1
        assert desktop.locator('input[accept*=".xlsx"]').count()==1

        load_page(desktop,'community.html','community.js',mock_denied=True)
        desktop.get_by_text('Sign in required').first.wait_for()
        assert errors == [], errors

        mobile = browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        mobile.on('pageerror', lambda e: errors.append(str(e)))
        for name in ('public-home.html','student-services.html','student-directory.html'):
            load_page(mobile,name)
            assert mobile.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'),name
        browser.close()
        assert errors == [], errors


if __name__ == '__main__':
    main()
    print('BCA Chromium smoke checks passed: public pages, logo animation, private access, mobile')
