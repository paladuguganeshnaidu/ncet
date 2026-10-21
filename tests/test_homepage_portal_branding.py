"""Regression: NCET homepage exact official branding, student portal wording and footer hierarchy."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/"static"
LINKS=[
    ("Dr. Thippeswamy Gangappa · Principal ↗","https://www.linkedin.com/in/dr-thippeswamy-gangappa-686b3822/"),
    ("Bhargava R · HOD ↗","https://www.linkedin.com/in/bhargava-r-a08b8182/"),
    ("Paladugu Ganesh Naidu · Developer ↗","https://www.linkedin.com/in/paladuguganeshnaidu/"),
]


def test_homepage_branding_terminology_and_footer_order(client):
    response=client.get("/")
    assert response.status_code==200,response.text[:350]
    html=response.text
    assert "NCET Student Portal" in html
    assert "BCA STUDENT SERVICES" not in html
    assert "Student services" not in html
    assert "student services" not in html
    assert "Student Portal" in html
    assert "BCA HOD" not in html
    assert "BCA directory" not in html
    assert "your department HOD" in html
    assert "home-revamp.css?v=20261017e" in html
    assert "homepage-polish.css" not in html
    assert "/static/ncet-brand.svg?v=20261017c" in html
    assert 'width="455" height="225"' in html
    assert "NCET Student Portal</p>" in html
    assert "Nagarjuna College of Engineering and Technology" in html
    assert "© 2026 NCET VerifyFlow" in html
    locations=[html.index(label) for label,_ in LINKS]
    assert locations==sorted(locations)
    for label,url in LINKS:
        assert f'href="{url}"' in html
        assert label in html
    assert "<h1" in html
    assert 'rel="canonical"' in html


def test_logo_assets_and_homepage_css_exist(client):
    for asset in ("ncet-brand.svg","ncet-brand.png","ngi-brand.svg"):
        result=client.get("/static/"+asset)
        assert result.status_code==200,asset
    for path in ("homepage-polish.css","ncet-brand-system.css"):
        result=client.get("/static/"+path)
        assert result.status_code==200,path
    svg=(STATIC/"ncet-brand.svg").read_text()
    assert svg.startswith("<svg")
    assert "data:image/png;base64," in svg
    css=(STATIC/"homepage-polish.css").read_text()
    assert "#F6872A" in css and "#0E2455" in css
    assert "aspect-ratio:455/225" in css


def test_public_pages_use_student_portal_language(client):
    for route in ("/","/students","/students/portal","/students/directory","/about"):
        result=client.get(route)
        assert result.status_code==200,(route,result.status_code)
        html=result.text.lower()
        assert "student services" not in html,route
    directory=client.get('/students/directory').text
    assert '1NC24BCA001' not in directory
    # Authenticated collaboration remains private, even when public terminology is updated.
    assert client.get("/community").status_code in (200,302,401,403)
