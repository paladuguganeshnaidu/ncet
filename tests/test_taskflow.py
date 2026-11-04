"""Practical HOD task allocation and non-destructive scoring tests."""
import json
from fastapi.testclient import TestClient
from app.database import DBSession,User
from app.taskflow import TaskItem, TaskNotification, TaskSubmission, run_task_once
from app.main import app
from app.ai_gateway import Provider,select_provider

PDF=b'%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF'
RULE=[{'id':'header','title':'Mandatory heading','type':'required_heading','required':True,'value':'Academic Report','instructions':''}]


def _batch(c,csrf,n=2):
    r=c.post('/api/tasks/batches',headers={'X-CSRF-Token':csrf},
         data={'title':'October academic records batch'},
         files=[('files',(f'ref{i}.pdf',PDF,'application/pdf')) for i in range(n)])
    assert r.status_code==201,r.text
    return [x['id'] for x in c.get('/api/tasks').json()['items']]


def _staff_id():
    with DBSession() as db:return db.query(User).filter(User.username=='staff').first().id


def test_hod_bulk_assignment_notifications_and_holds(client,login):
    h=login(client,'hod'); ids=_batch(client,h,3)
    who=_staff_id()
    r=client.post('/api/tasks/assign',json={'task_ids':ids,'staff_id':who,'notes':'Prepare official report with proper headings.', 'rules':RULE},headers={'X-CSRF-Token':h})
    assert r.status_code==200,r.text
    assert r.json()['assigned']==3
    with TestClient(app) as staff:
        s=login(staff,'staff')
        inbox=staff.get('/api/tasks/notifications/inbox').json()
        assert inbox['unread']==3
        nid=inbox['items'][0]['id']
        assert staff.post(f'/api/tasks/notifications/{nid}/read',headers={'X-CSRF-Token':s}).status_code==200
        assert len(staff.get('/api/tasks').json()['items'])==3
        assert staff.get(f'/api/tasks/{ids[0]}/reference').status_code==200
        assert staff.post(f'/api/tasks/{ids[0]}/submit',headers={'X-CSRF-Token':s},files={'file':('done.pdf',PDF,'application/pdf')}).status_code==201
    assert client.post(f'/api/tasks/{ids[1]}/hold',params={'hold':'true'},headers={'X-CSRF-Token':h}).json()['state']=='on_hold'
    assert client.post(f'/api/tasks/{ids[1]}/hold',params={'hold':'false'},headers={'X-CSRF-Token':h}).json()['state']=='assigned'


def test_hod_can_assign_pdf_specific_checklists(client,login):
    hod_csrf=login(client,'hod');ids=_batch(client,hod_csrf,2)
    first=[{'id':'cover','title':'Department cover page','type':'required_phrase','required':True,'value':'Department Cover','instructions':''}]
    second=[{'id':'outcomes','title':'Course outcomes section','type':'required_heading','required':True,'value':'Course Outcomes','instructions':''}]
    payload={'task_ids':ids,'staff_id':_staff_id(),
             'notes':'Complete both PDFs using their individual checklist requirements.',
             'rules_by_task':{str(ids[0]):first,str(ids[1]):second}}
    incomplete={**payload,'rules_by_task':{str(ids[0]):first}}
    assert client.post('/api/tasks/assign',headers={'X-CSRF-Token':hod_csrf},json=incomplete).status_code==422
    response=client.post('/api/tasks/assign',headers={'X-CSRF-Token':hod_csrf},json=payload)
    assert response.status_code==200,response.text
    with TestClient(app) as staff:
        login(staff,'staff')
        assigned={task['id']:task for task in staff.get('/api/tasks').json()['items'] if task['id'] in ids}
    assert assigned[ids[0]]['rules'][0]['value']=='Department Cover'
    assert assigned[ids[1]]['rules'][0]['value']=='Course Outcomes'


def test_permission_department_and_invalid_batch(client,login):
    h=login(client,'hod'); ids=_batch(client,h,1)
    for bad in (0,_staff_id()+10_000):
        r=client.post('/api/tasks/assign',headers={'X-CSRF-Token':h},json={'task_ids':ids,'staff_id':bad,'notes':'Some important task notes to staff.', 'rules':RULE})
        assert r.status_code==403
    assert client.post('/api/tasks/batches',headers={'X-CSRF-Token':h},data={'title':'Uploaded work'},files={'files':('bad.txt',b'x'*20,'text/plain')}).status_code==422
    with TestClient(app) as other:
        login(other,'hod2')
        assert other.get('/api/tasks').json()['items']==[]
        assert other.get(f'/api/tasks/{ids[0]}/reference').status_code==404
        token=other.get('/api/auth/me').json()['csrf']
        assert other.post('/api/tasks/assign',headers={'X-CSRF-Token':token},json={'task_ids':ids,'staff_id':_staff_id(),'notes':'Trying to assign someone else task.','rules':RULE}).status_code==403
    with TestClient(app) as staff:
        s=login(staff,'staff')
        assert staff.post('/api/tasks/assign',headers={'X-CSRF-Token':s},json={'task_ids':ids,'staff_id':_staff_id(),'notes':'Attempted staff assignment','rules':RULE}).status_code==403
        assert staff.get(f'/api/tasks/{ids[0]}/reference').status_code==404


def test_ai_missing_is_manual_review_not_rejection(client,login):
    h=login(client,'hod');id=_batch(client,h,1)[0]
    assert client.post('/api/tasks/assign',headers={'X-CSRF-Token':h},json={'task_ids':[id],'staff_id':_staff_id(), 'notes':'Prepare final document with all specified parts.','rules':RULE}).status_code==200
    with TestClient(app) as staff:
        s=login(staff,'staff')
        assert staff.post(f'/api/tasks/{id}/submit',headers={'X-CSRF-Token':s},files={'file':('final.pdf',PDF,'application/pdf')}).status_code==201
    import app.taskflow as tf
    prior=tf.select_provider
    try:
        tf.select_provider=lambda db:None
        assert run_task_once()
    finally:tf.select_provider=prior
    row=client.get('/api/tasks').json()['items'][0]
    assert row['state']=='manual_review' and row['score'] is None
    assert client.post(f'/api/tasks/{id}/decide',headers={'X-CSRF-Token':h},json={'decision':'approved','note':'I manually inspected the PDF and confirm acceptance.'}).status_code==200
    assert client.get('/api/tasks').json()['items'][0]['state']=='approved'


def test_manual_checklist_requires_specific_heading_and_valid_page_limit():
    from fastapi import HTTPException
    from app.database import DBSession,User
    from app.taskflow import AssignBody,TaskBatch,TaskItem,assign
    with DBSession() as db:
        hod=db.query(User).filter(User.username=='hod').one()
        staff=db.query(User).filter(User.username=='staff').one()
        batch=TaskBatch(title='Manual checklist regression',department=hod.department,created_by=hod.id)
        db.add(batch);db.flush()
        task=TaskItem(batch_id=batch.id,department=hod.department,filename='manual.pdf',reference_pdf=PDF)
        db.add(task);db.flush()
        base={'task_ids':[task.id],'staff_id':staff.id,
              'notes':'Prepare the academic document with the department checklist.'}
        for rules in ([{'id':'heading','title':'Required heading','type':'required_heading','value':''}],
                      [{'id':'max_pages','title':'Maximum pages','type':'max_pages','value':'many'}]):
            try:
                assign(AssignBody(**{**base,'rules':rules}),hod,db)
            except HTTPException as exc:
                assert exc.status_code==422
            else:
                raise AssertionError('Invalid checklist was accepted.')
        accepted=assign(AssignBody(**{**base,'rules':[{'id':'heading','title':'Required heading','type':'required_heading','value':'Approval'}]}),hod,db)
        assert accepted['assigned']==1


def test_task_list_batches_metadata_and_decisions_without_loading_reference_pdfs():
    from sqlalchemy import event
    from app.database import DBSession,engine,User
    from app.taskflow import TaskBatch,TaskDecision,TaskItem,list_tasks
    task_ids=[]
    with DBSession() as db:
        hod=db.query(User).filter(User.username=='hod').one()
        batch=TaskBatch(title='Performance regression batch',department=hod.department,created_by=hod.id)
        db.add(batch);db.flush()
        items=[TaskItem(batch_id=batch.id,department=hod.department,filename=f'perf_{i}.pdf',reference_pdf=PDF)
               for i in range(4)]
        db.add_all(items);db.flush();task_ids=[task.id for task in items]
        for task_id in task_ids:
            db.add_all([
                TaskDecision(task_id=task_id,actor_id=hod.id,decision='needs_correction',note='Please add the missing signature.'),
                TaskDecision(task_id=task_id,actor_id=hod.id,decision='approved',note='Reviewed the final academic document.')])
        db.commit()
    statements=[]
    def capture(_conn,_cursor,statement,_parameters,_context,_executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement.upper())
    event.listen(engine,'before_cursor_execute',capture)
    try:
        with DBSession() as db:
            hod=db.query(User).filter(User.username=='hod').one()
            response=list_tasks(hod,db)
    finally:
        event.remove(engine,'before_cursor_execute',capture)
    task_selects=[sql for sql in statements if 'FROM TASK_ITEMS' in sql]
    decision_selects=[sql for sql in statements if 'FROM TASK_DECISIONS' in sql]
    assert len(task_selects)==1
    assert 'REFERENCE_PDF' not in task_selects[0]
    assert len(decision_selects)==1
    assert len(response['items'])==4
    assert all(len(task['decisions'])==2 for task in response['items'])


def test_scoring_threshold_requires_actual_provider_and_no_uncertainty(client,login,monkeypatch):
    from app import taskflow as tf
    h=login(client,'hod');id=_batch(client,h,1)[0]
    rules=[{'id':f'rule{i}','title':f'Rule number {i}','type':'other','required':False,'value':'','instructions':'Check content'} for i in range(4)]
    r=client.post('/api/tasks/assign',headers={'X-CSRF-Token':h},json={'task_ids':[id],'staff_id':_staff_id(), 'notes':'Complete these four content requirements.', 'rules':rules})
    assert r.status_code==200,r.text
    monkeypatch.setattr(tf,'select_provider',lambda db:Provider('test','test-model','https://api.deepseek.com/chat/completions','unused'))
    from app.verification import Extracted
    monkeypatch.setattr('app.verification.extract_document',lambda *args:Extracted(['Doc content'],1,False,[]))
    def fake_ai(provider,system,payload,max_tokens=2200):
        return {'summary':'Reviewed','evaluations':[{'rule_id':f'rule{i}','result':('pass' if i<fake_ai.passed else 'issue'),'confidence':0.98,'evidence':'Doc content'} for i in range(4)]}
    monkeypatch.setattr(tf,'review_json',fake_ai)
    with TestClient(app) as staff:
        s=login(staff,'staff')
        for num,expected in [(3,'correction_required'),(4,'awaiting_hod')]:
            fake_ai.passed=num
            res=staff.post(f'/api/tasks/{id}/submit',headers={'X-CSRF-Token':s},files={'file':('completed.pdf',PDF,'application/pdf')})
            assert res.status_code==201,res.text
            assert run_task_once()
            item=staff.get('/api/tasks').json()['items'][0]
            assert item['score']==(75 if num==3 else 100)
            assert item['state']==expected


def test_insights_and_in_app_notifications_are_private(client,login):
    h=login(client,'hod');ids=_batch(client,h,2)
    summary=client.get('/api/tasks/insights/summary')
    assert summary.status_code==200 and summary.json()['total']==2
    with TestClient(app) as staff:
        login(staff,'staff')
        assert staff.get('/api/tasks/insights/summary').status_code==403
        assert staff.get('/api/tasks').json()['items']==[]
        assert staff.get('/api/tasks/notifications/inbox').json()['unread']==0
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/tasks').status_code==401
        assert anonymous.get('/tasks').status_code==401
        assert anonymous.get('/api/tasks/notifications/inbox').status_code==401



def test_bulk_fifty_pdfs_and_reject_fifty_one(client, login):
    h=login(client,'hod')
    files=[('files',(f'reference_{i:02d}.pdf',PDF,'application/pdf')) for i in range(50)]
    response=client.post('/api/tasks/batches',headers={'X-CSRF-Token':h},
        data={'title':'Fifty academic assignment references'},files=files)
    assert response.status_code==201,response.text
    assert response.json()['count']==50
    items=client.get('/api/tasks').json()['items']
    assert len(items)==50
    result=client.post('/api/tasks/assign',headers={'X-CSRF-Token':h},
        json={'task_ids':[t['id'] for t in items],'staff_id':_staff_id(),
              'notes':'Complete each PDF using the department checklist.',
              'rules':RULE})
    assert result.status_code==200,result.text
    assert result.json()['assigned']==50
    with TestClient(app) as staff:
        login(staff,'staff')
        assert staff.get('/api/tasks/notifications/inbox').json()['unread']==50
    too_many=files+[('files',('reference_50.pdf',PDF,'application/pdf'))]
    rejected=client.post('/api/tasks/batches',headers={'X-CSRF-Token':h},
        data={'title':'Too many assignment references'},files=too_many)
    assert rejected.status_code==422


def test_deepseek_provider_priority_and_stored_key(monkeypatch, client, login):
    from app.ai_gateway import select_provider
    from app.database import IntegrationSetting
    from app.verification import encrypt_key
    from cryptography.fernet import Fernet
    monkeypatch.setenv('SETTINGS_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.setenv('DEEPSEEK_API_KEY','direct-key-for-unit-tests')
    monkeypatch.setenv('OPENROUTER_API_KEY','openrouter-key-for-unit-tests')
    with DBSession() as db:
        provider=select_provider(db)
    assert provider.name=='DeepSeek'
    assert provider.model=='deepseek-flash'
    assert provider.url.startswith('https://api.deepseek.com/')
    monkeypatch.delenv('DEEPSEEK_API_KEY')
    with DBSession() as db:
        provider=select_provider(db)
    assert provider.name.startswith('OpenRouter')
    assert 'deepseek' in provider.model.lower()
    assert 'google/gemma' not in provider.model.lower()


def test_ai_process_brief_is_denied_for_staff_and_unconfigured(client, login, monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    hod_csrf=login(client,'hod')
    assert client.post('/api/tasks/insights/ai-brief',
                       headers={'X-CSRF-Token':hod_csrf}).status_code==503
    with TestClient(app) as staff_client:
        staff_csrf=login(staff_client,'staff')
        assert staff_client.post('/api/tasks/insights/ai-brief',
                                 headers={'X-CSRF-Token':staff_csrf}).status_code==403


def test_hod_review_history_is_durable(client, login, monkeypatch):
    hod_csrf=login(client,'hod')
    ids=_batch(client,hod_csrf,1)
    assigned=client.post('/api/tasks/assign',headers={'X-CSRF-Token':hod_csrf},
                         json={'task_ids':ids,'staff_id':_staff_id(),
                               'notes':'Prepare the complete academic report with all sections.',
                               'rules':RULE})
    assert assigned.status_code==200
    from app.taskflow import TaskItem,TaskDecision
    from app.database import DBSession
    with DBSession() as db:
        task=db.get(TaskItem,ids[0]);task.state='manual_review';db.commit()
    reviewed=client.post(f'/api/tasks/{ids[0]}/decide',
         headers={'X-CSRF-Token':hod_csrf},
         json={'decision':'approved','note':'Manual audit completed, references and format inspected.'})
    assert reviewed.status_code==200,reviewed.text
    row=next(r for r in client.get('/api/tasks').json()['items'] if r['id']==ids[0])
    assert row['decisions'][0]['decision']=='approved'
    with DBSession() as db:
        assert db.query(TaskDecision).filter(TaskDecision.task_id==ids[0]).count()==1


def test_weighted_review_uses_reference_context_and_explicit_hod_override(client,login,monkeypatch):
    from app import taskflow as tf
    from app.verification import Extracted
    hod_token=login(client,'hod'); task_id=_batch(client,hod_token,1)[0]
    rules=[{'id':f'check{i}', 'title':f'Check number {i}', 'type':'other',
            'required':i==0,'weight':5 if i==0 else 1,
            'value':'','instructions':'Review this evidence'} for i in range(3)]
    response=client.post('/api/tasks/assign',headers={'X-CSRF-Token':hod_token},
        json={'task_ids':[task_id],'staff_id':_staff_id(),
              'notes':'Compare the submitted report with the HOD reference instructions.','rules':rules})
    assert response.status_code==200,response.text
    monkeypatch.setattr(tf,'select_provider',lambda db:Provider('NVIDIA','test-model','https://integrate.api.nvidia.com/v1/chat/completions','test-key'))
    monkeypatch.setattr('app.verification.extract_document',
        lambda name,data:Extracted(['Official department report with verifiable objective text'],1,False,[]))
    seen=[]
    def mocked_review(provider,system,payload,max_tokens=2200):
        seen.append(payload)
        return {'summary':'Reviewed with source evidence.',
                'evaluations':[{'rule_id':f'check{i}','result':'issue' if i==0 else 'pass',
                                'confidence':0.98,'evidence':'verifiable objective text',
                                'issue':'Objective requires correction.'} for i in range(3)]}
    monkeypatch.setattr(tf,'review_json',mocked_review)
    with TestClient(app) as staff:
        staff_token=login(staff,'staff')
        submitted=staff.post(f'/api/tasks/{task_id}/submit',headers={'X-CSRF-Token':staff_token},
            files={'file':('completed.pdf',PDF,'application/pdf')})
        assert submitted.status_code==201,submitted.text
    assert run_task_once()
    task=client.get('/api/tasks').json()['items'][0]
    assert task['score']==29  # Two low-importance passes / seven weight units.
    assert task['state']=='correction_required'
    assert task['report']['rubric']['mandatory_failed']==['check0']
    assert task['report']['reference_comparison']['available']
    assert task['report']['document_signals']['word_count']>0
    assert seen and seen[0]['reference_text'].startswith('[REFERENCE PAGE 1]')
    assert 'HOD reference' in seen[0]['task_instructions']
    approval=client.post(f'/api/tasks/{task_id}/decide',headers={'X-CSRF-Token':hod_token},
        json={'decision':'approved','note':'I independently checked the source and authorized the documented exception.'})
    assert approval.status_code==200,approval.text
    assert approval.json()['state']=='approved'


def test_oversight_can_only_open_approved_task_documents(client,login):
    hod_token=login(client,'hod'); task_id=_batch(client,hod_token,1)[0]
    assert client.post('/api/tasks/assign',headers={'X-CSRF-Token':hod_token},
        json={'task_ids':[task_id],'staff_id':_staff_id(),
              'notes':'Produce an official report for the department.','rules':RULE}).status_code==200
    for oversight in ('principal','iqac'):
        with TestClient(app) as reviewer:
            login(reviewer,oversight)
            assert reviewer.get('/api/tasks').json()['items']==[]
            assert reviewer.get(f'/api/tasks/{task_id}/reference').status_code==404
            assert reviewer.get('/api/tasks/insights/summary').status_code==200
    from app.database import DBSession
    with DBSession() as db:
        task=db.get(TaskItem,task_id);task.state='approved';db.commit()
    for oversight in ('principal','iqac'):
        with TestClient(app) as reviewer:
            login(reviewer,oversight)
            assert reviewer.get('/api/tasks').json()['items'][0]['id']==task_id
            assert reviewer.get(f'/api/tasks/{task_id}/reference').status_code==200


def test_invalid_word_limit_and_weight_rejected_by_assignment(client,login):
    token=login(client,'hod');task_id=_batch(client,token,1)[0]
    base={'task_ids':[task_id],'staff_id':_staff_id(),
          'notes':'Please complete all required content as instructed.'}
    invalids=[
        {'id':'word', 'title':'Minimum words', 'type':'min_words','value':'zero'},
        {'id':'word', 'title':'Maximum words', 'type':'max_words','value':'0'},
        {'id':'weight', 'title':'Heavy critical item', 'type':'other','weight':101},
    ]
    for rule in invalids:
        resp=client.post('/api/tasks/assign',headers={'X-CSRF-Token':token},json={**base,'rules':[rule]})
        assert resp.status_code==422,resp.text

def test_model_source_identifiers_use_real_submission_text_and_reject_invented_ids(client,login,monkeypatch):
    import app.taskflow as tf
    from app.verification import Extracted
    token=login(client,'hod');task_id=_batch(client,token,1)[0]
    rules=[{'id':'check'+str(i),'title':'Source check '+str(i),'type':'semantic','required':True,'value':'','instructions':'Check the submitted source.'} for i in range(2)]
    assert client.post('/api/tasks/assign',headers={'X-CSRF-Token':token},json={'task_ids':[task_id],'staff_id':_staff_id(),'notes':'Synthetic source-citation test.','rules':rules}).status_code==200
    monkeypatch.setattr(tf,'select_provider',lambda db:Provider('NVIDIA','test-model','https://integrate.api.nvidia.com/v1/chat/completions','test-key'))
    monkeypatch.setattr('app.verification.extract_document',lambda name,data:Extracted(['The submitted document contains this exact source evidence.'],1,False,[]))
    def model(provider,system,payload,max_tokens=2200):
        source=payload['evidence_passages'][0]
        return {'evaluations':[
            {'rule_id':'check0','result':'pass','confidence':.99,'evidence_id':source['id'],'evidence':'A model paraphrase must never replace the selected document text.'},
            {'rule_id':'check1','result':'pass','confidence':.99,'evidence_id':'invented-source','evidence':source['text']}]}
    monkeypatch.setattr(tf,'review_json',model)
    with TestClient(app) as staff:
        staff_token=login(staff,'staff')
        assert staff.post(f'/api/tasks/{task_id}/submit',headers={'X-CSRF-Token':staff_token},files={'file':('completed.pdf',PDF,'application/pdf')}).status_code==201
    assert run_task_once()
    result=client.get('/api/tasks').json()['items'][0]
    findings={item['rule_id']:item for item in result['report']['findings']}
    assert findings['check0']['evidence']=='The submitted document contains this exact source evidence.'
    assert findings['check0']['result']=='pass' and findings['check0']['location'].startswith('Page 1')
    assert findings['check1']['result']=='uncertain' and findings['check1']['confidence']==0
    assert result['state']=='manual_review' and result['score'] is None

def test_staff_submission_downloads_preserve_department_and_approved_version_scope(client,login):
    token=login(client,'hod');task_id=_batch(client,token,1)[0]
    assert client.post('/api/tasks/assign',headers={'X-CSRF-Token':token},json={'task_ids':[task_id],'staff_id':_staff_id(),'notes':'Download access regression.','rules':RULE}).status_code==200
    with DBSession() as db:
        for revision in (1,2):
            db.add(TaskSubmission(task_id=task_id,uploaded_by=_staff_id(),revision=revision,filename=f'staff-v{revision}.pdf',content=PDF+str(revision).encode(),state='completed'))
        db.commit()
    response=client.get(f'/api/tasks/{task_id}/submission')
    assert response.status_code==200 and response.content.endswith(b'2')
    assert response.headers['cache-control']=='no-store'
    assert client.get(f'/api/tasks/{task_id}/submission?revision=1').content.endswith(b'1')
    assert client.get('/api/tasks').json()['items'][0]['latest_revision']==2
    for role,expected in [('staff',200),('staff2',404),('hod2',404),('principal',404),('iqac',404)]:
        with TestClient(app) as member:
            login(member,role)
            assert member.get(f'/api/tasks/{task_id}/submission').status_code==expected
    with DBSession() as db:
        db.get(TaskItem,task_id).state='approved';db.commit()
    for role in ('principal','iqac'):
        with TestClient(app) as member:
            login(member,role)
            assert member.get(f'/api/tasks/{task_id}/submission').content.endswith(b'2')
            assert member.get(f'/api/tasks/{task_id}/submission?revision=1').status_code==404
    with TestClient(app) as anonymous:
        assert anonymous.get(f'/api/tasks/{task_id}/submission').status_code==401
