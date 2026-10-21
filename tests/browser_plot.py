"""Live browser checks for the browser-local performance report."""
import os
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

BASE = os.getenv('NCET_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
WIDTHS = (320, 390, 768, 1366)

with sync_playwright() as playwright:
    browser = launch_chromium(playwright,headless=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={'width': width, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        response = page.goto(BASE + '/plot', wait_until='domcontentloaded', timeout=25000)
        assert response and response.status == 200, (width, response.status if response else None)
        page.locator('#health-status').get_by_text('Healthy').wait_for(timeout=10000)
        cls_text = '—'
        for _ in range(100):
            cls_text = page.locator('#metric-cls').inner_text()
            if cls_text != '—':
                break
            page.wait_for_timeout(50)
        assert cls_text != '—', (width, 'CLS sample was not emitted')
        cls = float(cls_text)
        assert cls <= 0.1, (width, cls)
        assert page.locator('.resource-row').count() == 5
        assert page.locator('#resource-total').inner_text() != '—'
        assert page.locator('meta[name="robots"]').get_attribute('content') == 'noindex,nofollow,noarchive'
        palette = page.evaluate("""() => ({
            navy: getComputedStyle(document.documentElement).getPropertyValue('--navy').trim(),
            orange: getComputedStyle(document.documentElement).getPropertyValue('--orange').trim()
        })""")
        assert palette == {'navy': '#0e2455', 'orange': '#f6872a'}, palette
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 3'), width
        page.locator('#check-health').click()
        page.locator('#health-status').get_by_text('Healthy').wait_for(timeout=10000)
        assert not errors, (width, errors)
        page.close()
    browser.close()

    browser = launch_chromium(playwright,headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(BASE + '/', wait_until='domcontentloaded', timeout=25000)
    assert page.locator('footer a[href="/plot"]').inner_text() == 'Performance & optimization'
    browser.close()

print('NCET PLOT PAGE PASS: live health probe, browser resource chart, privacy metadata, and 4 responsive widths.')
