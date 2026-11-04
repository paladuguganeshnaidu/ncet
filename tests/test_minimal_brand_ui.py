"""Minimal institutional design checks: single-brand pages and functional flows."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/"static"
PAGES=(
    "index.html","public-home.html","about.html","404.html","tasks.html",
    "student-portal.html","student-services.html","student-directory.html",
    "bca-management.html","bca-oversight.html","community.html",
    "complaints-dashboard.html","plot.html","bca-access-denied.html",
)


def test_every_static_page_uses_one_shared_minimal_design_layer():
    for page in PAGES:
        html=(STATIC/page).read_text(encoding="utf-8")
        assert html.count("enterprise-minimal.css")==1,page


def test_homepage_keeps_real_workflows_without_duplicate_college_marks():
    html=(STATIC/"public-home.html").read_text(encoding="utf-8")
    assert html.count('<img src="/static/ncet-brand.svg')==1
    assert "nav-accreditation" not in html
    assert "identity-panel" not in html
    assert "ncet-impact-band" not in html
    assert "hero-workflow" in html
    assert all(text in html for text in (
        "Define requirements","Submit documents","Review with evidence",
        'href="/students/portal"','href="/students/directory"',
        'role="search"'
    ))
    assert html.count('class="service-card"')==3


def test_no_repeated_brand_as_blank_profile_or_network_spinner():
    assert 'src="/static/profile-placeholder.svg"' in (STATIC/"student-portal.html").read_text(encoding="utf-8")
    js=(STATIC/"student-portal.js").read_text(encoding="utf-8")
    assert "img.src='/static/profile-placeholder.svg'" in js
    loader=(STATIC/"ncet-loading.js").read_text(encoding="utf-8")
    assert "ncet-loader-dot" in loader
    assert "mark.src='/static/ncet-brand.svg'" not in loader
    css=(STATIC/"enterprise-minimal.css").read_text(encoding="utf-8")
    assert "--ncet-gradient:" in css
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css


def test_shared_chrome_uses_ncet_colors_and_request_feedback_is_brief():
    css=(STATIC/"institutional-ui.css").read_text(encoding="utf-8")
    assert ":where(.topnav,.topbar,.site-header,.resume-site-header)" in css
    assert "border-bottom:3px solid var(--ncet-orange)" in css
    assert ".about-footer" in css and "border-top:3px solid var(--ncet-orange)" in css
    assert ".student-removal-review" in css
    loader=(STATIC/"ncet-loading.js").read_text(encoding="utf-8")
    assert "const MAX_INDICATOR_MS=2000" in loader
    assert "setTimeout(()=>{delete form.dataset.ncetNavigating;finish()},2000)" in loader

