"""Public institutional résumé sections, image assets, and profile security regressions."""
from pathlib import Path

from app.database import DBSession, User
from app.student_models import BCAStudent
from app.security import hash_password

BASE = Path(__file__).resolve().parents[1]
USN = "1NC24CS150"

def make_student(client):
    with DBSession() as db:
        user = User(username=USN.lower(),display_name="College Demo Student",
                    role="student",department="Computer Science & Engineering",
                    password_hash=hash_password("SecurePassword-123!"),active=True)
        db.add(user);db.flush()
        db.add(BCAStudent(user_id=user.id,usn=USN,semester=5,must_change_password=False))
        db.commit()
    reply=client.post("/api/auth/login",json={"username":USN.lower(),"password":"SecurePassword-123!","role":"student"})
    assert reply.status_code==200,reply.text
    return {"X-CSRF-Token":reply.json()["csrf"]}

def test_brand_assets_are_supplied_and_svg(client):
    for name in ("ncet-brand.png","ngi-brand.png","naac-brand.png"):
        file=BASE/"static"/name
        assert file.is_file(), name
        assert file.read_bytes().startswith(bytes.fromhex('89504e470d0a1a0a')), name
        response=client.get("/static/"+name)
        assert response.status_code==200
        assert response.headers["content-type"]=="image/png"
    for name in ("ncet-brand.svg","ngi-brand.svg","naac-brand.svg"):
        svg=(BASE/"static"/name).read_text()
        assert "data:image/png;base64," in svg
        response=client.get("/static/"+name)
        assert response.status_code==200
        assert response.headers["content-type"]=="image/svg+xml"


def test_portfolio_sections_projects_and_public_links(client):
    token=make_student(client)
    assert client.get("/students/profile/"+USN).status_code==404
    payload={
        "full_name":"College Demo Student",
        "mobile":"+919988776655",
        "email":"private@institution.example",
        "about":"Software engineering student creating research and academic tools.",
        "skills":["Python","C","Machine Learning"],
        "interests":["AI Agents","Cloud Computing","Open Source"],
        "certificates":[{"title":"Python Skills","issuer":"Cisco",
                         "proof_url":"https://example.org/credential/123"}],
        "projects":[{"title":"NCET Project Repository","description":"Secure document verification project.",
                     "technologies":["FastAPI","PostgreSQL"],
                     "github_url":"https://github.com/example/ncet-verification",
                     "live_url":"https://demo.example.org"}],
        "social_links":{"github":"https://github.com/example"},
        "publish":True,
    }
    response=client.put("/api/bca/showcase/me",headers=token,json=payload)
    assert response.status_code==200,response.text
    own=client.get("/api/bca/showcase/me").json()
    assert own["interests"]==payload["interests"]
    assert own["projects"][0]["title"]=="NCET Project Repository"
    public=client.get("/api/bca/directory/"+USN).json()
    assert public["projects"][0]["github_url"]==payload["projects"][0]["github_url"]
    page=client.get("/students/profile/"+USN)
    assert page.status_code==200,page.text
    html=page.text
    for label in ("About","Technical skills","Projects","Certifications","Areas of interest",
                  "GitHub, live work & professional links","NCET Project Repository",
                  "Python Skills","AI Agents","https://github.com/example/ncet-verification",
                  "https://demo.example.org","ncet-brand.svg","ngi-brand.svg","naac-brand.svg"):
        assert label in html,label
    assert "application/ld+json" in html
    assert "<lastmod>" in client.get("/sitemap.xml").text
    for confidential in ("private@institution.example","+919988776655"):
        assert confidential not in html
        assert confidential not in str(public)

def test_unsafe_external_links_and_contact_fields_rejected(client):
    token=make_student(client)
    base={"full_name":"College Demo Student","publish":True}
    for url in ("http://example.com","javascript:alert(1)","https://localhost/panel"):
        response=client.put("/api/bca/showcase/me",headers=token,json={
            **base,"projects":[{"title":"Unsafe Project","github_url":"https://github.com/example/repo","live_url":url}]})
        assert response.status_code==422,(url,response.text)
    response=client.put("/api/bca/showcase/me",headers=token,json={
        **base,"projects":[{"title":"Wrong GitHub","github_url":"https://github-notreal.example/project"}]})
    assert response.status_code==422
    response=client.put("/api/bca/showcase/me",headers=token,json={
        **base,"interests":["Email me at private@example.org"]})
    assert response.status_code==422
    assert client.get("/students/profile/"+USN).status_code==404

def test_unpublishing_removes_projects_from_public_search(client):
    token=make_student(client)
    data={"full_name":"College Demo Student","projects":[{"title":"Safe Public Project"}],"publish":True}
    assert client.put("/api/bca/showcase/me",headers=token,json=data).status_code==200
    assert "Safe Public Project" in client.get("/students/profile/"+USN).text
    data["publish"]=False
    assert client.put("/api/bca/showcase/me",headers=token,json=data).status_code==200
    assert client.get("/students/profile/"+USN).status_code==404
    assert USN not in client.get("/sitemap.xml").text
