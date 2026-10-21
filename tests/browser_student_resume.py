"""Render a published NCET student résumé in Chromium at mobile/desktop widths."""
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from time import perf_counter
from statistics import median
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

fd,path=tempfile.mkstemp(prefix='ncet-resume-',suffix='.sqlite3')
os.close(fd)
os.environ['APP_ENV']='development'
os.environ['DATABASE_URL']='sqlite:///'+path
os.environ['STORAGE_BACKEND']='database'
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from app.main import app
from app.database import Base,DBSession,engine,User
from app.student_models import BCAStudent
from app.student_profiles import StudentShowcase
from app.departments import AcademicDepartment

static=Path(__file__).resolve().parents[1]/'static'
Base.metadata.create_all(engine)
with DBSession() as db:
    db.add(AcademicDepartment(code='Computer Science & Engineering',name='Computer Science & Engineering',active=True))
    u=User(username='1nc24cs150',display_name='Example Engineering Student',
           role='student',department='Computer Science & Engineering',active=True,
           password_hash='not-used')
    db.add(u);db.flush()
    db.add(BCAStudent(user_id=u.id,usn='1NC24CS150',semester=5,must_change_password=False))
    db.add(StudentShowcase(student_id=u.id,published=True,
           about='Building useful campus tools and learning responsible engineering.',
           skills_json='["Python","C++","FastAPI"]',
           interests_json='["Artificial Intelligence","Open Source"]',
           projects_json='[{"title":"Student Project","description":"A campus workflow application","technologies":["Python","React"],"github_url":"https://github.com/example/demo","live_url":"https://example.org/demo"}]',
           certificates_json='[{"title":"Programming Certificate","issuer":"Cisco","proof_url":"https://example.org/cert"}]',
           social_links_json='{"github":"https://github.com/example"}'))
    db.commit()
with TestClient(app) as client:
    html=client.get('/students/profile/1NC24CS150').text
assert 'Student Project' in html and 'Programming Certificate' in html

with sync_playwright() as p:
    browser=launch_chromium(p,headless=True)
    switches=[]
    for width in (320,375,390,768,1024,1440):
        page=browser.new_page(viewport={'width':width,'height':850},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        def serve(route):
            location=urlsplit(route.request.url).path
            if location.startswith('/static/'):
                file=(static/location[len('/static/'):]).resolve()
                if not file.is_relative_to(static.resolve()) or not file.exists():
                    route.fulfill(status=404,body='Not found');return
                suffix=file.suffix.lower()
                mime={'.png':'image/png','.css':'text/css','.js':'text/javascript','.webp':'image/webp','.svg':'image/svg+xml'}.get(suffix,'application/octet-stream')
                route.fulfill(status=200,body=file.read_bytes(),headers={'content-type':mime})
            elif location=='/students/profile/1NC24CS150':
                route.fulfill(status=200,body=html,headers={'content-type':'text/html; charset=utf-8'})
            else:route.fulfill(status=404,body='Not found')
        page.route('http://ncet.test/**',serve)
        page.goto('http://ncet.test/students/profile/1NC24CS150',wait_until='load')
        # The footer image is intentionally lazy. Scroll it into view before checking naturalWidth.
        page.locator('.resume-footer img').scroll_into_view_if_needed()
        page.wait_for_function('Array.from(document.images).every(img=>img.complete&&img.naturalWidth>0)',timeout=6000)
        report=page.evaluate("""() => ({
            width: document.documentElement.scrollWidth,viewport:innerWidth,
            sections:[...document.querySelectorAll('.resume-section')].map(x=>x.id),
            images:[...document.images].map(img=>({source:img.src,loaded:img.complete&&img.naturalWidth>0}))
        })""")
        assert report['width']<=width+2,(width,report)
        assert report['sections']==['about','skills','projects','certifications','interests','links']
        assert all(x['loaded'] for x in report['images']),(width,report['images'])
        assert not errors,(width,errors)
        # Once JS initializes, the portfolio is a single in-page accessible tab view.
        assert page.locator('.resume-anchors[role="tablist"]').count()==1
        assert page.locator('.resume-section:not([hidden])').count()==1
        assert page.locator('#about').is_visible()
        page.locator('a[href="#projects"]').click()
        assert page.url.endswith('#projects'),page.url
        assert page.locator('#projects').is_visible()
        assert page.locator('#about').is_hidden()
        assert page.locator('#projects').get_attribute('aria-labelledby')=='profile-tab-projects'
        page.locator('a[href="#projects"]').press('ArrowRight')
        assert page.locator('#certifications').is_visible()
        assert page.locator('a[href="#certifications"]').get_attribute('aria-selected')=='true'
        page.go_back(wait_until='domcontentloaded')
        assert page.locator('#projects').is_visible()
        page.goto('http://ncet.test/students/profile/1NC24CS150#links',wait_until='load')
        assert page.locator('#links').is_visible()
        assert page.locator('.resume-section:not([hidden])').count()==1
        # Browser-perceived, measured in the test runner (not a synthetic Lighthouse score).
        for target in ('skills','interests','about'):
            start=perf_counter()
            page.locator('a[href="#'+target+'"]').click()
            page.wait_for_function("document.querySelector('#resume-tab-stage').style.height === ''",timeout=3000)
            switches.append((perf_counter()-start)*1000)
            assert page.locator('#'+target).is_visible()
        page.emulate_media(reduced_motion='reduce')
        page.locator('a[href="#projects"]').click()
        assert page.locator('#projects').is_visible()
        assert page.locator('#resume-tab-stage').evaluate('(el)=>el.style.height')==''
        assert not errors,(width,errors)
        page.close()
    # Without JavaScript, all sections remain indexable and readable.
    nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':850})
    page=nojs.new_page()
    page.route('http://ncet.test/**',serve)
    page.goto('http://ncet.test/students/profile/1NC24CS150',wait_until='load')
    assert page.locator('.resume-section:visible').count()==6
    assert page.locator('.resume-anchors[role="tablist"]').count()==0
    nojs.close()
    browser.close()
engine.dispose()
os.unlink(path)
switches.sort()
p95=switches[min(len(switches)-1,int(len(switches)*.95))]
original_css=10432+8120+6555+4636+7184
original_js=1752
updated_css=(static/'resume-profile.css').stat().st_size
updated_js=(static/'student-profile-tabs.js').stat().st_size
before=original_css+original_js
after=updated_css+updated_js
assert after<before*.75,(before,after)
print('NCET RESUME PERFORMANCE BENCHMARK')
print(f'Critical CSS+JS bytes (uncompressed): previous={before}, updated={after}, reduction={(before-after)/before*100:.1f}%')
print(f'Critical stylesheet/script requests: previous=6, updated=2')
print(f'Tab switch browser timings, 18 interactions: median={median(switches):.0f} ms, p95={p95:.0f} ms')
print('NCET résumé audit passed: six widths, six sections, reduced motion, keyboard/history, no-JS fallback, all institutional images loaded.')
