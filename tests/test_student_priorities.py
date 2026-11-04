"""Private HOD student priorities: department scope, persistence and sort order."""
from app.database import DBSession, User, AuditLog
from app.security import hash_password
from app.student_models import BCAStudent, StudentPriority


def make_student(usn, department='Computer Science & Engineering'):
    with DBSession() as db:
        user=User(username=usn.lower(),display_name='Student '+usn[-3:],role='student',
                  department=department,active=True,
                  password_hash=hash_password('StrongStudentPassword-123!'))
        db.add(user);db.flush()
        db.add(BCAStudent(user_id=user.id,usn=usn,semester=3,must_change_password=False))
        db.commit()
        return user.id


def test_hod_priorities_sort_first_and_clear_back_to_usn_order(client,login):
    usns=['1NC24CS901','1NC24CS902','1NC24CS903','1NC24CS904','1NC24CS905']
    ids=[make_student(usn) for usn in usns]
    csrf=login(client,'hod')

    plain=client.get('/api/bca/students').json()['items']
    assert [row['usn'] for row in plain]==usns
    assert all(row['priority_stars']==0 for row in plain)

    for usn,stars in ((usns[1],2),(usns[2],1),(usns[3],3),(usns[4],1)):
        response=client.put(f'/api/bca/students/{usn}/priority',headers={'X-CSRF-Token':csrf},
                            json={'stars':stars})
        assert response.status_code==200,response.text
        assert response.json()['priority_stars']==stars

    ranked=client.get('/api/bca/students').json()['items']
    assert [row['usn'] for row in ranked]==[usns[3],usns[1],usns[2],usns[4],usns[0]]
    assert [row['priority_stars'] for row in ranked]==[3,2,1,1,0]

    # Clicking the same rating clears it; unrated students keep USN order.
    cleared=client.put(f'/api/bca/students/{usns[1]}/priority',headers={'X-CSRF-Token':csrf},
                       json={'stars':0})
    assert cleared.status_code==200,cleared.text
    assert [row['usn'] for row in client.get('/api/bca/students').json()['items']]==[
        usns[3],usns[2],usns[4],usns[0],usns[1]]
    with DBSession() as db:
        assert db.query(StudentPriority).filter(StudentPriority.student_id==ids[1]).count()==0
        assert db.query(AuditLog).filter_by(event='student.priority.updated').count()==5


def test_student_priorities_are_hod_only_and_never_returned_to_staff_or_admin(client,login):
    usn='1NC24CS911'
    make_student(usn)
    hod_csrf=login(client,'hod')
    assert client.put(f'/api/bca/students/{usn}/priority',json={'stars':2}).status_code==403
    assert client.put(f'/api/bca/students/{usn}/priority',headers={'X-CSRF-Token':hod_csrf},
                      json={'stars':4}).status_code==422
    assert client.put(f'/api/bca/students/{usn}/priority',headers={'X-CSRF-Token':hod_csrf},
                      json={'stars':2}).status_code==200

    # A HOD assigned to another branch cannot set or retrieve this priority.
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as other_hod:
        token=login(other_hod,'hod2')
        assert other_hod.put(f'/api/bca/students/{usn}/priority',
            headers={'X-CSRF-Token':token},json={'stars':3}).status_code==404
        assert all(row['usn']!=usn for row in other_hod.get('/api/bca/students').json()['items'])

    # Staff and admins can read their enrollment views, but not the private HOD rating.
    staff_csrf=login(client,'staff')
    staff_rows=client.get('/api/bca/students').json()['items']
    assert next(row for row in staff_rows if row['usn']==usn).get('priority_stars') is None
    assert client.put(f'/api/bca/students/{usn}/priority',headers={'X-CSRF-Token':staff_csrf},
                      json={'stars':3}).status_code==403
    login(client,'admin')
    admin_rows=client.get('/api/bca/students').json()['items']
    assert next(row for row in admin_rows if row['usn']==usn).get('priority_stars') is None


def test_private_priority_does_not_block_approved_permanent_student_removal(client,login):
    usn='1NC24CS921'
    student_id=make_student(usn)
    hod_csrf=login(client,'hod')
    rated=client.put(f'/api/bca/students/{usn}/priority',headers={'X-CSRF-Token':hod_csrf},
                     json={'stars':3})
    assert rated.status_code==200,rated.text

    admin_csrf=login(client,'admin')
    selection={'usns':[usn],'mode':'delete'}
    preview=client.post('/api/bca/students/removal/preview',headers={'X-CSRF-Token':admin_csrf},
                        json=selection)
    assert preview.status_code==200,preview.text
    assert preview.json()['blocked']==0
    result=client.post('/api/bca/students/removal/execute',headers={'X-CSRF-Token':admin_csrf},json={
        **selection,'preview_token':preview.json()['preview_token'],
        'confirmation':preview.json()['confirmation'],'current_password':'SecurePassword-123!',
        'reason':'Remove temporary student test account','backup_confirmed':True})
    assert result.status_code==200,result.text
    with DBSession() as db:
        assert db.query(User).filter(User.id==student_id).first() is None
        assert db.query(StudentPriority).filter(StudentPriority.student_id==student_id).count()==0
