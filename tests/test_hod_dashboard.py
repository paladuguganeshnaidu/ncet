"""HOD tracking dashboards: real timestamps, department scoping, full counts and no blobs."""
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import DBSession, User, utcnow
from app.taskflow import (TaskBatch, TaskItem, TaskEvent, TaskSubmission, TaskDecision)

PDF=b'%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF'
RULE=[{'id':'heading','title':'Report header','type':'required_heading',
       'required':True,'value':'Report','instructions':''}]

def batch(client,csrf,number=3):
    response=client.post('/api/tasks/batches',
       data={'title':'HOD dashboard test batch'},
       files=[('files',(f'reference_{i}.pdf',PDF,'application/pdf')) for i in range(number)],
       headers={'X-CSRF-Token':csrf})
    assert response.status_code==201,response.text
    return [x['id'] for x in client.get('/api/tasks').json()['items']]

def staff_id():
    with DBSession() as db:
        return db.query(User).filter(User.username=='staff').one().id

def assign(client,csrf,task):
    result=client.post('/api/tasks/assign',headers={'X-CSRF-Token':csrf},
        json={'task_ids':[task],'staff_id':staff_id(),
              'notes':'Prepare academic final records using the supplied PDF.',
              'rules':RULE,'deadline':(utcnow()+timedelta(days=2)).isoformat()})
    assert result.status_code==200,result.text

def test_empty_dashboard_and_role_scoping(client,login):
    assert client.get('/api/tasks/dashboard').status_code==401
    hod=login(client,'hod')
    result=client.get('/api/tasks/dashboard')
    assert result.status_code==200,result.text
    body=result.json()
    assert body['counts']=={'total':0,'working':0,'reviewing':0,'approved':0,'overdue':0,'unassigned':0}
    assert body['tasks']==[] and body['activity']==[] and body['staff']==[]
    batch(client,hod,1)
    assert client.get('/api/tasks/dashboard').json()['counts']['total']==1
    with TestClient(app) as other:
        login(other,'hod2')
        response=other.get('/api/tasks/dashboard')
        assert response.status_code==200
        assert response.json()['counts']['total']==0
        assert response.json()['activity']==[]
    for username in ('staff','principal','iqac','admin'):
        with TestClient(app) as other:
            login(other,username)
            assert other.get('/api/tasks/dashboard').status_code==403,username

def test_assignment_progress_and_real_approval_history(client,login):
    hod=login(client,'hod')
    ids=batch(client,hod,3)
    assign(client,hod,ids[0]);assign(client,hod,ids[1])
    assert client.post(f'/api/tasks/{ids[1]}/hold',params={'hold':'true'},
                       headers={'X-CSRF-Token':hod}).status_code==200
    with TestClient(app) as staff:
        staff_token=login(staff,'staff')
        submitted=staff.post(f'/api/tasks/{ids[0]}/submit',
            headers={'X-CSRF-Token':staff_token},
            files={'file':('finished.pdf',PDF,'application/pdf')})
        assert submitted.status_code==201
    with DBSession() as db:
        row=db.get(TaskItem,ids[0])
        row.state='awaiting_hod'
        row.updated_at=utcnow()
        db.commit()
    before=client.get('/api/tasks/dashboard').json()
    assert before['counts']=={'total':3,'working':1,'reviewing':1,'approved':0,'overdue':0,'unassigned':1}
    one=next(x for x in before['tasks'] if x['id']==ids[0])
    assert one['submitted_at'] is not None
    assert one['approved_at'] is None
    assert one['staff']=='NCET staff'
    assert any(e['event']=='submitted' and e['actor']=='NCET staff' for e in one['history'])
    response=client.post(f'/api/tasks/{ids[0]}/decide',headers={'X-CSRF-Token':hod},
         json={'decision':'approved','note':'Document inspected and content meets requirements.'})
    assert response.status_code==200,response.text
    after=client.get('/api/tasks/dashboard').json()
    assert after['counts']=={'total':3,'working':1,'reviewing':0,'approved':1,'overdue':0,'unassigned':1}
    one=next(x for x in after['tasks'] if x['id']==ids[0])
    assert one['approved_at'] and one['submitted_at']
    assert one['approved_at']>=one['submitted_at']
    assert any(e['event']=='approved' and e['actor']=='NCET hod' for e in one['history'])
    assert len(after['daily_approvals'])==1
    assert after['staff'][0]['approved']==1
    with DBSession() as db:
        names={e.event for e in db.query(TaskEvent).filter(TaskEvent.task_id==ids[0])}
        assert {'created','assigned','submitted','approved'}.issubset(names)

def test_overdue_and_timestamped_changes(client,login):
    token=login(client,'hod')
    ids=batch(client,token,2)
    assign(client,token,ids[0])
    with DBSession() as db:
        row=db.get(TaskItem,ids[0]);row.deadline=utcnow()-timedelta(minutes=35)
        db.commit()
    snapshot=client.get('/api/tasks/dashboard').json()
    assert snapshot['counts']['overdue']==1
    task=next(x for x in snapshot['tasks'] if x['id']==ids[0])
    assert task['overdue']
    assert task['deadline']
    assert task['history'][0]['event']=='assigned'
    assert all(e['at'].endswith('+00:00') for e in task['history'])
    status=client.post(f'/api/tasks/{ids[0]}/hold',params={'hold':'true'},
                       headers={'X-CSRF-Token':token})
    assert status.status_code==200
    update=client.patch(f'/api/tasks/{ids[0]}/deadline',
        json={'deadline':(utcnow()+timedelta(days=3)).isoformat()},
        headers={'X-CSRF-Token':token})
    assert update.status_code==200
    snapshot=client.get('/api/tasks/dashboard').json()
    assert snapshot['counts']['overdue']==0
    assert {'on_hold','deadline_changed'}.issubset(
        {e['event'] for e in next(x for x in snapshot['tasks'] if x['id']==ids[0])['history']})

def test_historical_records_are_not_fabricated(client,login):
    token=login(client,'hod')
    task_id=batch(client,token,1)[0]
    with DBSession() as db:
        item=db.get(TaskItem,task_id)
        item.assigned_to=staff_id()
        item.state='approved'
        task_time=utcnow()-timedelta(days=4)
        db.query(TaskEvent).filter(TaskEvent.task_id==task_id).delete()
        db.add(TaskSubmission(task_id=task_id,uploaded_by=item.assigned_to,
            revision=1,filename='historical.pdf',content=PDF,created_at=task_time))
        db.add(TaskDecision(task_id=task_id,actor_id=db.query(User).filter(User.username=='hod').first().id,
            decision='approved',note='Historical staff document approved.',
            created_at=task_time+timedelta(hours=1)))
        db.commit()
    response=client.get('/api/tasks/dashboard')
    assert response.status_code==200,response.text
    row=response.json()['tasks'][0]
    assert row['submitted_at'] and row['approved_at']
    assert len(row['history'])==2
    assert {'submitted','approved'}=={x['event'] for x in row['history']}

def test_counts_not_truncated_to_recent_task_listing(client,login):
    token=login(client,'hod')
    with DBSession() as db:
        hod=db.query(User).filter(User.username=='hod').one()
        batch=TaskBatch(department=hod.department,title='Large QA task cohort',created_by=hod.id)
        db.add(batch);db.flush()
        for i in range(505):
            db.add(TaskItem(batch_id=batch.id,department=hod.department,
                filename=f'cohort_{i:03d}.pdf',reference_pdf=PDF))
        db.commit()
    result=client.get('/api/tasks/dashboard')
    assert result.status_code==200,result.text
    body=result.json()
    assert body['counts']['total']==505
    assert body['counts']['unassigned']==505
    assert len(body['tasks'])==500
    assert body['task_list_truncated'] is True
    # UI does not expose source PDFs or secret payloads.
    assert 'reference_pdf' not in result.text
    assert 'content' not in body['tasks'][0]


def test_server_side_search_status_and_pagination_across_department(client,login):
    token=login(client,'hod')
    with DBSession() as db:
        hod=db.query(User).filter(User.username=='hod').one()
        staff=db.query(User).filter(User.username=='staff').one()
        group=TaskBatch(department=hod.department,title='Pagination and search test',
                        created_by=hod.id)
        db.add(group);db.flush()
        # Make the distinctive assigned task the oldest, outside the first page.
        old=utcnow()-timedelta(days=100)
        db.add(TaskItem(batch_id=group.id,department=hod.department,
            filename='Unique_Older_Academic_Record.pdf',reference_pdf=PDF,
            assigned_to=staff.id,assigned_by=hod.id,state='approved',updated_at=old))
        for index in range(505):
            db.add(TaskItem(batch_id=group.id,department=hod.department,
                filename=f'common_record_{index:03d}.pdf',reference_pdf=PDF))
        db.commit()
    initial=client.get('/api/tasks/dashboard')
    assert initial.status_code==200,initial.text
    summary=initial.json()
    assert summary['counts']['total']==506
    assert len(summary['tasks'])==500
    assert summary['task_list_total']==506
    assert summary['task_list_truncated'] is True
    # Staff workload includes the older assigned task, not only the page.
    staff_row=next(x for x in summary['staff'] if x['id']==staff_id())
    assert staff_row['total']==1 and staff_row['approved']==1

    page=client.get('/api/tasks/dashboard',params={'offset':500,'limit':50}).json()
    assert page['task_list_offset']==500 and page['task_list_total']==506
    assert len(page['tasks'])==6
    assert any(x['file']=='Unique_Older_Academic_Record.pdf' for x in page['tasks'])
    searched=client.get('/api/tasks/dashboard',params={
        'status':'approved','search':'Unique_Older','staff_id':staff_id(),'limit':10})
    assert searched.status_code==200,searched.text
    rows=searched.json()
    assert rows['counts']['total']==506
    assert rows['task_list_total']==1
    assert len(rows['tasks'])==1
    assert rows['tasks'][0]['file']=='Unique_Older_Academic_Record.pdf'

    empty=client.get('/api/tasks/dashboard',params={'status':'reviewing'}).json()
    assert empty['task_list_total']==0 and empty['counts']['total']==506
    assert client.get('/api/tasks/dashboard',params={'limit':501}).status_code==422
    with TestClient(app) as another:
        login(another,'hod2')
        assert another.get('/api/tasks/dashboard',params={'search':'Unique_Older'}).json()['task_list_total']==0


def test_extended_deadline_updated_date_and_sort_filters(client,login):
    token=login(client,'hod')
    ids=batch(client,token,3)
    assign(client,token,ids[0])
    current=utcnow()
    with DBSession() as db:
        first=db.get(TaskItem,ids[0])
        first.deadline=current+timedelta(days=2)
        first.updated_at=current-timedelta(days=3)
        second=db.get(TaskItem,ids[1])
        second.updated_at=current-timedelta(days=12)
        last=db.get(TaskItem,ids[2])
        last.updated_at=current
        db.commit()
    no_deadline=client.get('/api/tasks/dashboard',params={'deadline_filter':'no_deadline'}).json()
    assert no_deadline['task_list_total']==2
    soon=client.get('/api/tasks/dashboard',params={'deadline_filter':'due_soon'}).json()
    assert soon['task_list_total']==1 and soon['tasks'][0]['id']==ids[0]
    assert client.get('/api/tasks/dashboard',params={'deadline_filter':'due_set'}).json()['task_list_total']==1
    earliest=client.get('/api/tasks/dashboard',params={'sort':'oldest'}).json()['tasks']
    assert earliest[0]['id']==ids[1]
    soon_first=client.get('/api/tasks/dashboard',params={'sort':'due_soon'}).json()['tasks']
    assert soon_first[0]['id']==ids[0]
    recent=client.get('/api/tasks/dashboard',params={
        'from_date':(current-timedelta(days=4)).date().isoformat()}).json()
    assert recent['task_list_total']==2
    assert client.get('/api/tasks/dashboard',params={'sort':'wrong'}).status_code==422
    assert client.get('/api/tasks/dashboard',params={'from_date':'2026-10-20',
        'to_date':'2026-10-10'}).status_code==422
