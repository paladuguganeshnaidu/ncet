"""Integration tests for selected-student deprovisioning and permanent deletion gates.

No live institution data is touched. Fixtures run in disposable test SQLite.
"""
from datetime import timedelta
from fastapi.testclient import TestClient

from app.database import DBSession, User, Session, AuditLog, LoginFailure, utcnow
from app.main import app
from app.security import hash_password
from app.student_models import BCAStudent, StudentCase
from app.student_profiles import StudentShowcase


def create_students(count=3):
    ids = []
    with DBSession() as db:
        for n in range(1, count+1):
            usn=f'1NC24BCA{n:03d}'
            user=User(username=usn.lower(),display_name=f'Student {n} Safe',
                      role='student',department='Computer Applications',
                      active=True,password_hash=hash_password('StrongStudentPassword-123!'))
            db.add(user);db.flush()
            db.add(BCAStudent(user_id=user.id,usn=usn,semester=3,must_change_password=False))
            ids.append((usn,user.id))
        db.commit()
    return ids


def payload(ids,mode='disable'):
    return {'usns':list(ids),'mode':mode}


def preview(client,csrf,ids,mode='disable'):
    return client.post('/api/bca/students/removal/preview',
                       headers={'X-CSRF-Token':csrf},json=payload(ids,mode))


def execute(client,csrf,preview_body,ids,mode='disable',password='SecurePassword-123!',reason='Duplicate student enrollment correction'):
    return client.post('/api/bca/students/removal/execute',headers={'X-CSRF-Token':csrf},
        json={**payload(ids,mode),'preview_token':preview_body['preview_token'],
              'current_password':password,'confirmation':preview_body['confirmation'],
              'reason':reason,'backup_confirmed':mode=='delete'})


def test_disable_selected_revokes_sessions_hides_profiles_and_retains_cases(client,login):
    users=create_students()
    with DBSession() as db:
        person=db.query(User).filter(User.username==users[0][0].lower()).one()
        db.add(StudentShowcase(student_id=person.id,published=True))
        db.add(StudentCase(reference='NCET-BCA-HISTORY',student_id=person.id,
            department='Computer Applications',category='academics',
            subject='Academic concern',description='A legitimate private issue remains.',
            status='submitted'))
        db.commit()
    with TestClient(app) as student:
        response=student.post('/api/auth/login',json={
            'username':users[0][0].lower(),'role':'student','password':'StrongStudentPassword-123!'})
        assert response.status_code==200
        assert student.get('/api/bca/me').status_code==200
        token=login(client,'admin')
        check=preview(client,token,[users[0][0],users[1][0]])
        assert check.status_code==200,check.text
        data=check.json()
        assert data['count']==2 and data['mode']=='disable'
        assert data['items'][0]['published'] is True
        # A typed phrase + recent password + CSRF must precede removal.
        assert client.post('/api/bca/students/removal/execute',json={
            **payload([users[0][0],users[1][0]]),'preview_token':data['preview_token'],
            'confirmation':data['confirmation'],'current_password':'SecurePassword-123!',
            'reason':'Duplicate student enrollment correction'}).status_code==403
        result=execute(client,token,data,[users[0][0],users[1][0]])
        assert result.status_code==200,result.text
        assert result.json()['affected']==2
        assert student.get('/api/bca/me').status_code==401
        assert student.post('/api/auth/login',json={
            'username':users[0][0].lower(),'role':'student','password':'StrongStudentPassword-123!'}).status_code==401
    with DBSession() as db:
        removed=db.query(User).filter(User.id.in_([users[0][1],users[1][1]])).all()
        assert len(removed)==2 and all(u.active is False for u in removed)
        assert db.query(User).filter(User.id==users[2][1]).one().active
        assert not db.query(StudentShowcase).filter_by(student_id=users[0][1]).one().published
        assert db.query(StudentCase).filter_by(reference='NCET-BCA-HISTORY').count()==1
        assert db.query(AuditLog).filter_by(event='bca.students.disable').count()==1
    # Current roster shows inactive for authorized staff; UI hides them by default.
    roster=client.get('/api/bca/students').json()['items']
    assert any(x['usn']==users[0][0] and x['active'] is False for x in roster)


def test_preview_signature_expiry_batch_integrity_confirmation_and_wrong_password(client,login):
    ids=create_students()
    token=login(client,'admin')
    selected=[ids[0][0],ids[1][0]]
    response=preview(client,token,selected)
    assert response.status_code==200
    data=response.json()
    forged=data.copy();forged['preview_token']='a'+data['preview_token'][1:]
    assert execute(client,token,forged,selected).status_code==409
    from app.student_removal import snapshot, Selection, challenge
    with DBSession() as db:
        administrator=db.query(User).filter(User.username=='admin').one()
        session=db.query(Session).filter(Session.user_id==administrator.id).order_by(Session.id.desc()).first()
        info,_=snapshot(db,administrator,Selection(usns=selected))
        expired=data.copy()
        expired['preview_token']=challenge(session,administrator,info,1)
    assert execute(client,token,expired,selected).status_code==409
    wrong=execute(client,token,data,list(reversed(selected)),mode='disable')
    assert wrong.status_code==200,wrong.text  # Canonical sorting ignores display order.
    with DBSession() as db:
        assert db.query(User).filter(User.id==ids[0][1]).one().active is False
    # A stale signed preview fails after record status changes.
    assert execute(client,token,data,selected).status_code==409
    assert preview(client,token,selected,mode='weird').status_code==422
    assert preview(client,token,selected*2).status_code==422
    assert preview(client,token,[ids[0][0]]).status_code==409  # Removed access cannot be replayed.
    assert preview(client,token,[ids[2][0].lower()]).status_code==200
    assert preview(client,token,['1NC99BAD000']).status_code==404
    assert preview(client,token,['not-an-id']).status_code==422
    assert preview(client,token,selected*26).status_code==422


def test_delete_admin_only_no_academic_history_and_atomic_rejection(client,login):
    ids=create_students()
    with DBSession() as db:
        db.add(StudentCase(reference='NCET-BCA-KEEP',student_id=ids[0][1],
            department='Computer Applications',category='academics',
            subject='Valid student issue',description='Keep this record for audit.'))
        db.commit()
    with TestClient(app) as hod:
        hod_csrf=login(hod,'hod')
        # The same institution department is required, as well as role.
        with DBSession() as db:
            db.query(User).filter(User.username=='hod').update({User.department:'Computer Applications'})
            db.commit()
        assert preview(hod,hod_csrf,[ids[0][0]],'delete').status_code==403
        assert preview(hod,hod_csrf,[ids[0][0]],'disable').status_code==200
    for role in ('principal','staff','iqac','hod2'):
        with TestClient(app) as other:
            csrf=login(other,role)
            assert preview(other,csrf,[ids[0][0]]).status_code==403
    token=login(client,'admin')
    p=preview(client,token,[ids[0][0],ids[1][0]],'delete')
    assert p.status_code==200,p.text
    data=p.json()
    assert data['blocked']>=1
    assert 'student_cases' in data['items'][0]['deletion_blockers']
    fail=execute(client,token,data,[ids[0][0],ids[1][0]],'delete')
    assert fail.status_code==409
    with DBSession() as db:
        assert db.query(BCAStudent).filter(BCAStudent.user_id.in_([ids[0][1],ids[1][1]])).count()==2
        assert db.query(StudentCase).filter_by(reference='NCET-BCA-KEEP').count()==1
    clean=preview(client,token,[ids[2][0]],'delete')
    assert clean.status_code==200,clean.text
    d=clean.json()
    assert d['blocked']==0
    badbackup=client.post('/api/bca/students/removal/execute',
       headers={'X-CSRF-Token':token},json={**payload([ids[2][0]],'delete'),
       'preview_token':d['preview_token'],'confirmation':d['confirmation'],
       'current_password':'SecurePassword-123!','reason':'Delete test-only account without history',
       'backup_confirmed':False})
    assert badbackup.status_code==422
    removed=execute(client,token,d,[ids[2][0]],'delete')
    assert removed.status_code==200,removed.text
    assert removed.json()['action']=='delete'
    with DBSession() as db:
        assert db.get(User,ids[2][1]) is None
        assert db.query(BCAStudent).filter_by(user_id=ids[2][1]).first() is None
        assert db.query(User).filter_by(username=ids[0][0].lower()).one().active


def test_preview_drift_reauthentication_throttle_and_role_scope(client,login):
    users=create_students()
    token=login(client,'admin')
    p=preview(client,token,[users[0][0]]).json()
    with DBSession() as db:
        user=db.get(User,users[0][1]);user.display_name='Changed Student Name';db.commit()
    assert execute(client,token,p,[users[0][0]]).status_code==409
    fresh=preview(client,token,[users[0][0]]).json()
    for i in range(5):
        wrong=execute(client,token,fresh,[users[0][0]],password='IncorrectPassword-123!')
        assert wrong.status_code==403,wrong.text
    locked=execute(client,token,fresh,[users[0][0]])
    assert locked.status_code==429
    with DBSession() as db:
        assert db.get(User,users[0][1]).active
        assert db.query(LoginFailure).filter(LoginFailure.username.like('student-remove:%')).count()==5


def test_hod_department_boundary_and_non_student_usn(client,login):
    ids=create_students()
    token=login(client,'hod')
    assert preview(client,token,[ids[0][0]]).status_code==403
    with DBSession() as db:
        db.query(User).filter(User.username=='hod').update({User.department:'Computer Applications'})
        db.commit()
    p=preview(client,token,[ids[0][0]])
    assert p.status_code==200,p.text
    assert execute(client,token,p.json(),[ids[0][0]]).status_code==200
    # Transfers or changes between preview and mutation require fresh authorization.
    with DBSession() as db:
        person=db.get(User,ids[1][1]);person.department='Mechanical Engineering';db.commit()
    assert preview(client,token,[ids[1][0]]).status_code==404
