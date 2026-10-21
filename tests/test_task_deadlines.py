"""HOD-assigned task deadlines, timezone validation, scoping and audit regressions."""
from datetime import timedelta
from fastapi.testclient import TestClient
from app.database import DBSession, User, AuditLog, utcnow
from app.taskflow import TaskItem,TaskNotification
from app.main import app

PDF=b'%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF'
RULE=[{'id':'heading','title':'Mandatory heading','type':'required_heading',
       'required':True,'value':'Report','instructions':''}]

def create_task(client,login):
    csrf=login(client,'hod')
    r=client.post('/api/tasks/batches',headers={'X-CSRF-Token':csrf},
       data={'title':'Academic audit task batch'},
       files={'files':('reference.pdf',PDF,'application/pdf')})
    assert r.status_code==201,r.text
    task=client.get('/api/tasks').json()['items'][0]['id']
    with DBSession() as db:
        staff=db.query(User).filter(User.username=='staff').one()
        staff_id=staff.id
    return csrf,task,staff_id

def assign(client,csrf,task,staff_id,deadline=None):
    body={'task_ids':[task],'staff_id':staff_id,
        'notes':'Complete the academic reference document and submit a signed PDF.',
        'rules':RULE}
    if deadline is not None:body['deadline']=deadline
    return client.post('/api/tasks/assign',json=body,headers={'X-CSRF-Token':csrf})

def update(client,csrf,task,deadline):
    return client.patch(f'/api/tasks/{task}/deadline',
        json={'deadline':deadline},headers={'X-CSRF-Token':csrf})

def test_hod_assigns_deadline_to_staff_and_notifications(client,login):
    csrf,task,staff_id=create_task(client,login)
    future=(utcnow()+timedelta(days=4)).replace(microsecond=0).isoformat()
    result=assign(client,csrf,task,staff_id,future)
    assert result.status_code==200,result.text
    row=client.get('/api/tasks').json()['items'][0]
    assert row['deadline']==future
    assert row['overdue'] is False
    with TestClient(app) as member:
        login(member,'staff')
        staff_task=member.get('/api/tasks').json()['items'][0]
        assert staff_task['deadline']==future
        assert staff_task['overdue'] is False
        inbox=member.get('/api/tasks/notifications/inbox').json()
        assert 'due' in inbox['items'][0]['text']
        assert 'reference.pdf' in inbox['items'][0]['text']
    with DBSession() as db:
        assert db.query(AuditLog).filter(AuditLog.event=='task.assigned').count()==1

def test_deadlines_normalized_editable_and_can_be_cleared(client,login):
    csrf,task,staff_id=create_task(client,login)
    assert assign(client,csrf,task,staff_id).status_code==200
    assert client.get('/api/tasks').json()['items'][0]['deadline'] is None
    from datetime import timezone
    tz=timezone(timedelta(hours=5,minutes=30))
    india=(utcnow()+timedelta(days=3)).astimezone(tz).replace(microsecond=0).isoformat()
    updated=update(client,csrf,task,india)
    assert updated.status_code==200,updated.text
    assert updated.json()['changed'] is True
    assert updated.json()['deadline'].endswith('+00:00')
    assert client.get('/api/tasks').json()['items'][0]['deadline']==updated.json()['deadline']
    repeat=update(client,csrf,task,india)
    assert repeat.status_code==200 and not repeat.json()['changed']
    removed=update(client,csrf,task,None)
    assert removed.status_code==200 and removed.json()=={'deadline':None,'changed':True}
    assert client.get('/api/tasks').json()['items'][0]['deadline'] is None
    with DBSession() as db:
        assert db.query(AuditLog).filter(AuditLog.event=='task.deadline_updated').count()==2
        assert db.query(TaskNotification).filter(TaskNotification.task_id==task).count()==3

def test_past_naive_invalid_and_extreme_deadlines_rejected(client,login):
    csrf,task,staff_id=create_task(client,login)
    past=(utcnow()-timedelta(minutes=1)).isoformat()
    naive=(utcnow()+timedelta(days=1)).replace(tzinfo=None).isoformat()
    far=(utcnow()+timedelta(days=800)).isoformat()
    for value in (past,naive,far):
        assert assign(client,csrf,task,staff_id,value).status_code==422,value
    assert assign(client,csrf,task,staff_id).status_code==200
    for value in (past,naive,far):
        assert update(client,csrf,task,value).status_code==422,value
    assert client.get('/api/tasks').json()['items'][0]['deadline'] is None

def test_deadline_access_scope_and_finished_task_integrity(client,login):
    csrf,task,staff_id=create_task(client,login)
    valid=(utcnow()+timedelta(days=2)).isoformat()
    # An unassigned task cannot be given a deadline via the edit API.
    assert update(client,csrf,task,valid).status_code==409
    assert assign(client,csrf,task,staff_id).status_code==200
    assert client.patch(f'/api/tasks/{task}/deadline',json={'deadline':valid}).status_code==403
    with TestClient(app) as staff:
        st=login(staff,'staff')
        assert update(staff,st,task,valid).status_code==403
    with TestClient(app) as outside:
        other=login(outside,'hod2')
        assert update(outside,other,task,valid).status_code==404
    with TestClient(app) as admin:
        a=login(admin,'admin')
        assert update(admin,a,task,valid).status_code==403
    with DBSession() as db:
        obj=db.get(TaskItem,task);obj.state='approved';db.commit()
    assert update(client,csrf,task,valid).status_code==409

def test_overdue_staff_visibility_and_late_submission_still_permitted(client,login):
    csrf,task,staff_id=create_task(client,login)
    soon=(utcnow()+timedelta(days=1)).isoformat()
    assert assign(client,csrf,task,staff_id,soon).status_code==200
    with DBSession() as db:
        obj=db.get(TaskItem,task)
        obj.deadline=utcnow()-timedelta(minutes=30)
        db.commit()
    with TestClient(app) as staff:
        token=login(staff,'staff')
        row=staff.get('/api/tasks').json()['items'][0]
        assert row['overdue'] is True
        assert row['deadline'].endswith('+00:00')
        submit=staff.post(f'/api/tasks/{task}/submit',
             headers={'X-CSRF-Token':token},
             files={'file':('completed.pdf',PDF,'application/pdf')})
        assert submit.status_code==201,submit.text
