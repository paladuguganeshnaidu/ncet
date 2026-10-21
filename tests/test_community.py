"""BCA project feed is institution-internal, moderated and separate from private cases."""
from fastapi.testclient import TestClient
from app.main import app
from app.database import DBSession,User
from test_bca_students import import_one,login_student,prepare_bca


def test_private_board_usn_profiles_public_to_signed_in_users(client,login):
    _token,pwd=import_one(client,login)
    assert client.get('/community').status_code==200
    with TestClient(app) as anon:
        assert anon.get('/community').status_code==401
        assert anon.get('/api/community/profiles').status_code==401
        assert anon.get('/api/community/posts').status_code==401
        assert anon.get('/api/community/profiles/1NC24BCA001').status_code==401
    with TestClient(app) as stu:
        csrf=login_student(stu,pwd)
        me=stu.get('/api/community/me').json()
        assert me['name']=='Student One' and me['usn']=='1NC24BCA001' and me['must_change_password']
        assert stu.post('/api/community/posts',headers={'X-CSRF-Token':csrf},json={
            'title':'Our college chatbot','description':'We are building a college chatbot for student support services.',
            'help_needed':'Python and documentation help'}).status_code==403
        changed=stu.post('/api/auth/change-password',headers={'X-CSRF-Token':csrf},json={
            'old_password':pwd,'new_password':'NewCommunityPassword-2026!'})
        assert changed.status_code==200
        assert stu.put('/api/community/me',headers={'X-CSRF-Token':csrf},json={'bio':'Interested in machine learning','skills':'Python, Figma'}).status_code==200
        p=stu.post('/api/community/posts',headers={'X-CSRF-Token':csrf},json={
            'title':'Our college chatbot','description':'We are building a college chatbot for student support services.',
            'help_needed':'Python and documentation help'})
        assert p.status_code==201,p.text
        pid=p.json()['id']
        assert stu.post(f'/api/community/posts/{pid}/comments',headers={'X-CSRF-Token':csrf},json={'message':'I will handle the UI components.'}).status_code==201
        assert stu.get('/api/community/posts').json()['items'][0]['author']['usn']=='1NC24BCA001'
        assert stu.get(f'/api/community/posts/{pid}').json()['comments'][0]['author']['name']=='Student One'
        assert stu.get('/api/community/profiles').json()['items'][0]['skills']=='Python, Figma'
    with TestClient(app) as staff:
        login(staff,'staff')
        assert staff.get('/api/community/profiles/1NC24BCA001').json()['name']=='Student One'
        assert staff.get(f'/api/community/posts/{pid}').json()['comments'][0]['author']['usn']=='1NC24BCA001'
        assert staff.get('/api/bca/cases').status_code==403
    for role in ('principal','iqac','admin'):
        with TestClient(app) as viewer:
            login(viewer,role)
            assert viewer.get('/api/community/posts').status_code==200
            assert viewer.get('/api/community/profiles').status_code==200
            assert viewer.get('/api/bca/cases').status_code==403
    assert 'Disallow: /community' in client.get('/robots.txt').text
    assert '/community' not in client.get('/sitemap.xml').text
    assert client.get('/community').headers['X-Robots-Tag'].lower().startswith('noindex')


def test_public_discussion_no_dm_csrf_rate_limits_and_moderation(client,login):
    hod_token,pwd=import_one(client,login)
    with TestClient(app) as student:
        csrf=login_student(student,pwd)
        student.post('/api/auth/change-password',headers={'X-CSRF-Token':csrf},json={
            'old_password':pwd,'new_password':'NewCommunityPassword-2026!'})
        body={'title':'Research research repository','description':'I am organizing a repository of course notes and helpful links.','help_needed':'Research, references and proofreading'}
        assert student.post('/api/community/posts',json=body).status_code==403
        created=student.post('/api/community/posts',headers={'X-CSRF-Token':csrf},json=body)
        assert created.status_code==201
        id=created.json()['id']
        assert student.post('/api/community/posts',headers={'X-CSRF-Token':csrf},json={**body,'description':'too short'}).status_code==422
        assert student.post(f'/api/community/posts/{id}/comments',json={'message':'Ready!'}).status_code==403
        msg=student.post(f'/api/community/posts/{id}/comments',headers={'X-CSRF-Token':csrf},json={'message':'I can help by collecting references.'})
        assert msg.status_code==201,msg.text
        comment_id=msg.json()['id']
        with TestClient(app) as hod_other:
            login(hod_other,'hod2')
            assert hod_other.get(f'/api/community/posts/{id}').status_code==404
            assert hod_other.post(f'/api/community/posts/{id}/hide',headers={'X-CSRF-Token':hod_other.get('/api/auth/me').json()['csrf']}).status_code==404
        with TestClient(app) as principal:
            pc=login(principal,'principal')
            assert principal.post(f'/api/community/posts/{id}/comments',headers={'X-CSRF-Token':pc},json={'message':'The department supports this initiative.'}).status_code==201
            assert principal.post(f'/api/community/posts/{id}/hide',headers={'X-CSRF-Token':pc}).status_code==403
        assert client.post(f'/api/community/comments/{comment_id}/hide',headers={'X-CSRF-Token':hod_token}).status_code==200
        assert len(client.get(f'/api/community/posts/{id}').json()['comments'])==1
        assert student.patch(f'/api/community/posts/{id}',headers={'X-CSRF-Token':csrf},json={'state':'closed'}).status_code==200
        assert student.post(f'/api/community/posts/{id}/comments',headers={'X-CSRF-Token':csrf},json={'message':'One more detail'}).status_code==409
        assert client.post(f'/api/community/posts/{id}/hide',headers={'X-CSRF-Token':hod_token}).status_code==200
        assert client.get('/api/community/posts').json()['items']==[]
        assert student.get(f'/api/community/posts/{id}').status_code==404


def test_import_rejects_duplicate_usn_and_all_discussion_needs_login(client,login):
    token,pwd=import_one(client,login)
    assert client.post('/api/bca/students/import',headers={'X-CSRF-Token':token},files={
        'file':('roster.csv',b'usn,full_name,branch,semester\n1NC24BCA001,Other Name,Computer Applications,4\n','text/csv')}).status_code==409
    with TestClient(app) as anon:
        for u in ('/api/community/me','/api/community/profiles','/api/community/posts'):
            assert anon.get(u).status_code==401
    assert 'usn' not in client.get('/students').text.lower() or '1nc24bca001' not in client.get('/students').text.lower()
