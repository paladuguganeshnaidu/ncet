"""Reference-PDF DeepSeek suggestions must stay drafts until HOD confirms each."""
import json
import pytest
from fastapi.testclient import TestClient

from app.database import DBSession, User
from app.main import app
from app.taskflow import TaskItem
from app.reference_rules import RuleDraft, parse_generated_rules, run_rule_draft_once
from app.ai_gateway import Provider
from app.verification import Extracted

PDF=b'%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF'

def _upload(client,csrf,filenames):
    response=client.post('/api/tasks/batches',headers={'X-CSRF-Token':csrf},
        data={'title':'Reference academic checklists'},
        files=[('files',(f,PDF,'application/pdf')) for f in filenames])
    assert response.status_code==201,response.text
    return client.get('/api/tasks').json()['items']

def _mock_provider(monkeypatch):
    monkeypatch.setattr('app.reference_rules.select_provider',
        lambda db:Provider('DeepSeek','deepseek-chat','https://example.invalid','mock-key'))
    monkeypatch.setattr('app.verification.extract_document',
        lambda filename,pdf: Extracted([f'Introduction {filename} Student ID required'],1,False,[]))
    def fake_ai(provider,system,payload,max_tokens=3000):
        name=payload['filename']
        return {'summary':'Reference rules extracted from this PDF.',
            'rules':[{'title':'Required introduction','type':'required_heading','required':True,
                       'value':'Introduction','instructions':'Include the introduction heading.',
                       'evidence':'Introduction'},
                     {'title':'Include document identifier','type':'required_phrase','required':False,
                       'value':'Student ID','instructions':'Use the document identifier.',
                       'evidence':'Student ID'}]}
    monkeypatch.setattr('app.reference_rules.review_json',fake_ai)

def test_auto_queues_per_uploaded_pdf_and_hod_confirmation(client,login,monkeypatch):
    token=login(client,'hod')
    rows=_upload(client,token,['intro.pdf','report.pdf'])
    ids=[r['id'] for r in rows]
    with DBSession() as db:
        assert db.query(RuleDraft).count()==2
        assert {d.state for d in db.query(RuleDraft)}=={'queued'}
    assert client.get('/api/tasks/rules/drafts').status_code==200
    _mock_provider(monkeypatch)
    assert run_rule_draft_once() is True
    assert run_rule_draft_once() is True
    assert run_rule_draft_once() is False
    draft_data=client.get('/api/tasks/rules/drafts').json()['items']
    assert all(x['state']=='ready' and len(x['rules'])==2 for x in draft_data)
    with DBSession() as db:
        staff=db.query(User).filter_by(username='staff').one()
        staff_id=staff.id
    body={'task_ids':ids,'staff_id':staff_id,'notes':'Prepare documents as described in the PDF.',
          'use_generated_rules':True,'confirmed_task_ids':ids}
    missing=client.post('/api/tasks/assign',headers={'X-CSRF-Token':token},
        json={**body,'confirmed_task_ids':[]})
    assert missing.status_code==422
    ok=client.post('/api/tasks/assign',headers={'X-CSRF-Token':token},json=body)
    assert ok.status_code==200,ok.text
    with DBSession() as db:
        tasks=db.query(TaskItem).filter(TaskItem.id.in_(ids)).all()
        assert all(len(json.loads(t.rules_json))==2 and t.state=='assigned' for t in tasks)

def test_failed_provider_can_be_retried_without_fake_rules(client,login,monkeypatch):
    token=login(client,'hod')
    id=_upload(client,token,['unable.pdf'])[0]['id']
    monkeypatch.setattr('app.reference_rules.select_provider',lambda db:None)
    assert run_rule_draft_once() is True
    item=client.get('/api/tasks/rules/drafts').json()['items'][0]
    assert item['state']=='failed' and item['rules']==[]
    assert 'Configure' in item['error']
    response=client.post('/api/tasks/rules/retry',
        json={'task_ids':[id]},headers={'X-CSRF-Token':token})
    assert response.status_code==200
    assert response.json()['queued']==1
    assert client.get('/api/tasks/rules/drafts').json()['items'][0]['state']=='queued'

def test_drafts_are_department_scoped(client,login):
    token=login(client,'hod')
    task_id=_upload(client,token,['private.pdf'])[0]['id']
    client.post('/api/auth/logout',headers={'X-CSRF-Token':token})
    principal=login(client,'principal')
    assert client.get('/api/tasks/rules/drafts').status_code==403
    assert client.post('/api/tasks/rules/retry',headers={'X-CSRF-Token':principal},json={'task_ids':[task_id]}).status_code==403
    client.post('/api/auth/logout',headers={'X-CSRF-Token':principal})
    other=login(client,'hod2')
    assert client.get('/api/tasks/rules/drafts').json()['items']==[]
    assert client.post('/api/tasks/rules/retry',headers={'X-CSRF-Token':other},json={'task_ids':[task_id]}).status_code==404

def test_hallucinated_rules_are_rejected():
    text='Introduction is necessary. Signature appears here.'
    with pytest.raises(ValueError,match='No proposals'):
        parse_generated_rules({'rules':[{'type':'required_heading','title':'Fake heading',
          'value':'Faculty ID','evidence':'Fabricated evidence','required':True}]},text)
    valid={'rules':[{'type':'required_heading','title':'Introduction heading',
            'required':True,'value':'Introduction','evidence':'Introduction'}]}
    parsed,summary=parse_generated_rules(valid,text)
    assert len(parsed)==1 and parsed[0]['type']=='required_heading'
