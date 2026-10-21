"""Opt-in photo privacy, upload constraints, and dynamic portfolio discoverability."""
import io
from PIL import Image
from app.database import DBSession, User
from app.student_models import BCAStudent
from app.student_profiles import StudentShowcase
from app.security import hash_password

USN="1NC24BCA991"

def setup_student(client):
    with DBSession() as db:
        user=User(username=USN.lower(),display_name="Demo Portfolio Student",
                  role="student",department="Computer Applications",
                  password_hash=hash_password("SecurePassword-123!"))
        db.add(user);db.flush()
        db.add(BCAStudent(user_id=user.id,usn=USN,semester=4,must_change_password=False))
        db.commit()
    login=client.post("/api/auth/login",json={"username":USN.lower(),
                          "password":"SecurePassword-123!","role":"student"})
    assert login.status_code==200,login.text
    return {"X-CSRF-Token":login.json()["csrf"]}

def sample_photo():
    output=io.BytesIO()
    Image.new("RGB",(160,160),(35,120,80)).save(output,format="PNG")
    return output.getvalue()

def test_photo_private_until_publish_and_remove(client):
    headers=setup_student(client)
    assert client.get("/students/profile/"+USN+"/photo").status_code==404
    assert client.put("/api/bca/showcase/me/photo",files={"file":("profile.png",sample_photo(),"image/png")}).status_code in (401,403)
    result=client.put("/api/bca/showcase/me/photo",headers=headers,
                      files={"file":("profile.png",sample_photo(),"image/png")})
    assert result.status_code==200,result.text
    assert result.json()["size_bytes"]<150000
    private=client.get("/api/bca/showcase/me/photo")
    assert private.status_code==200
    assert private.headers["content-type"]=="image/webp"
    assert client.get("/students/profile/"+USN+"/photo").status_code==404
    assert client.get("/api/bca/showcase/me").json()["photo_available"] is True
    publish=client.put("/api/bca/showcase/me",headers=headers,json={
        "full_name":"Demo Portfolio Student","skills":["C","Python"],"publish":True})
    assert publish.status_code==200,publish.text
    public=client.get("/students/profile/"+USN+"/photo")
    assert public.status_code==200 and public.headers["content-type"]=="image/webp"
    page=client.get("/students/profile/"+USN)
    assert '/students/profile/'+USN+'/photo' in page.text
    assert 'og:image' in page.text
    assert USN in client.get("/sitemap.xml").text
    assert "<lastmod>" in client.get("/sitemap.xml").text
    unpublish=client.put("/api/bca/showcase/me",headers=headers,json={
        "full_name":"Demo Portfolio Student","publish":False})
    assert unpublish.status_code==200
    assert client.get("/students/profile/"+USN+"/photo").status_code==404
    assert client.get("/students/profile/"+USN).status_code==404
    assert USN not in client.get("/sitemap.xml").text
    assert client.get("/api/bca/showcase/me/photo").status_code==200
    delete=client.delete("/api/bca/showcase/me/photo",headers=headers)
    assert delete.status_code==200
    assert client.get("/api/bca/showcase/me/photo").status_code==404

def test_photo_rejects_oversize_and_malformed(client):
    headers=setup_student(client)
    huge=client.put("/api/bca/showcase/me/photo",headers=headers,
        files={"file":("large.png",b"x"*(150000),"image/png")})
    assert huge.status_code==413
    malformed=client.put("/api/bca/showcase/me/photo",headers=headers,
        files={"file":("fake.png",b"not-a-real-image","image/png")})
    assert malformed.status_code==422
    svg=client.put("/api/bca/showcase/me/photo",headers=headers,
        files={"file":("test.svg",b"<svg/>","image/svg+xml")})
    assert svg.status_code==422
    with DBSession() as db:
        assert db.query(StudentShowcase).count()==0

def test_student_directory_server_pagination(client):
    with DBSession() as db:
        for i in range(31):
            u=User(username=f"1nc24bca{i:03d}",display_name=f"Published student {i:03d}",
                   role="student",department="Computer Applications",
                   password_hash="test-hash")
            db.add(u);db.flush()
            db.add(BCAStudent(user_id=u.id,usn=f"1NC24BCA{i:03d}",
                              semester=4,must_change_password=False))
            db.add(StudentShowcase(student_id=u.id,published=True))
        db.commit()
    html=client.get("/students/directory").text
    assert 'Page 1 of 2' in html and 'page=2' in html
    page2=client.get("/students/directory?page=2")
    assert page2.status_code==200
    assert 'Published student 030' in page2.text
    assert client.get("/students/directory?page=3").status_code==404
    query=client.get("/api/bca/directory?limit=12&offset=24").json()
    assert query["total"]==31 and len(query["items"])==7
    sitemap=client.get("/sitemap.xml")
    assert sitemap.status_code==200
    assert "1NC24BCA030" in sitemap.text
    assert "1NC24BCA000" in sitemap.text
