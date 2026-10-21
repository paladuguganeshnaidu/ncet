"""Official 404 page and case-insensitive USN acceptance end-to-end."""
from fastapi.testclient import TestClient

from app.database import DBSession, User
from app.main import app
from app.security import hash_password
from app.student_models import BCAStudent
from app.student_profiles import StudentShowcase

USN="1NC24CS150"
PASSWORD="LongStudentPassword-2026!"

def published_student():
    with DBSession() as db:
        u=User(username=USN.lower(),display_name="USN Case Test Student",
               role="student",department="Computer Science & Engineering",
               active=True,password_hash=hash_password(PASSWORD))
        db.add(u);db.flush()
        db.add(BCAStudent(user_id=u.id,usn=USN,semester=5,must_change_password=False))
        db.add(StudentShowcase(student_id=u.id,published=True,
                              about="Learning engineering and college collaboration",
                              skills_json='["Python"]'))
        db.commit()


def test_404_html_is_real_unindexed_and_linked(client):
    response=client.get("/unknown/students/no-such-page")
    assert response.status_code==404
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"]=="no-store"
    assert "noindex" in response.headers["x-robots-tag"]
    html=response.text
    for expected in ('Page not found','We couldn\'t find that page','/static/ncet-brand.svg',
                     'NCET Student Portal','href="/students"','href="/students/directory"',
                     'href="/"','uppercase, lowercase and mixed-case USNs'):
        assert expected in html,expected
    assert "/unknown/students/no-such-page" not in client.get("/sitemap.xml").text


def test_api_and_asset_404_still_machine_readable(client):
    for path in ("/api/no-route-exists","/static/no-such-asset.svg",
                 "/api/bca/directory/1NC24CS999"):
        response=client.get(path,headers={"accept":"application/json"})
        assert response.status_code==404
        assert response.headers["content-type"].startswith("application/json"),path
        assert "We couldn't find that page" not in response.text
    response=client.get("/any-missing",headers={"accept":"application/json"})
    assert response.status_code==404
    assert response.headers["content-type"].startswith("application/json")


def test_public_unpublished_profiles_are_not_leaked_via_404(client):
    published_student()
    with DBSession() as db:
        item=db.query(StudentShowcase).first();item.published=False;db.commit()
    for candidate in (USN,USN.lower(),"1Nc24Cs150"):
        result=client.get("/students/profile/"+candidate)
        assert result.status_code==404
        assert "noindex" in result.headers["x-robots-tag"]
        assert "USN Case Test Student" not in result.text
    assert USN not in client.get("/sitemap.xml").text


def test_student_login_accepts_upper_lower_and_mixed_usn(client):
    published_student()
    for candidate in (USN,USN.lower(),"1Nc24Cs150","  1nC24cS150  "):
        with TestClient(app) as signed:
            result=signed.post("/api/auth/login",json={
                "username":candidate,"password":PASSWORD,"role":"student"})
            assert result.status_code==200,(candidate,result.text)
            assert result.json()["user"]["username"]==USN.lower()
            own=signed.get("/api/bca/me")
            assert own.status_code==200
            assert own.json()["usn"]==USN
    wrong=client.post("/api/auth/login",json={
        "username":USN.swapcase(),"password":"IncorrectPassword!","role":"student"})
    assert wrong.status_code==401


def test_public_profiles_directory_and_photo_lookup_case_insensitive(client):
    published_student()
    for candidate in (USN,USN.lower(),"1Nc24Cs150","  1nC24cS150  "):
        search=client.get("/api/bca/directory",params={"q":candidate.strip()})
        assert search.status_code==200
        assert search.json()["total"]==1
        assert search.json()["items"][0]["usn"]==USN
        record=client.get("/api/bca/directory/"+candidate.strip())
        assert record.status_code==200
        assert record.json()["usn"]==USN
        page=client.get("/students/profile/"+candidate.strip())
        assert page.status_code==200
        assert f"/students/profile/{USN}" in page.text
        assert "USN Case Test Student" in page.text
        photo=client.get("/students/profile/"+candidate.strip()+"/photo")
        assert photo.status_code==404   # Student has not uploaded a photo.


def test_duplicate_enrollment_ignores_usn_letter_case(client,login):
    admin=login(client,'admin')
    endpoint="/api/bca/students/enroll"
    student={"usn":"1nc24cs151","full_name":"Case Enrollment Student",
             "branch":"Computer Science & Engineering","semester":4}
    first=client.post(endpoint,headers={"X-CSRF-Token":admin},
                      json={"students":[student]})
    assert first.status_code==200,first.text
    assert first.json()["credentials"][0]["usn"]=="1NC24CS151"
    second=client.post(endpoint,headers={"X-CSRF-Token":admin},
                       json={"students":[{**student,"usn":"1Nc24cS151"}]})
    assert second.status_code==409,second.text
    with DBSession() as db:
        assert db.query(User).filter(User.username=="1nc24cs151").count()==1
