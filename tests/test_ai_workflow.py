"""Security and verification regression tests using a private ephemeral SQLite DB."""
import io
import json
import os
import fitz
import pytest
from cryptography.fernet import Fernet
from app.database import DBSession, Document, RulePolicy, Verification, IntegrationSetting
from app.verification import AIResponse, AIItem, extract_document, build_report, run_job


def login_role(client,username):
    r=client.post('/api/auth/login',json={'username':username,'password':'SecurePassword-123!','role':('hod' if username=='hod2' else username)})
    assert r.status_code==200,r.text
    return {'X-CSRF-Token':r.json()['csrf']}


def signout(client,h):
    assert client.post('/api/auth/logout',headers=h).status_code==200


def pdf_data(text):
    d=fitz.open();p=d.new_page();p.insert_text((70,70),text,fontsize=15);blob=d.tobytes();d.close();return blob


def upload(client,h,text='REPORT SUBMISSION',filename='sample.pdf'):
    response=client.post('/api/documents',headers=h,
        data={'title':'Faculty Annual Compliance Report','category':'Academic Audit','year':'2026–27',
              'description':'Official faculty report submitted for verification and review.'},
        files={'file':(filename,pdf_data(text),'application/pdf')})
    assert response.status_code==201,response.text
    return response.json()['id']


def finish(public_id):
    with DBSession() as db:
        job=(db.query(Verification).join(Document).filter(Document.public_id==public_id).order_by(Verification.id.desc()).first())
        assert job is not None
        job_id=job.id
    run_job(job_id)


def store_rulebook(client,h,rules):
    response=client.put('/api/rules',headers=h,json={'rules':rules})
    assert response.status_code==200,response.text
    return response.json()['version']


def test_hod_rulebook_version_history_department_separation(client):
    h=login_role(client,'hod')
    assert client.get('/api/rules').json()['version']==0
    rules=[{'id':'heading','title':'Executive Summary heading','type':'required_heading','required':True,'value':'Executive Summary','instructions':'Exact heading'}]
    assert store_rulebook(client,h,rules)==1
    rules.append({'id':'grammar','title':'Professional grammar','type':'grammar','required':False,'instructions':'Ensure clarity'})
    assert store_rulebook(client,h,rules)==2
    latest=client.get('/api/rules').json()
    assert latest['version']==2 and len(latest['rules'])==2
    old=client.get('/api/rules/versions/1').json()
    assert len(old['rules'])==1
    signout(client,h)
    h=login_role(client,'staff')
    assert client.get('/api/rules').json()['version']==2
    assert client.put('/api/rules',headers=h,json={'rules':[]}).status_code==403
    signout(client,h)
    h=login_role(client,'hod2')
    assert client.get('/api/rules').json()['rules']==[]
    assert client.get('/api/rules/versions/1').status_code==404


def test_ai_pass_then_hod_and_principal(client,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','test-secret-not-a-real-key')
    def fake_call(extracted,rules,key):
        assert 'Executive Summary' in extracted.pages[0]
        return AIResponse(summary='Verified against the checklist.',evaluations=[
            AIItem(rule_id='heading',result='pass',location='Page 1',confidence=1.0),
            AIItem(rule_id='grammar',result='pass',location='Page 1',confidence=.96)])
    monkeypatch.setattr('app.verification.call_ai',fake_call)
    h=login_role(client,'hod')
    store_rulebook(client,h,[{'id':'heading','title':'Executive Summary heading','type':'required_heading','value':'Executive Summary'},
                           {'id':'grammar','title':'Grammar standards','type':'grammar','required':True}])
    signout(client,h)
    h=login_role(client,'staff');uid=upload(client,h,'Executive Summary\nDepartment Verification Report');finish(uid)
    d=client.get('/api/documents').json()['items'][0]
    assert d['status']=='pending' and d['verification']['status']=='passed'
    v=client.get(f'/api/documents/{uid}/verification').json()
    assert v['policy_version']==1 and v['report']['ai_used'] and len(v['report']['findings'])==2
    signout(client,h)
    h=login_role(client,'hod')
    assert client.post(f'/api/documents/{uid}/review',headers=h,json={'decision':'approved'}).status_code==200
    signout(client,h)
    h=login_role(client,'principal')
    assert client.get('/api/documents').json()['items'][0]['status']=='approved'


def test_mandatory_violations_resubmit_and_manual_review(client,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','fake-key')
    def fake_ai(extracted,rules,key):
        return AIResponse(summary='Summary',evaluations=[AIItem(rule_id='grammar',result='pass',confidence=.93)])
    monkeypatch.setattr('app.verification.call_ai',fake_ai)
    h=login_role(client,'hod');store_rulebook(client,h,[{'id':'heading','title':'Mandatory heading','type':'required_heading','value':'Executive Summary'},
                                                {'id':'grammar','title':'Grammar','type':'grammar'}]);signout(client,h)
    # Keep enough extractable PDF text to avoid OCR uncertainty so this case
    # exercises a deterministic missing-heading violation, not manual review.
    h=login_role(client,'staff');id=upload(client,h,'Different Heading\nThis report contains enough explanatory text for reliable extraction.');finish(id)
    assert client.get('/api/documents').json()['items'][0]['status']=='needs_correction'
    report=client.get(f'/api/documents/{id}/verification').json()['report']
    assert report['status']=='needs_correction'
    signout(client,h)
    h=login_role(client,'hod')
    assert client.post(f'/api/documents/{id}/review',headers=h,json={'decision':'approved'}).status_code==409
    signout(client,h)
    h=login_role(client,'staff')
    resp=client.post(f'/api/documents/{id}/resubmit',headers=h,data={'note':'Added missing required heading'},
        files={'file':('revision.pdf',pdf_data('Executive Summary\nThis report includes enough supporting text for reliable extraction.'),'application/pdf')})
    assert resp.status_code==200,resp.text
    assert client.get('/api/documents').json()['items'][0]['status']=='verifying'
    finish(id)
    assert client.get('/api/documents').json()['items'][0]['status']=='pending'
    assert client.get(f'/api/documents/{id}/verification').json()['revision']==2


def test_missing_api_key_or_ambiguous_signature_goes_manual_review(client,monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    h=login_role(client,'hod');store_rulebook(client,h,[{'id':'sig','title':'Signed by Principal','type':'signature'}]);signout(client,h)
    h=login_role(client,'staff');id=upload(client,h,'Digitally signed?');finish(id)
    assert client.get('/api/documents').json()['items'][0]['status']=='manual_review'
    signout(client,h)
    h=login_role(client,'hod')
    assert client.post(f'/api/documents/{id}/review',headers=h,json={'decision':'approved','note':'Original signed document verified manually'}).status_code==200


def test_admin_api_key_encrypted_never_returned(client,monkeypatch):
    monkeypatch.setenv('SETTINGS_ENCRYPTION_KEY',Fernet.generate_key().decode())
    h=login_role(client,'principal')
    assert client.get('/api/admin/integrations').status_code==403
    signout(client,h)
    h=login_role(client,'admin')
    fake='sk-or-v1-TRULYPRIVATE-DO-NOT-LOG'
    r=client.put('/api/admin/integrations/openrouter',headers=h,json={'api_key':fake})
    assert r.status_code==200,r.text
    status=client.get('/api/admin/integrations').json()
    assert status['openrouter_configured'] and fake not in json.dumps(status)
    with DBSession() as db:
        encrypted=db.get(IntegrationSetting,'openrouter_key').encrypted_value
        assert fake not in encrypted
    assert client.get('/api/users').status_code==200
    assert client.delete('/api/admin/integrations/openrouter',headers=h).status_code==200


def test_unreliable_ai_is_manual_not_auto_fail(client,monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY','test-key')
    def failing_ai(*args):raise ValueError('malformed JSON')
    monkeypatch.setattr('app.verification.call_ai',failing_ai)
    h=login_role(client,'hod')
    store_rulebook(client,h,[{'id':'writing','title':'Clear grammar','type':'grammar','required':True}]);signout(client,h)
    h=login_role(client,'staff');id=upload(client,h,'A valid ordinary faculty report');finish(id)
    assert client.get('/api/documents').json()['items'][0]['status']=='manual_review'
    assert client.get(f'/api/documents/{id}/verification').json()['report']['ai_error']=='ValueError'


def test_ocr_image_extracts_text():
    from PIL import Image, ImageDraw, ImageFont
    import shutil
    if not shutil.which('tesseract'):pytest.skip('OCR binary unavailable')
    im=Image.new('RGB',(1400,240),'white');d=ImageDraw.Draw(im)
    f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
    d.text((65,50),'Executive Summary',fill='black',font=f)
    buff=io.BytesIO();im.save(buff,'PNG')
    result=extract_document('scanned.png',buff.getvalue())
    assert 'Executive Summary' in result.pages[0]
