"""Protection against accidental or unauthorized cleanup."""
from app.database import DBSession, User, Document, AuditLog
from app.student_profiles import StudentShowcase


def _preview(client, csrf, action):
    response = client.get("/api/admin/cleanup/preview")
    assert response.status_code == 200, response.text
    return next(a for a in response.json()["actions"] if a["id"] == action)


def test_cleanup_is_admin_only(client, login):
    assert client.get("/api/admin/cleanup/preview").status_code == 401
    csrf = login(client, "staff")
    assert client.get("/api/admin/cleanup/preview").status_code == 403
    r = client.post("/api/admin/cleanup/execute",
                    headers={"X-CSRF-Token": csrf},
                    json={"action": "disable_staff",
                          "confirmation": "DISABLE STAFF ACCOUNTS", "expected_count": 2})
    assert r.status_code == 403


def test_cleanup_requires_phrase_and_fresh_preview(client, login):
    csrf = login(client, "admin")
    count = _preview(client, csrf, "disable_staff")["count"]
    assert count == 2
    headers = {"X-CSRF-Token": csrf}
    payload = {"action": "disable_staff", "expected_count": count,
               "confirmation": "YES"}
    assert client.post("/api/admin/cleanup/execute", headers=headers,
                       json=payload).status_code == 422
    payload["confirmation"] = "DISABLE STAFF ACCOUNTS"
    payload["expected_count"] = count + 1
    assert client.post("/api/admin/cleanup/execute", headers=headers,
                       json=payload).status_code == 409
    with DBSession() as db:
        assert db.query(User).filter(User.role == "staff", User.active.is_(True)).count() == 2
    payload["expected_count"] = count
    response = client.post("/api/admin/cleanup/execute", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["affected"] == 2
    with DBSession() as db:
        assert db.query(User).filter(User.role == "staff", User.active.is_(True)).count() == 0
        assert db.query(User).filter(User.role == "admin", User.active.is_(True)).count() == 1
        assert db.query(AuditLog).filter(AuditLog.event == "admin.cleanup.disable_staff").count() == 1


def test_unpublish_student_profiles(client, login):
    with DBSession() as db:
        student = User(username="teststudent", display_name="Example Student",
                       role="student", department="Computer Applications",
                       password_hash="not-used")
        db.add(student)
        db.flush()
        db.add(StudentShowcase(student_id=student.id, published=True))
        db.commit()
    csrf = login(client, "admin")
    preview = _preview(client, csrf, "unpublish_profiles")
    assert preview["count"] == 1
    r = client.post("/api/admin/cleanup/execute",
                    headers={"X-CSRF-Token": csrf},
                    json={"action": "unpublish_profiles",
                          "confirmation": preview["confirmation"],
                          "expected_count": 1})
    assert r.status_code == 200, r.text
    with DBSession() as db:
        assert db.query(StudentShowcase).filter(StudentShowcase.published.is_(True)).count() == 0
        assert db.query(User).filter(User.username == "teststudent").count() == 1


def test_approved_pdfs_require_backup_confirmation(client, login, create_doc):
    staff_csrf = login(client, "staff")
    doc_id = create_doc(client, staff_csrf)
    with DBSession() as db:
        doc = db.query(Document).filter(Document.public_id == doc_id).one()
        doc.status = "approved"
        db.commit()
    admin_csrf = login(client, "admin")
    preview = _preview(client, admin_csrf, "delete_approved_pdf_documents")
    assert preview["count"] == 1
    body = {"action": preview["id"], "confirmation": preview["confirmation"],
            "expected_count": 1}
    r = client.post("/api/admin/cleanup/execute",
                    headers={"X-CSRF-Token": admin_csrf}, json=body)
    assert r.status_code == 422
    with DBSession() as db:
        assert db.query(Document).filter(Document.public_id == doc_id).count() == 1
    body["backup_confirmed"] = True
    body["admin_password"] = "SecurePassword-123!"
    r = client.post("/api/admin/cleanup/execute",
                    headers={"X-CSRF-Token": admin_csrf}, json=body)
    assert r.status_code == 200, r.text
    with DBSession() as db:
        assert db.query(Document).filter(Document.public_id == doc_id).count() == 0
        assert db.query(AuditLog).filter(AuditLog.event == "admin.cleanup.delete_approved_pdf_documents").count() == 1
