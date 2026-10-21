"""Institutional visual and login design guardrails."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_professional_stylesheet_and_accessibility():
    css=(ROOT/'static/enterprise.css').read_text()
    html=(ROOT/'static/index.html').read_text()
    assert 'enterprise.css' in html
    assert '--e-navy:#0e2455' in css
    assert '--e-orange:#f6872a' in css
    assert 'prefers-reduced-motion' in css
    assert ':focus-visible' in css
    assert 'min-width:0' in css
def test_login_uses_server_assigned_identity():
    js=(ROOT/'static/app.js').read_text()
    assert 'role:null' in js
    assert 'data-action="pick-role"' not in js
    assert 'Welcome to NCET VerifyFlow' in js
    assert 'Sign in with your institution-issued username and password' in js
def test_existing_workflows_remain_visible():
    js=(ROOT/'static/app.js').read_text()
    assert 'Department staff' in js
    assert 'Verification report' in js
    assert 'submit-document' in js
    assert 'data-page="upload"' in js
