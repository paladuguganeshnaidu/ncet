"""Security, routing and workflow regression for NCET private complaint management.

Runs against isolated per-test SQLite fixtures; does not touch production users.
"""
from datetime import timedelta
from fastapi.testclient import TestClient
from app.database import DBSession, User, utcnow
from app.main import app
from app.security import hash_password
from app.student_models import BCAStudent, StudentCase, StudentCaseMessage


def setup_cases():
    with DBSession() as db:
        hod=db.query(User).filter_by(username='hod').one()
        hod.department='Computer Applications'
        person=User(username='1nc24bca986',display_name='Student Tester',
            role='student',department='Computer Applications',
            password_hash=hash_password('StudentTesterPassword123!'),active=True)
        foreign=User(username='1nc24bca987',display_name='Other Student',
            role='student',department='Computer Applications',
            password_hash=hash_password('StudentTesterPassword123!'),active=True)
        db.add_all([person,foreign]);db.flush()
        for u in (person,foreign):
            db.add(BCAStudent(user_id=u.id,usn=u.username.upper(),semester=3,
                              must_change_password=False))
        now=utcnow()
        cases=[
            ('NEWA','submitted','academics',2,person.id),
            ('WAIT','in_review','examinations',9,person.id),
            ('ANSWER','in_review','facilities',1,person.id),
            ('DONE','resolved','fees',12,person.id),
            ('CLOSED','closed','documentation',22,person.id),
            ('FOREIGN','submitted','request',2,foreign.id),
        ]
        for key,status,category,age,student in cases:
            record=StudentCase(reference='NCET-BCA-'+key,student_id=student,
                department='Computer Applications',category=category,
                subject='A private academic concern '+key,
                description='Private details should never appear in public output.',
                status=status,created_at=now-timedelta(days=age),
                updated_at=now-timedelta(days=age))
            db.add(record);db.flush()
            if key=='WAIT':
                db.add(StudentCaseMessage(case_id=record.id,actor_id=person.id,
                    body='Student provided the requested update.'))
            if key=='ANSWER':
                db.add(StudentCaseMessage(case_id=record.id,actor_id=person.id,
                    body='Student asked a question.'))
                db.add(StudentCaseMessage(case_id=record.id,actor_id=hod.id,
                    body='HOD answered the question.'))
        db.commit()


def student_client():
    c=TestClient(app)
    response=c.post('/api/auth/login',json={'username':'1nc24bca986',
        'role':'student','password':'StudentTesterPassword123!'})
    assert response.status_code==200,response.text
    return c,response.json()['csrf']


def test_canonical_route_authentication_headers_and_static_bypass(client,login):
    assert client.get('/complaints').status_code==401
    assert client.get('/bca/complaints').status_code==401
    assert client.get('/api/bca/cases').status_code==401
    for path in ('/static/complaints-dashboard.html','/static/bca-oversight.html',
                 '/static/bca-management.html'):
        denial=client.get(path)
        assert denial.status_code==404,path
    setup_cases()
    login(client,'hod')
    for route in ('/complaints','/bca/complaints'):
        result=client.get(route)
        assert result.status_code==200 and 'Complaint management' in result.text
        assert result.headers['cache-control']=='no-store'
        assert 'noindex' in result.headers['x-robots-tag']
        assert 'frame-ancestors' in result.headers['content-security-policy']
        assert result.headers['x-frame-options']=='DENY'
    robots=client.get('/robots.txt').text
    assert 'Disallow: /complaints' in robots
    assert '/complaints' not in client.get('/sitemap.xml').text
    with TestClient(app) as principal:
        login(principal,'principal')
        a=principal.get('/complaints',follow_redirects=False)
        assert a.status_code==303 and a.headers['location']=='/bca/oversight'
        summary=principal.get('/api/bca/oversight').json()
        assert summary['cases_total']==6 and 'cases' not in summary
        assert principal.get('/api/bca/cases').status_code==403
    with TestClient(app) as another_hod:
        login(another_hod,'hod2')
        page=another_hod.get('/complaints')
        assert page.status_code==200
        cases=another_hod.get('/api/bca/cases').json()
        assert cases['all_total']==0
        assert another_hod.get('/api/bca/cases/NCET-BCA-WAIT').status_code==404
    for role in ('staff','admin','iqac'):
        with TestClient(app) as other:
            login(other,role)
            denial=other.get('/complaints')
            assert denial.status_code==403,role
            assert 'Private details should never appear' not in denial.text
            assert other.get('/api/bca/cases').status_code==403


def test_reply_needed_and_aged_attention_filters(client,login):
    setup_cases()
    csrf=login(client,'hod')
    all_data=client.get('/api/bca/cases').json()
    assert all_data['all_total']==6
    assert all_data['attention_counts']=={'awaiting_reply':3,'older_than_7d':1}
    waiting=client.get('/api/bca/cases',params={'attention':'awaiting_reply'}).json()
    assert waiting['total']==3
    assert all(x['awaiting_reply'] and x['status'] in ('submitted','in_review')
               for x in waiting['items'])
    age=client.get('/api/bca/cases',params={'attention':'older_than_7d'}).json()
    assert age['total']==1 and age['items'][0]['reference']=='NCET-BCA-WAIT'
    assert age['items'][0]['older_than_7d']
    assert not any('description' in x for x in all_data['items'])
    assert client.get('/api/bca/cases',params={'attention':'bad'}).status_code==422
    assert client.get('/api/bca/cases',params={'to_date':'9999-12-31'}).status_code==200
    assert client.get('/api/bca/cases',params={'limit':101}).status_code==422

    ref='NCET-BCA-NEWA'
    without_csrf=client.post('/api/bca/cases/'+ref+'/messages',json={'message':'Review started.'})
    assert without_csrf.status_code==403
    reply=client.post('/api/bca/cases/'+ref+'/messages',
         headers={'X-CSRF-Token':csrf},json={'message':'We are now checking your request.'})
    assert reply.status_code==200,reply.text
    new_wait=client.get('/api/bca/cases',params={'attention':'awaiting_reply'}).json()
    assert new_wait['total']==2
    assert all(x['reference']!=ref for x in new_wait['items'])

    change=client.patch('/api/bca/cases/'+ref+'/status',
           headers={'X-CSRF-Token':csrf},
           json={'status':'resolved','note':'The academic concern is resolved.'})
    assert change.status_code==200
    closed=client.patch('/api/bca/cases/'+ref+'/status',
           headers={'X-CSRF-Token':csrf},
           json={'status':'closed','note':'Resolution was confirmed with the student.'})
    assert closed.status_code==200
    assert client.post('/api/bca/cases/'+ref+'/messages',
           headers={'X-CSRF-Token':csrf},json={'message':'A late reply'}).status_code==409
    assert client.get('/api/bca/cases',params={'attention':'awaiting_reply'}).json()['total']==2


def test_cross_student_isolation_and_case_fetch_scope(client,login):
    setup_cases()
    login(client,'hod')
    assert client.get('/api/bca/cases/NCET-BCA-WAIT').status_code==200
    with student_client()[0] as student:
        own=student.get('/api/bca/cases').json()
        assert own['all_total']==5
        assert all('student' not in x for x in own['items'])
        assert student.get('/api/bca/cases/NCET-BCA-FOREIGN').status_code==404
        assert student.get('/api/bca/cases/NCET-BCA-NONEXISTENT').status_code==404
        assert student.get('/api/bca/cases/NCET-BCA-WAIT').status_code==200
        assert student.get('/complaints').status_code==403
