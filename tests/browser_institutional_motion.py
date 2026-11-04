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
        page.locator('.hero-workflow').wait_for(state='visible')
        assert page.locator('.workflow-steps li').count()==3,width
        assert page.locator('.topnav img[src*="ncet-brand"]').count()==1,width
        assert page.locator('.ncet-campus-photo img').count()==1,width
        assert page.locator('.ncet-impact-band').count()==0,width
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
    page.locator('.hero-workflow').scroll_into_view_if_needed()
    assert page.locator('.workflow-steps li').count()==3
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
    # Polling/read-only calls are background work and must not display a global toast.
    page.evaluate("() => { window.__backgroundRead=fetch('/api/ui-motion-slow'); }")
    page.wait_for_timeout(650)
    assert page.locator('.ncet-network-loader').is_hidden()
    page.evaluate('() => window.__backgroundRead')
    page.evaluate("() => { window.__slowOperation=fetch('/api/ui-motion-slow',{method:'POST'}); }")
    page.locator('.ncet-network-loader:not([hidden])').wait_for(state='visible',timeout=1500)
    assert page.locator('.ncet-network-loader .ncet-loader-dot').count()==1
    assert page.locator('.ncet-network-loader img').count()==0
    page.evaluate('() => window.__slowOperation')
    page.locator('.ncet-network-loader').wait_for(state='hidden',timeout=2000)
    page.emulate_media(reduced_motion='reduce')
    page.reload(wait_until='domcontentloaded')
    page.locator('.hero-workflow').scroll_into_view_if_needed()
    assert page.locator('.workflow-steps li').count()==3
    assert page.evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches")
    # The logged-in document workspace has its own form progress state and must
    # not show a stale page-wide toast even for a slow authenticated mutation.
    page.goto(BASE+'/app',wait_until='domcontentloaded')
    # Do not import the global loader at all: cached scripts can outlive code fixes.
    assert page.locator('script[src*="ncet-loading.js"]').count()==0
    page.evaluate("() => { window.__appMutation=fetch('/api/ui-motion-slow',{method:'POST'}); }")
    page.wait_for_timeout(650)
    assert page.locator('.ncet-network-loader').count()==0
    page.evaluate('() => window.__appMutation')
    browser.close()

print('NCET MOTION & UI AUDIT PASS: 6 public routes × 6 widths = 36 layouts, minimal activity indicator, accessible mobile menu and reduced motion.')
