"""NCET full institutional UI regression: viewport, campus, real loaders, menu and reduced motion."""
import os
import time
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

BASE=os.getenv('NCET_BASE_URL','http://127.0.0.1:8000').rstrip('/')
PAGES=['/','/students','/students/directory','/students/portal','/about','/app']
WIDTHS=(320,375,390,768,1024,1440)

with sync_playwright() as p:
    browser=launch_chromium(p,headless=True)
    for width in WIDTHS:
        page=browser.new_page(viewport={'width':width,'height':880},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        for route in PAGES:
            result=page.goto(BASE+route,wait_until='domcontentloaded',timeout=25000)
            assert result and result.status==200,(route,width,result.status if result else None)
            page.locator('body').wait_for(state='visible')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(route,width,page.evaluate('document.documentElement.scrollWidth'))
            assert page.locator('link[href*="institutional-ui.css"]').count()==1,(route,width)
            assert page.locator('script[src*="institutional-ui.js"]').count()==1,(route,width)
            assert not errors,(route,width,errors)
            errors.clear()
        page.goto(BASE+'/',wait_until='domcontentloaded')
        page.locator('.identity-crest').wait_for(state='visible')
        assert page.locator('.identity-crest').evaluate('(el)=>el.complete && el.naturalWidth>0'),width
        assert page.locator('.identity-center').evaluate('(el)=>getComputedStyle(el).backgroundColor')=='rgb(255, 255, 255)'
        assert page.locator('.ncet-campus-photo img').count()==1,width
        assert page.locator('.ncet-impact-metrics .institutional-counter').count()==4,width
        assert page.locator('.footer-credits a').count()==3,width
        if width<=700:
            page.locator('.ncet-menu-toggle').wait_for(state='visible')
            menu=page.locator('.ncet-menu-toggle')
            assert menu.get_attribute('aria-expanded')=='false'
            menu.click()
            assert menu.get_attribute('aria-expanded')=='true'
            assert page.locator('#ncet-mobile-links a[href="/students"]').is_visible()
            page.keyboard.press('Escape')
            assert menu.get_attribute('aria-expanded')=='false'
        else:
            assert page.locator('.ncet-menu-toggle').is_hidden()
        page.close()
    page=browser.new_page(viewport={'width':390,'height':900})
    page.goto(BASE+'/',wait_until='domcontentloaded')
    page.locator('.ncet-impact-band').scroll_into_view_if_needed()
    page.wait_for_timeout(1100)
    assert [v.inner_text() for v in page.locator('[data-ncet-count]').all()]==['25+','6','3','4']
    # No artificial spinner: mark appears only while the slow API call is pending.
    # Stub the native fetch BEFORE application scripts wrap it. A synchronous
    # Playwright route.sleep would block the test controller past the shimmer.
    page.add_init_script("""(() => {
      const nativeFetch=window.fetch.bind(window);
      window.fetch=(url,opts)=>{
        if(String(url).includes('/api/ui-motion-slow')){
          return new Promise(resolve=>setTimeout(()=>resolve(new Response('{}',{
            status:200,headers:{'content-type':'application/json'}
          })),1450));
        }
        return nativeFetch(url,opts);
      };
    })()""")
    page.reload(wait_until='domcontentloaded')
    page.evaluate("() => { window.__slowOperation=fetch('/api/ui-motion-slow',{method:'POST'}); }")
    page.locator('.ncet-network-loader:not([hidden])').wait_for(state='visible',timeout=1500)
    assert page.locator('.ncet-network-loader img').get_attribute('src')=='/static/ncet-brand.svg'
    page.evaluate('() => window.__slowOperation')
    page.locator('.ncet-network-loader').wait_for(state='hidden',timeout=2000)
    page.emulate_media(reduced_motion='reduce')
    page.reload(wait_until='domcontentloaded')
    page.locator('.ncet-impact-band').scroll_into_view_if_needed()
    assert page.locator('.ncet-counter').first.inner_text()=='25+'
    assert page.evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches")
    browser.close()

print('NCET MOTION & UI AUDIT PASS: 6 public routes × 6 widths = 36 layouts, genuine logo loader, accessible mobile menu, counters and reduced motion.')
