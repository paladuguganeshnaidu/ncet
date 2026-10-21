"""Mandatory four-field enrollment and super-admin managed branch catalog."""
import io
from openpyxl import Workbook
from app.database import DBSession,User
from app.departments import AcademicDepartment

def bca_faculty(client,login,username='hod'):
    with DBSession() as db:
        db.query(User).filter(User.username==username).one().department='Computer Applications'
        db.commit()
    return login(client,username)

def test_admin_controls_departments_and_stable_codes(client,login):
    assert client.get('/api/academic/departments').status_code==401
    token=login(client,'admin')
    before=client.get('/api/academic/departments').json()['items']
    assert any(d['code']=='Computer Applications' for d in before)
    headers={'X-CSRF-Token':token}
    added=client.post('/api/admin/departments',headers=headers,json={'name':'Information Science & Engineering'})
    assert added.status_code==201,added.text
    code=added.json()['code']
    assert code.startswith('dept-')
    changed=client.patch('/api/admin/departments/'+code,headers=headers,
                         json={'name':'Information Science and Engineering'})
    assert changed.status_code==200,changed.text
    assert changed.json()['code']==code
    assert changed.json()['name']=='Information Science and Engineering'
    disabled=client.patch('/api/admin/departments/'+code,headers=headers,json={'active':False})
    assert disabled.status_code==200
    assert not disabled.json()['active']
    assert client.post('/api/admin/departments',headers=headers,json={'name':'Computer Applications'}).status_code==409
    assert client.post('/api/admin/departments',headers=headers,json={'name':'=HACK()'}).status_code==422
    staff=login(client,'staff')
    assert client.post('/api/admin/departments',headers={'X-CSRF-Token':staff},
                       json={'name':'Unauthorized Branch'}).status_code==403

def test_all_registration_fields_required_and_admin_transfer(client,login):
    hod=bca_faculty(client,login)
    endpoint='/api/bca/students/enroll'
    valid={'usn':'1NC24BCA930','full_name':'Four Field Student',
           'branch':'Computer Applications','semester':3}
    for key in ('usn','full_name','branch','semester'):
        bad={k:v for k,v in valid.items() if k!=key}
        assert client.post(endpoint,headers={'X-CSRF-Token':hod},
                           json={'students':[bad]}).status_code==422
    for key in ('full_name','branch'):
        bad={**valid,key:''}
        assert client.post(endpoint,headers={'X-CSRF-Token':hod},
                           json={'students':[bad]}).status_code==422
    good=client.post(endpoint,headers={'X-CSRF-Token':hod},json={'students':[valid]})
    assert good.status_code==200,good.text
    assert good.json()['credentials'][0]['branch']=='Computer Applications'
    with DBSession() as db:
        assert db.query(User).filter(User.username=='1nc24bca930').one().department=='Computer Applications'
    admin=login(client,'admin')
    changed=client.patch('/api/bca/students/1NC24BCA930',headers={'X-CSRF-Token':admin},
                         json={'full_name':'Transferred Student','branch':'Mechanical Engineering','semester':4})
    assert changed.status_code==200,changed.text
    with DBSession() as db:
        assert db.query(User).filter(User.username=='1nc24bca930').one().department=='Mechanical Engineering'
    scoped=bca_faculty(client,login)
    assert not any(s['usn']=='1NC24BCA930' for s in client.get('/api/bca/students').json()['items'])
    # Admin sees every student, nonadmin only authorized branch.
    admin=login(client,'admin')
    assert any(s['branch']=='Mechanical Engineering' for s in client.get('/api/bca/students').json()['items'])

def test_csv_and_excel_require_usn_name_branch_sem(client,login):
    token=bca_faculty(client,login)
    headers={'X-CSRF-Token':token}
    csv_route='/api/bca/students/import'
    legacy=b'usn,full_name,semester\\n1NC24BCA934,Old Format,2\\n'.replace(b'\\n',b'\n')
    assert client.post(csv_route,headers=headers,files={'file':('x.csv',legacy,'text/csv')}).status_code==422
    csv=b'usn,full_name,branch,semester\n1NC24BCA934,Valid CSV Student,Computer Applications,2\n'
    good=client.post(csv_route,headers=headers,files={'file':('x.csv',csv,'text/csv')})
    assert good.status_code==200,good.text
    wb=Workbook();ws=wb.active;ws.append(['USN','Name','Branch','Sem'])
    ws.append(['1NC24BCA935','Valid Excel Student','Computer Applications',3])
    output=io.BytesIO();wb.save(output)
    xls=client.post('/api/bca/students/import-excel',headers=headers,files={'file':(
        'students.xlsx',output.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert xls.status_code==200,xls.text
    bad_book=Workbook();sh=bad_book.active;sh.append(['USN','Name','Sem']);sh.append(['1NC24BCA936','Invalid',3])
    broken=io.BytesIO();bad_book.save(broken)
    assert client.post('/api/bca/students/import-excel',headers=headers,files={'file':(
        'bad.xlsx',broken.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}).status_code==422
