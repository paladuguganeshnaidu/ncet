import os
import tempfile
import pytest
os.environ['APP_ENV']='development'
os.environ['STORAGE_BACKEND']='database'
_fd,path=tempfile.mkstemp(suffix='.sqlite3')
os.close(_fd)
os.environ['DATABASE_URL']='sqlite:///'+path
from fastapi.testclient import TestClient
from app.database import Base, engine, DBSession, User
from app.security import hash_password
from app.main import app

@pytest.fixture(autouse=True)
def reset_data():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from app.departments import AcademicDepartment
    with DBSession() as db:
        for name in ('Computer Applications','Computer Science & Engineering','Mechanical Engineering'):
            db.add(AcademicDepartment(code=name,name=name,active=True))
        for name,role,department in [('admin','admin','Institution'),('principal','principal','Institution'),('hod','hod','Computer Science & Engineering'),
                                      ('hod2','hod','Mechanical Engineering'),('staff','staff','Computer Science & Engineering'),
                                      ('staff2','staff','Mechanical Engineering'),('iqac','iqac','Institution')]:
            db.add(User(username=name,display_name=f'NCET {name}',role=role,department=department,
                        password_hash=hash_password('SecurePassword-123!')))
        db.commit()
    yield

@pytest.fixture
def client():
    with TestClient(app) as c:yield c

@pytest.fixture
def login():
    def _login(c,username):
        response=c.post('/api/auth/login',json={'username':username,'password':'SecurePassword-123!','role':('hod' if username=='hod2' else 'staff' if username=='staff2' else username)})
        assert response.status_code==200,response.text
        return response.json()['csrf']
    return _login

@pytest.fixture
def sample_file():
    return ('report.pdf',b'%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF', 'application/pdf')

@pytest.fixture
def create_doc(sample_file):
    def _create(c,csrf):
        name,body,mime=sample_file
        r=c.post('/api/documents',headers={'X-CSRF-Token':csrf},data={
            'title':'NCET Academic Audit Report','category':'Academic Audit','year':'2026–27',
            'description':'Department annual evaluation and academic progress tracking.'},files={'file':(name,body,mime)})
        assert r.status_code==201,r.text
        return r.json()['id']
    return _create
