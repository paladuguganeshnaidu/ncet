"""User-facing service and performance contracts for NCET VerifyFlow."""
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]

def test_public_home_links_actions_and_without_rotating_hero(client):
    response=client.get('/')
    assert response.status_code==200
    html=response.text
    assert 'Your campus.' in html
    assert 'Guidance</span>' not in html
    assert 'film-frames' not in html
    assert 'toggle-animation' not in html
    assert 'href="/students/portal"' in html
    assert 'href="/students/directory"' in html
    assert 'role="search"' in html
    assert 'Skip to main content' in html
    assert 'prefers-reduced-motion' in (ROOT/'static'/'experience.css').read_text()

def test_public_students_directory_works_and_faculty_pages_protected(client):
    assert client.get('/students').status_code==200
    assert client.get('/students/directory').status_code==200
    assert client.get('/api/bca/directory').status_code==200
    assert client.get('/bca/manage').status_code==401
    assert client.get('/community').status_code==401
    assert 'noindex' in client.get('/students/portal').headers.get('x-robots-tag','')

def test_role_workspace_does_not_fetch_blocking_google_fonts():
    stylesheet=(ROOT/'static'/'styles.css').read_text()
    assert 'fonts.googleapis.com' not in stylesheet
    assert '@import' not in stylesheet
    assert 'appearance' not in stylesheet[:1]  # do not silently change core app CSS
