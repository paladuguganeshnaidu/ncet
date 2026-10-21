"""Only expressly published profiles should be crawlable."""
from app.database import DBSession, User
from app.student_models import BCAStudent
from app.student_profiles import StudentShowcase


def test_public_directory_contains_server_rendered_opt_in_links(client):
    with DBSession() as db:
        person = User(username="1nc24bca983", display_name="Example Published Student",
                      role="student", department="Computer Science & Engineering",
                      password_hash="not-used", active=True)
        private = User(username="1nc24bca984", display_name="Unpublished Example Student",
                       role="student", department="Computer Applications",
                       password_hash="not-used", active=True)
        db.add_all([person, private])
        db.flush()
        db.add_all([
            BCAStudent(user_id=person.id, usn="1NC24BCA983", semester=3,
                       must_change_password=False),
            BCAStudent(user_id=private.id, usn="1NC24BCA984", semester=3,
                       must_change_password=False),
            StudentShowcase(student_id=person.id, published=True, skills_json='["Python"]'),
            StudentShowcase(student_id=private.id, published=False),
        ])
        db.commit()
    html=client.get("/students/directory")
    assert html.status_code==200
    assert "/students/profile/1NC24BCA983" in html.text
    assert "Example Published Student" in html.text
    directory = client.get("/api/bca/directory")
    published = next(item for item in directory.json()["items"] if item["usn"] == "1NC24BCA983")
    assert published["department"] == "Computer Science & Engineering"
    assert "/students/profile/1NC24BCA984" not in html.text
    profile=client.get("/students/profile/1NC24BCA983")
    assert profile.status_code==200
    assert 'application/ld+json' in profile.text
    assert 'index,follow' in profile.text
    assert "Example Published Student" in profile.text
    assert "Computer Science &amp; Engineering" in profile.text
    assert client.get("/students/profile/1NC24BCA984").status_code==404
    sitemap=client.get("/sitemap.xml")
    assert "/students/profile/1NC24BCA983" in sitemap.text
    assert "/students/profile/1NC24BCA984" not in sitemap.text
