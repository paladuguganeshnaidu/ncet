"""Community summaries are private, idempotent and avoid student profiling."""
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from app.database import DBSession,User,utcnow
from app.community import CollaborationPost
from app.discussion_digest import DiscussionDigest,current_slot,summarize_slot,_redact
from app.ai_gateway import Provider
from app.main import app


def test_six_hour_windows_and_identifier_redaction():
    t=lambda h:datetime(2026,10,16,h,30,tzinfo=timezone.utc)
    assert current_slot(t(0))=='2026-10-16-06'
    assert current_slot(t(4))=='2026-10-16-06'
    assert current_slot(t(7))=='2026-10-16-12'
    assert '1NC24BCA001' not in _redact('Please contact 1NC24BCA001 at demo@example.org')
    assert 'demo@example.org' not in _redact('demo@example.org')


def test_no_discussion_digest_is_nonprofiling_and_once_per_slot(client,login):
    from app import discussion_digest as dg
    assert dg.summarize_slot()
    with DBSession() as db:
        rows=db.query(DiscussionDigest).all()
        assert len(rows)==1 and rows[0].post_count==0
        assert rows[0].status=='complete'
    assert not dg.summarize_slot()
    login(client,'hod')
    assert client.get('/api/insights/discussions').status_code==403 # non-BCA HOD
    with TestClient(app) as anon:
        assert anon.get('/api/insights/discussions').status_code==401


def test_ai_summary_does_not_send_student_name_or_usn(client,login,monkeypatch):
    from app import discussion_digest as dg
    from app.database import User
    with DBSession() as db:
        h=db.query(User).filter(User.username=='hod').one();h.department='Computer Applications'
        student=db.query(User).filter(User.username=='staff').one()
        db.add(CollaborationPost(student_id=student.id,title='Student 1NC24BCA001 project collaboration',
            department=student.department,description='Contact 1NC24BCA001 about the science fair.',
            help_needed='Python contributors needed.',state='open',hidden=False))
        db.commit()
    monkeypatch.setattr(dg,'select_provider',lambda db:Provider('test','test-model','https://api.deepseek.com/chat/completions','fake'))
    def mock_provider(provider,system,payload,max_tokens=1300):
        joined=str(payload)
        assert '1NC24BCA001' not in joined
        assert 'Student' in joined # benign subject terms remain
        assert 'mental state' in system # prohibition documented
        return {'summary':'One student project needs Python collaborators.','topics':['Programming collaboration'],'review_flags':[]}
    monkeypatch.setattr(dg,'review_json',mock_provider)
    assert dg.summarize_slot()
    csrf=login(client,'hod')
    data=client.get('/api/insights/discussions').json()
    assert data['items'][0]['status']=='complete'
    assert data['items'][0]['posts']==1
    assert 'Python collaborators' in data['items'][0]['summary']
