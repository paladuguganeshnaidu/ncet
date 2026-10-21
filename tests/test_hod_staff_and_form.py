"""Regression tests for upload errors and department-scoped HOD accounts."""
from app.database import DBSession, User

def test_short_title_error(client,login,sample_file):
    t=login(client,'staff')
    r=client.post('/api/documents',headers={'X-CSRF-Token':t},
        data={'title':'dfbx','category':'Academic Audit','year':'2026–27','description':'Department review document.'}, files={'file':sample_file})
    assert r.status_code==422 and 'title' in r.json()['detail'].lower()
    assert client.get('/api/documents').json()['total']==0

def test_short_description_error(client,login,sample_file):
    t=login(client,'staff')
    r=client.post('/api/documents',headers={'X-CSRF-Token':t},
        data={'title':'Academic document','category':'Academic Audit','year':'2026–27','description':'Short'},files={'file':sample_file})
    assert r.status_code==422 and 'description' in r.json()['detail'].lower()

def test_hod_scope(client,login):
    t=login(client,'hod')
    assert [u['username'] for u in client.get('/api/users').json()['items']]==['staff']
    data={'username':'facultynew','display_name':'New Faculty Member','role':'staff','department':'Computer Science & Engineering','password':'SecureFacultyPassword123!'}
    assert client.post('/api/users',json=data).status_code==403
    r=client.post('/api/users',headers={'X-CSRF-Token':t},json=data)
    assert r.status_code==201,r.text
    assert {u['username'] for u in client.get('/api/users').json()['items']}=={'staff','facultynew'}
    assert client.post('/api/users',headers={'X-CSRF-Token':t},json={**data,'username':'offdept','department':'Mechanical Engineering'}).status_code==403
    assert client.post('/api/users',headers={'X-CSRF-Token':t},json={**data,'username':'newhod','role':'hod'}).status_code==403

def test_hod_reset_only_own_staff(client,login):
    t=login(client,'hod')
    with DBSession() as db:
        ids={u.username:u.id for u in db.query(User).all()}
    own=ids['staff']
    assert client.patch(f'/api/users/{own}',headers={'X-CSRF-Token':t},json={'password':'NewStaffPassword123!'}).status_code==200
    assert client.patch(f'/api/users/{own}',headers={'X-CSRF-Token':t},json={'active':False}).status_code==200
    assert client.patch(f'/api/users/{own}',headers={'X-CSRF-Token':t},json={'department':'Mechanical Engineering'}).status_code==403
    for name in ('admin','principal','hod','hod2','staff2','iqac'):
        assert client.patch(f"/api/users/{ids[name]}",headers={'X-CSRF-Token':t},json={'active':False}).status_code==404
    assert client.get('/api/audit').status_code==403

def test_staff_cannot_manage_users(client,login):
    t=login(client,'staff')
    assert client.get('/api/users').status_code==403
    assert client.post('/api/users',headers={'X-CSRF-Token':t},json={'username':'stranger','display_name':'No Access Person','role':'staff','department':'Computer Science & Engineering','password':'LongEnoughPassword123!'}).status_code==403

def test_other_department_hod(client,login):
    t=login(client,'hod2')
    assert [u['username'] for u in client.get('/api/users').json()['items']]==['staff2']
