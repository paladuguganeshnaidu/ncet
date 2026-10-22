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

    # CLS is the largest session window, not the sum of every shift during a visit.
    browser = launch_chromium(playwright,headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.add_init_script("""
        const NativeObserver = window.PerformanceObserver;
        class PlotObserver {
          constructor(callback) { this.callback = callback; this.native = null; }
          observe(options) {
            if (options.type === 'layout-shift') {
              window.__plotLayoutShiftCallback = this.callback;
              return;
            }
            this.native = new NativeObserver(this.callback);
            this.native.observe(options);
          }
          disconnect() { this.native?.disconnect(); }
        }
        PlotObserver.supportedEntryTypes = NativeObserver.supportedEntryTypes;
        window.PerformanceObserver = PlotObserver;
    """)
    page.goto(BASE + '/plot', wait_until='domcontentloaded', timeout=25000)
    page.evaluate("""() => {
      const callback = window.__plotLayoutShiftCallback;
      if (!callback) throw new Error('Plot CLS observer was not registered');
      const entries = [
        {value: 0.06, startTime: 1000, hadRecentInput: false},
        {value: 0.04, startTime: 1600, hadRecentInput: false},
        {value: 0.20, startTime: 2700, hadRecentInput: false},
        {value: 0.04, startTime: 3600, hadRecentInput: false},
        {value: 0.20, startTime: 4500, hadRecentInput: false},
        {value: 0.12, startTime: 5500, hadRecentInput: false},
        {value: 0.09, startTime: 10000, hadRecentInput: false},
        {value: 0.02, startTime: 10800, hadRecentInput: false},
        {value: 0.02, startTime: 11700, hadRecentInput: false},
        {value: 0.02, startTime: 12600, hadRecentInput: false},
        {value: 0.02, startTime: 13500, hadRecentInput: false},
        {value: 0.02, startTime: 14400, hadRecentInput: false},
        {value: 0.30, startTime: 15000, hadRecentInput: false,
          sources: [{node: document.querySelector('.metric')}]},
        {value: 0.70, startTime: 15100, hadRecentInput: true,
          sources: [{node: document.querySelector('body')}]}
      ];
      callback({getEntries: () => entries});
    }""")
    assert page.locator('#metric-cls').inner_text() == '0.440'
    page.locator('#shift-diagnostics summary').click()
    shift_report = page.locator('#shift-source-list').inner_text()
    assert 'article.metric.panel · shift score 0.300' in shift_report, shift_report
    assert '0.70' not in shift_report, shift_report
    browser.close()

print('NCET PLOT PAGE PASS: live health probe, browser resource chart, privacy metadata, 4 responsive widths, and CLS session-window calculation.')
