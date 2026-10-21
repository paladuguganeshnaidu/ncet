"""BCA student and HOD workflow without modifying live records."""
import io
import re
from app.database import DBSession, User


def prepare_bca():
    with DBSession() as db:
        for name in ('hod','staff'):
            account=db.query(User).filter(User.username==name).one()
            account.department='Computer Applications'
        db.commit()


def import_one(client,login):
    prepare_bca()
    token=login(client,'hod')
    r=client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={
        'file':('students.csv',b'usn,full_name,branch,semester\n1NC24BCA001,Student One,Computer Applications,3\n','text/csv')})
    assert r.status_code==200,r.text
    assert r.json()['created']==1
    return token,r.json()['credentials'][0]['temporary_password']


def login_student(client,pwd):
    r=client.post('/api/auth/login',json={'username':'1NC24BCA001','password':pwd,'role':'student'})
    assert r.status_code==200,r.text
    return r.json()['csrf']


def test_csv_enrollment_role_scope_validation_and_no_overwrite(client,login):
    prepare_bca()
    token=login(client,'staff')
    csv=b'usn,full_name,branch,semester\n1NC24BCA001,Student One,Computer Applications,3\n1NC24BCA002,Student Two,Computer Applications,4\n'
    assert client.post('/api/bca/students/import',files={'file':('x.csv',csv,'text/csv')}).status_code==403
    invalid=client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={'file':('x.csv',b'usn,full_name,branch,semester\nBADA,Student One,Computer Applications,3\n','text/csv')})
    assert invalid.status_code==422
    r=client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={'file':('x.csv',csv,'text/csv')})
    assert r.status_code==200,r.text
    assert r.json()['created']==2
    assert all(len(x['temporary_password'])>=20 for x in r.json()['credentials'])
    assert client.get('/api/bca/students').status_code==200
    assert len(client.get('/api/bca/students').json()['items'])==2
    assert client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={'file':('x.csv',csv,'text/csv')}).status_code==409
    assert len(client.get('/api/bca/students').json()['items'])==2


def test_case_privacy_password_change_hod_replies_and_closure(client,login):
    hod_token,pwd=import_one(client,login)
    # HOD session belongs to TestClient, students are separate sessions.
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as student_client:
        student_token=login_student(student_client,pwd)
        profile=student_client.get('/api/bca/me').json()
        assert profile['usn']=='1NC24BCA001' and profile['must_change_password']
        payload={'category':'academics','subject':'Class timetable issue','description':'Our class timetable needs correction for this week.'}
        assert student_client.post('/api/bca/cases',headers={'X-CSRF-Token':student_token},json=payload).status_code==403
        change=student_client.post('/api/auth/change-password',headers={'X-CSRF-Token':student_token},json={'old_password':pwd,'new_password':'A-new-very-strong-password-1234!'})
        assert change.status_code==200,change.text
        assert not student_client.get('/api/bca/me').json()['must_change_password']
        assert student_client.post('/api/bca/cases',json=payload).status_code==403
        c=student_client.post('/api/bca/cases',headers={'X-CSRF-Token':student_token},json=payload)
        assert c.status_code==201,c.text
        ref=c.json()['reference']
        assert ref.startswith('NCET-REQ-')
        assert len(student_client.get('/api/bca/cases').json()['items'])==1
        assert client.get('/api/bca/cases').status_code==200
        # Case replies cannot be read by staff.
        from fastapi.testclient import TestClient
        with TestClient(app) as staff_client:
            staff_token=login(staff_client,'staff')
            assert staff_client.get('/api/bca/cases').status_code==403
            assert staff_client.get('/api/bca/cases/'+ref).status_code==403
        assert client.patch('/api/bca/cases/'+ref+'/status',headers={'X-CSRF-Token':hod_token},json={'status':'resolved','note':'Issue has been reviewed and corrected.'}).status_code==200
        assert student_client.get('/api/bca/cases/'+ref).json()['messages'][0]['author']=='HOD'
        assert student_client.post('/api/bca/cases/'+ref+'/messages',headers={'X-CSRF-Token':student_token},json={'message':'Thank you for the update.'}).status_code==200
        assert client.patch('/api/bca/cases/'+ref+'/status',headers={'X-CSRF-Token':hod_token},json={'status':'closed','note':'We have finished the timetable correction.'}).status_code==200
        assert student_client.post('/api/bca/cases/'+ref+'/messages',headers={'X-CSRF-Token':student_token},json={'message':'One more'}).status_code==409
        with TestClient(app) as other:
            login(other,'hod2')
            assert other.get('/api/bca/cases/'+ref).status_code==404
            assert other.get('/api/bca/cases').status_code==200
            assert other.get('/api/bca/cases').json()['all_total']==0


def test_student_requests_follow_actual_department_and_notify_its_hod(client,login):
    admin_token=login(client,'admin')
    imported=client.post('/api/bca/students/import',headers={'X-CSRF-Token':admin_token},files={
        'file':('students.csv',b'usn,full_name,branch,semester\n1NC24CSE901,Student CSE,Computer Science & Engineering,5\n','text/csv')})
    assert imported.status_code==200,imported.text
    temporary=imported.json()['credentials'][0]['temporary_password']

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as student:
        signed=student.post('/api/auth/login',json={'username':'1nc24cse901','password':temporary,'role':'student'})
        assert signed.status_code==200,signed.text
        csrf=signed.json()['csrf']
        changed=student.post('/api/auth/change-password',headers={'X-CSRF-Token':csrf},json={
            'old_password':temporary,'new_password':'CSE-student-new-password-2026!'})
        assert changed.status_code==200,changed.text
        created=student.post('/api/bca/cases',headers={'X-CSRF-Token':csrf},json={
            'category':'academics','subject':'CSE lab schedule review',
            'description':'Please review the updated Computer Science laboratory schedule.'})
        assert created.status_code==201,created.text
        ref=created.json()['reference']
        assert student.get('/api/bca/cases/'+ref).status_code==200

    # This fixture's HOD is CSE; the other HOD belongs to Mechanical Engineering.
    hod_token=login(client,'hod')
    cases=client.get('/api/bca/cases').json()
    assert cases['total']==1 and cases['items'][0]['reference']==ref
    detail=client.get('/api/bca/cases/'+ref).json()
    assert detail['student']['name']=='Student CSE'
    assert client.patch('/api/bca/cases/'+ref+'/status',headers={'X-CSRF-Token':hod_token},json={
        'status':'resolved','note':'The schedule has been reviewed with the department.'}).status_code==200
    alerts=client.get('/api/alerts/inbox').json()['items']
    assert any('New student request' in item['text'] for item in alerts)
    with TestClient(app) as unrelated:
        login(unrelated,'hod2')
        assert unrelated.get('/api/bca/cases').json()['all_total']==0
        assert unrelated.get('/api/bca/cases/'+ref).status_code==404


def test_public_indexable_service_private_data_not_indexable(client):
    for route in ('/','/students'):
        response=client.get(route)
        assert response.status_code==200
        assert 'noindex' not in response.headers.get('x-robots-tag','').lower()
    assert 'noindex' in client.get('/students/portal').headers['x-robots-tag']
    assert 'noindex' in client.get('/bca/manage').headers['x-robots-tag']
    assert 'noindex' in client.get('/api/bca/students').headers['x-robots-tag']
    robots=client.get('/robots.txt').text
    assert 'Disallow: /students/portal' in robots
    xml=client.get('/sitemap.xml').text
    assert '/students<' in xml
    assert '/students/portal' not in xml
    assert '/bca/manage' not in xml
    assert client.get('/api/bca/cases').status_code==401


def test_no_public_student_directory_and_hod_department_scope(client,login):
    token,pwd=import_one(client,login)
    assert client.get('/api/bca/students').status_code==200
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as outsider:
        csrf=login(outsider,'principal')
        assert outsider.get('/api/bca/students').status_code==403
        assert outsider.get('/api/bca/cases').status_code==403
        assert outsider.post('/api/bca/students/import',headers={'X-CSRF-Token':csrf},files={'file':('x.csv',b'usn,full_name,branch,semester\n1NC24BCA111,Someone Else,Computer Applications,2','text/csv')}).status_code==403


def test_admin_cannot_create_incomplete_student(client,login):
    token=login(client,'admin')
    data={'username':'1nc24bca555','display_name':'New Student Example','role':'student',
          'department':'Computer Applications','password':'GeneratedStrongPassword1234!'}
    response=client.post('/api/users',headers={'X-CSRF-Token':token},json=data)
    assert response.status_code==422
    with DBSession() as db:
        assert db.query(User).filter(User.username=='1nc24bca555').first() is None


def test_cs_usn_cannot_be_assigned_to_computer_applications(client,login):
    token=login(client,'admin')
    csv=b'usn,full_name,branch,semester\n1NC24CS999,Student Example,Computer Applications,3\n'
    imported=client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={
        'file':('students.csv',csv,'text/csv')})
    assert imported.status_code==422
    assert 'identifies Computer Science & Engineering' in imported.text
    with DBSession() as db:
        assert db.query(User).filter(User.username=='1nc24cs999').first() is None

    cse_csv=b'usn,full_name,branch,semester\n1NC24CS998,Student Example,Computer Science & Engineering,3\n'
    imported=client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={
        'file':('students.csv',cse_csv,'text/csv')})
    assert imported.status_code==200,imported.text
    from app.student_profiles import FacultyUpdate, faculty_edit
    from fastapi import HTTPException
    with DBSession() as db:
        admin=db.query(User).filter(User.username=='admin').one()
        student=db.query(User).filter(User.username=='1nc24cs998').one()
        try:
            faculty_edit('1NC24CS998',FacultyUpdate(full_name='Student Example',
                branch='Computer Applications',semester=3),admin,db)
        except HTTPException as exc:
            assert exc.status_code==422
        else:
            raise AssertionError('A CS-coded student was reassigned to Computer Applications.')
        db.rollback()
        assert student.department=='Computer Science & Engineering'


def test_admin_password_reset_requires_student_password_change(client,login):
    from app.student_models import BCAStudent
    import_one(client,login)
    admin_token=login(client,'admin')
    with DBSession() as db:
        student=db.query(User).filter(User.username=='1nc24bca001').one()
        student_id=student.id
    reset=client.patch(f'/api/users/{student_id}',headers={'X-CSRF-Token':admin_token},
        json={'password':'ResetBCAStudentPassword2026!'})
    assert reset.status_code==200,reset.text
    with DBSession() as db:
        student=db.query(BCAStudent).filter(BCAStudent.user_id==student_id).one()
        assert student.must_change_password is True


def test_csv_import_rejects_spreadsheet_formulas(client,login):
    prepare_bca()
    token=login(client,'staff')
    malicious=bytes([10]).join([b'usn,full_name,branch,semester',b'1NC24BCA555,=Dangerous Formula,Computer Applications,3',b''])
    response=client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},
        files={'file':('roster.csv',malicious,'text/csv')})
    assert response.status_code==422,response.text


def test_browser_favicon_compatibility(client):
    response=client.get('/favicon.ico',follow_redirects=False)
    assert response.status_code==302
    assert response.headers['location']=='/static/ncet-brand.png'
    assert client.get('/favicon.ico').status_code==200
