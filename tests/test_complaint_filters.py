"""Private complaint desk regression: scoped metrics, filtering, pagination and HOD access."""
from datetime import timedelta
from fastapi.testclient import TestClient
from app.database import DBSession, User, utcnow
from app.main import app
from app.security import hash_password
from app.student_models import BCAStudent, StudentCase


def seed_cases():
    with DBSession() as db:
        hod=db.query(User).filter_by(username='hod').one()
        hod.department='Computer Applications'
        student=User(username='1nc24bca889',display_name='Student One',role='student',
                     department='Computer Applications',
                     password_hash=hash_password('StudentTestPassword1234!'),active=True)
        other=User(username='1nc24bca890',display_name='Student Two',role='student',
                   department='Computer Applications',
                   password_hash=hash_password('StudentTestPassword1234!'),active=True)
        db.add_all([student,other]);db.flush()
        db.add(BCAStudent(user_id=student.id,usn=student.username.upper(),semester=3,must_change_password=False))
        db.add(BCAStudent(user_id=other.id,usn=other.username.upper(),semester=3,must_change_password=False))
        current=utcnow()
        categories=['academics','facilities','examinations']
        statuses=['submitted','in_review','resolved','closed']
        for i in range(56):
            db.add(StudentCase(reference=f'NCET-BCA-TEST{i:04d}',student_id=student.id,
                department='Computer Applications',category=categories[i%3],
                subject=f'Campus issue {i:03d}',description='Private student case data.',
                status=statuses[i%4],created_at=current-timedelta(days=i),
                updated_at=current-timedelta(days=i//2)))
        db.add(StudentCase(reference='NCET-BCA-OTHER',student_id=other.id,
            department='Computer Applications',category='faculty',
            subject='Other student concern',description='Other student private data.',
            status='submitted',created_at=current,updated_at=current))
        db.commit()


def test_hod_complaints_filtered_paginated_with_stable_counts(client,login):
    seed_cases()
    login(client,'hod')
    page=client.get('/bca/complaints')
    assert page.status_code==200
    assert 'Complaint management' in page.text
    assert 'noindex' in page.headers['x-robots-tag']
    assert 'Disallow: /bca/complaints' in client.get('/robots.txt').text
    response=client.get('/api/bca/cases')
    assert response.status_code==200,response.text
    data=response.json()
    assert len(data['items'])==30
    assert data['all_total']==57 and data['total']==57
    assert data['has_more'] is True
    assert data['counts']=={'submitted':15,'in_review':14,'resolved':14,'closed':14}
    assert data['categories']['faculty']==1
    assert data['items'][0]['student']['name']=='Student Two'
    assert 'Private student case data.' not in response.text
    later=client.get('/api/bca/cases',params={'offset':30,'limit':30}).json()
    assert len(later['items'])==27 and not later['has_more']
    refs=[x['reference'] for x in data['items']+later['items']]
    assert len(set(refs))==57
    approved=client.get('/api/bca/cases',params={'status':'resolved','category':'academics',
        'sort':'oldest','limit':100}).json()
    assert approved['counts']==data['counts']
    assert approved['all_total']==57
    assert all(x['status']=='resolved' and x['category']=='academics' for x in approved['items'])
    assert approved['total']==len(approved['items'])
    found=client.get('/api/bca/cases',params={'search':'Campus issue 030'}).json()
    assert found['total']==1 and found['items'][0]['reference']=='NCET-BCA-TEST0030'
    latest=client.get('/api/bca/cases',params={'from_date':utcnow().date().isoformat()}).json()
    assert latest['total']>=1
    invalid=client.get('/api/bca/cases',params={'from_date':'2026-10-20','to_date':'2026-10-10'})
    assert invalid.status_code==422
    assert client.get('/api/bca/cases',params={'limit':101}).status_code==422
    assert client.get('/api/bca/cases',params={'status':'secret'}).status_code==422


def test_private_complaints_do_not_leak_to_other_students_or_departments(client,login):
    seed_cases()
    login(client,'hod')
    with TestClient(app) as student:
        resp=student.post('/api/auth/login',json={'username':'1nc24bca889',
            'password':'StudentTestPassword1234!','role':'student'})
        assert resp.status_code==200,resp.text
        mine=student.get('/api/bca/cases',params={'limit':100}).json()
        assert mine['all_total']==56 and mine['total']==56
        assert all('student' not in x for x in mine['items'])
        assert not any('OTHER' in x['reference'] for x in mine['items'])
        assert student.get('/bca/complaints').status_code==403
        assert student.get('/api/bca/cases/NCET-BCA-OTHER').status_code==404
    with TestClient(app) as unrelated:
        login(unrelated,'hod2')
        assert unrelated.get('/bca/complaints').status_code==200
        assert unrelated.get('/api/bca/cases').json()['all_total']==0
        assert unrelated.get('/api/bca/cases/NCET-BCA-OTHER').status_code==404
    with TestClient(app) as principal:
        login(principal,'principal')
        access=principal.get('/bca/complaints',follow_redirects=False)
        assert access.status_code==303 and access.headers['location']=='/bca/oversight'
        assert principal.get('/api/bca/cases').status_code==403
        summary=principal.get('/api/bca/oversight').json()
        assert summary['cases_total']==57
        assert 'cases' not in summary
    assert client.get('/api/bca/cases/NCET-BCA-OTHER').status_code==200
