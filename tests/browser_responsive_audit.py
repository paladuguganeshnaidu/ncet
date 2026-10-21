"""Repeatable viewport regression for public NCET pages.

Run after local server starts:
    NCET_BASE_URL=http://127.0.0.1:8000 python tests/browser_responsive_audit.py

No student or administrative account credentials are used.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

BASE = os.getenv("NCET_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PAGES = ["/", "/students", "/about", "/students/directory", "/students/portal", "/app", "/plot"]
WIDTHS = [320, 375, 390, 428, 768, 1024, 1440]
SCREENSHOTS = os.getenv("NCET_RESPONSIVE_SCREENSHOTS") == "1"
DEST = Path(__file__).parent / "responsive-screenshots"
issues = []

with sync_playwright() as playwright:
    browser = launch_chromium(playwright,headless=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": 900},
                                device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        for route in PAGES:
            response = page.goto(BASE + route, wait_until="domcontentloaded", timeout=25000)
            if not response or response.status >= 400:
                issues.append((width, route, "HTTP " + str(response.status if response else "no response")))
                continue
            page.wait_for_timeout(150)
            measurements = page.evaluate("""() => {
                const doc=document.documentElement;
                const offenders=[...document.querySelectorAll("body *")]
                  .filter(el => {
                    const rect=el.getBoundingClientRect();
                    const style=getComputedStyle(el);
                    return style.position!=="fixed" &&
                        rect.width > 0 && rect.right > innerWidth+3 &&
                        style.visibility!=="hidden" && style.display!=="none";
                  })
                  .slice(0, 12).map(el=>({
                    tag:el.tagName.toLowerCase(),id:el.id,
                    className:String(el.className||"").slice(0,65)
                  }));
                return {scrollWidth:doc.scrollWidth, viewport:innerWidth, offenders};
            }""")
            if measurements["scrollWidth"] > width + 3:
                issues.append((width, route, "overflow", measurements))
            for error in errors:
                issues.append((width, route, "JavaScript", error))
            errors.clear()
            if SCREENSHOTS:
                DEST.mkdir(parents=True, exist_ok=True)
                label = route.strip("/").replace("/", "-") or "home"
                page.screenshot(path=str(DEST / f"{label}-{width}px.png"), full_page=True)
        page.close()
    browser.close()

if issues:
    for issue in issues:
        print("FAILED:", issue)
    raise SystemExit(f"Responsive audit found {len(issues)} problems.")
print(f"PASS: {len(PAGES)} pages x {len(WIDTHS)} viewports with no document-level overflow or JS exceptions.")
