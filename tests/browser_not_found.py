"""Real Chromium 404 UX checks against local NCET test server."""
import os
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

base=os.getenv("NCET_BASE_URL","http://127.0.0.1:8878").rstrip("/")
widths=(320,375,390,768,1024,1440)
with sync_playwright() as tool:
    browser=launch_chromium(tool,headless=True)
    for width in widths:
        page=browser.new_page(viewport={"width":width,"height":850},device_scale_factor=1)
        errors=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        response=page.goto(base+"/no-such-public-route",wait_until="networkidle")
        assert response and response.status==404,(width,response.status if response else None)
        assert "Page not found" in page.title(),width
        assert page.locator("h1").inner_text()=="We couldn't find that page."
        assert page.locator("a[href='/students']").count()==1
        assert page.locator("a[href='/students/directory']").count()==1
        assert page.locator("img[src='/static/ncet-brand.svg']").count()==2
        for img in page.locator("img[src='/static/ncet-brand.svg']").all():
            assert img.evaluate("(img)=>img.complete && img.naturalWidth>0"),width
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),width
        assert not errors,(width,errors)
        if width==390:
            page.locator(".secondary-action").click()
            assert page.url.rstrip("/").endswith("/students"),page.url
            assert page.locator("body").is_visible()
        page.close()
    browser.close()
print("404 CHROMIUM PASS: 6 viewport widths, working original NCET transparent logo, navigation and no horizontal overflow.")
