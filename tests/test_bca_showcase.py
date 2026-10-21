"""Privacy-first BCA student onboarding and opt-in public directory regression tests."""
import io
import json
from openpyxl import Workbook
from fastapi.testclient import TestClient
from app.main import app
from app.database import User, DBSession
from app.student_profiles import StudentShowcase


def setup_bca():
    with DBSession() as db:
        for username in ('hod','staff'):
            u=db.query(User).filter_by(username=username).one()
            u.department='Computer Applications'
        db.commit()


def enroll(client,login,records):
    setup_bca()
    token=login(client,'hod')
    response=client.post('/api/bca/students/enroll',headers={'X-CSRF-Token':token},
                         json={'students':records})
    return response,token


def test_single_usn_enrollment_and_private_student_profile(client,login):
    response,token=enroll(client,login,[{'usn':'1NC24BCA301','full_name':'Student Example','branch':'Computer Applications','semester':1}])
    assert response.status_code==200,response.text
    credentials=response.json()['credentials'][0]
    assert credentials['name']=='Student Example'
    assert credentials['temporary_password']!='Ncet@1nc24bca301'
    assert len(credentials['temporary_password'])>=24
    assert client.get('/api/bca/directory').json()['items']==[]
    assert client.get('/api/bca/directory/1NC24BCA301').status_code==404
    with TestClient(app) as student_client:
        login_result=student_client.post('/api/auth/login',json={'username':'1NC24BCA301',
            'password':credentials['temporary_password'],'role':'student'})
        assert login_result.status_code==200
        student_token=login_result.json()['csrf']
        private=student_client.get('/api/bca/showcase/me').json()
        assert private['usn']=='1NC24BCA301'
        assert private['full_name']=='Student Example'
        assert student_client.put('/api/bca/showcase/me',headers={'X-CSRF-Token':student_token},json={
            'full_name':'Student Example','publish':True}).status_code==403
        changed=student_client.post('/api/auth/change-password',headers={'X-CSRF-Token':student_token},
            json={'old_password':credentials['temporary_password'],
                  'new_password':'GenuinelyNewLongPassword2026!'})
        assert changed.status_code==200
        payload={'full_name':'BCA Student Example','mobile':'+919876543210',
                 'email':'student.private@example.org','about':'Python and accessible software',
                 'skills':['Python','Accessibility','Python'],
                 'certificates':[{'title':'Python Essentials','issuer':'Cisco','proof_url':'https://example.org/verify/123'}],
                 'publish':True}
        saved=student_client.put('/api/bca/showcase/me',headers={'X-CSRF-Token':student_token},json=payload)
        assert saved.status_code==200,saved.text
        assert saved.json()['published'] is True
        mine=student_client.get('/api/bca/showcase/me').json()
        assert mine['mobile']=='+919876543210'
        assert mine['email']=='student.private@example.org'
    public=client.get('/api/bca/directory/1NC24BCA301')
    assert public.status_code==200
    assert public.json()['name']=='BCA Student Example'
    assert public.json()['skills']==['Python','Accessibility']
    assert public.json()['certificates'][0]['title']=='Python Essentials'
    page=client.get('/students/profile/1NC24BCA301')
    assert page.status_code==200
    assert 'BCA Student Example' in page.text
    assert '1NC24BCA301' in client.get('/sitemap.xml').text
    for obj in (public.text,client.get('/api/bca/directory').text,page.text,
                client.get('/sitemap.xml').text):
        assert '9876543210' not in obj
        assert 'student.private@example.org' not in obj
        assert 'GenuinelyNewLongPassword' not in obj
    with TestClient(app) as another_student:
        pass


def test_public_profile_can_be_unpublished_and_inputs_are_validated(client,login):
    reply,token=enroll(client,login,[{'usn':'1NC24BCA302','full_name':'Second Student','branch':'Computer Applications','semester':4}])
    assert reply.status_code==200
    pwd=reply.json()['credentials'][0]['temporary_password']
    with TestClient(app) as student:
        auth=student.post('/api/auth/login',json={'username':'1nc24bca302','password':pwd,'role':'student'})
        csrf=auth.json()['csrf']
        student.post('/api/auth/change-password',headers={'X-CSRF-Token':csrf},
                     json={'old_password':pwd,'new_password':'ChangePassword2026!12345'})
        base={'full_name':'Second Student','mobile':'9998887776','email':'private@example.org',
              'about':'Learning software engineering','skills':['Java'],'certificates':[],
              'publish':True}
        invalid=student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},
                            json={**base,'certificates':[{'title':'Unsafe proof','issuer':'Institution','proof_url':'javascript:alert(1)'}]})
        assert invalid.status_code==422
        assert student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},json=base).status_code==200
        assert client.get('/api/bca/directory/1NC24BCA302').status_code==200
        assert student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},
                           json={**base,'publish':False}).status_code==200
    assert client.get('/api/bca/directory/1NC24BCA302').status_code==404
    assert client.get('/students/profile/1NC24BCA302').status_code==404
    assert '1NC24BCA302' not in client.get('/sitemap.xml').text


def test_excel_and_bulk_enrollment_are_scoped_and_atomic(client,login):
    setup_bca()
    assert client.post('/api/bca/students/enroll',json={'students':[{'usn':'1NC24BCA303','full_name':'Candidate Name','branch':'Computer Applications','semester':3}]}).status_code in (401,403)
    staff_csrf=login(client,'staff')
    good={'students':[{'usn':'1NC24BCA303','full_name':'Excel Student','branch':'Computer Applications','semester':3},
                      {'usn':'1NC24BCA304','full_name':'Second Excel Student','branch':'Computer Applications','semester':1}]}
    response=client.post('/api/bca/students/enroll',headers={'X-CSRF-Token':staff_csrf},json=good)
    assert response.status_code==200
    assert response.json()['created']==2
    dup=client.post('/api/bca/students/enroll',headers={'X-CSRF-Token':staff_csrf},
                    json={'students':[{'usn':'1NC24BCA304','full_name':'Already Enrolled','branch':'Computer Applications','semester':1},{'usn':'1NC24BCA305','full_name':'New Candidate','branch':'Computer Applications','semester':1}]})
    assert dup.status_code==409
    assert client.get('/api/bca/students').status_code==200
    assert len(client.get('/api/bca/students').json()['items'])==2
    wb=Workbook();ws=wb.active;ws.append(['usn','full_name','branch','semester'])
    ws.append(['1NC24BCA306','Spreadsheet Student','Computer Applications',2]);ws.append(['1NC24BCA307','Another Student','Computer Applications',3])
    raw=io.BytesIO();wb.save(raw)
    excel=client.post('/api/bca/students/import-excel',headers={'X-CSRF-Token':staff_csrf},
                      files={'file':('students.xlsx',raw.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert excel.status_code==200,excel.text
    assert excel.json()['created']==2
    edit=client.patch('/api/bca/students/1NC24BCA307',headers={'X-CSRF-Token':staff_csrf},
                      json={'full_name':'Corrected Student Name','branch':'Computer Applications','semester':5})
    assert edit.status_code==200
    assert 'Corrected Student Name' in str(client.get('/api/bca/students').json())



def test_public_profiles_reject_contact_details_in_public_fields(client,login):
    response,token=enroll(client,login,[{'usn':'1NC24BCA311','full_name':'Profile Student','branch':'Computer Applications','semester':3}])
    assert response.status_code==200
    password=response.json()['credentials'][0]['temporary_password']
    with TestClient(app) as student:
        auth=student.post('/api/auth/login',json={'username':'1nc24bca311','password':password,'role':'student'})
        csrf=auth.json()['csrf']
        assert student.post('/api/auth/change-password',headers={'X-CSRF-Token':csrf},
            json={'old_password':password,'new_password':'MyNewPrivatePassword888!'}).status_code==200
        payload={'full_name':'Profile Student','mobile':'+919988776655','email':'private@example.org',
                 'about':'Contact me at secret@example.org','skills':['Python'],
                 'certificates':[],'publish':True}
        attempt=student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},json=payload)
        assert attempt.status_code==422
        second=student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},
            json={**payload,'about':'Working on academic technology','skills':['Contact 9998887776']})
        assert second.status_code==422
        third=student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},
            json={**payload,'about':'Interested in software engineering'})
        assert third.status_code==200
        assert client.get('/api/bca/directory/1NC24BCA311').status_code==200
