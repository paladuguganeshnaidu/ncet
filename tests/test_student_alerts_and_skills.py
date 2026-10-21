"""BCA skill capacity, public link validation, request alerts and role-scoped oversight."""
from fastapi.testclient import TestClient
from app.main import app
from app.database import DBSession, User

def make_bca_hod():
    with DBSession() as db:
        hod=db.query(User).filter_by(username='hod').one()
        hod.department='Computer Applications'
        db.commit()

def create_student(client,login,suffix='701'):
    make_bca_hod()
    csrf=login(client,'hod')
    resp=client.post('/api/bca/students/enroll',headers={'X-CSRF-Token':csrf},
        json={'students':[{'usn':'1NC24BCA'+suffix,'full_name':'Student Example','branch':'Computer Applications','semester':3}]})
    assert resp.status_code==200,resp.text
    return resp.json()['credentials'][0]['temporary_password']

def sign_in_student(client,suffix,password):
    response=client.post('/api/auth/login',json={
        'username':'1nc24bca'+suffix,'password':password,'role':'student'})
    assert response.status_code==200,response.text
    csrf=response.json()['csrf']
    changed=client.post('/api/auth/change-password',headers={'X-CSRF-Token':csrf},
        json={'old_password':password,'new_password':'ChangedStudentPassword12345!'})
    assert changed.status_code==200,changed.text
    return csrf

def test_48_skills_c_single_letter_and_social_profiles(client,login):
    password=create_student(client,login)
    skills=['Python','Java','C','C++','JavaScript','TypeScript','SQL','HTML5','CSS3','React.js',
       'Node.js','Express.js','Flask','FastAPI','REST APIs','Machine Learning','Deep Learning',
       'Generative AI','Large Language Models (LLMs)','Natural Language Processing (NLP)',
       'Prompt Engineering','Retrieval-Augmented Generation (RAG)','AI Agents','LangChain',
       'LangGraph','Model Context Protocol (MCP)','Transformers','Hugging Face','Ollama',
       'PyTorch','TensorFlow','Scikit-learn','NumPy','Pandas','Matplotlib','Data Preprocessing',
       'Feature Engineering','Model Training','Model Evaluation','Classification Algorithms',
       'Decision Trees','Random Forest','Support Vector Machines (SVM)','Neural Networks',
       'Embeddings','Vector Databases','Semantic Search','LLM Fine','R']
    with TestClient(app) as student:
        csrf=sign_in_student(student,'701',password)
        payload={'full_name':'Student Example','skills':skills,'publish':True,
            'social_links':{'github':'https://github.com/example','linkedin':'https://www.linkedin.com/in/example/',
                'leetcode':'https://leetcode.com/u/example/','codechef':'https://www.codechef.com/users/example'},
            'mobile':'+919876543210','email':'student.private@example.org',
            'about':'Developing AI tools','certificates':[]}
        saved=student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},json=payload)
        assert saved.status_code==200,saved.text
        assert student.get('/api/bca/showcase/me').json()['skills']==skills
        invalid=student.put('/api/bca/showcase/me',headers={'X-CSRF-Token':csrf},
              json={**payload,'social_links':{'github':'https://wrong.example/my-github'}})
        assert invalid.status_code==422
    public=client.get('/api/bca/directory/1NC24BCA701')
    assert public.status_code==200
    assert public.json()['skills']==skills
    page=client.get('/students/profile/1NC24BCA701')
    assert 'https://github.com/example' in page.text
    assert 'https://www.linkedin.com/in/example/' in page.text
    for response in (public.text,page.text,client.get('/api/bca/directory').text):
        assert '9876543210' not in response
        assert 'student.private@example.org' not in response

def test_complaint_notification_principal_summary_and_project_alert(client,login):
    password=create_student(client,login,'702')
    with TestClient(app) as student:
        csrf=sign_in_student(student,'702',password)
        resp=student.post('/api/bca/cases',headers={'X-CSRF-Token':csrf},json={
            'category':'academics','subject':'Class scheduling concern','description':'Please review the change in class schedule for our semester.'})
        assert resp.status_code==201,resp.text
        ref=resp.json()['reference']
        assert ref.startswith('NCET-REQ-')
        assert student.get('/api/alerts/inbox').json()['unread']==0
        with TestClient(app) as hod:
            h=login(hod,'hod')
            inbox=hod.get('/api/alerts/inbox').json()
            complaints=[n for n in inbox['items'] if n['category']=='complaints']
            assert len(complaints)==1
            assert complaints[0]['link']=='/complaints'
            mark=hod.post('/api/alerts/'+complaints[0]['id']+'/read',headers={'X-CSRF-Token':h})
            assert mark.status_code==200
            assert hod.get('/api/alerts/inbox').json()['unread']==0
            response=hod.post('/api/bca/cases/'+ref+'/messages',headers={'X-CSRF-Token':h},
                json={'message':'Please share the exact schedule details.'})
            assert response.status_code==200,response.text
            summary=hod.get('/api/bca/oversight')
            assert summary.status_code==200
            assert summary.json()['cases_total']==1
            assert summary.json()['cases'][0]['subject']=='Class scheduling concern'
        updated=student.get('/api/alerts/inbox').json()
        assert any(n['category']=='complaints' for n in updated['items'])
        post=student.post('/api/community/posts',headers={'X-CSRF-Token':csrf},
            json={'title':'Building a campus assistant','description':'We are developing a web project to support academic resources for BCA students.',
                  'help_needed':'Frontend collaboration for our project'})
        assert post.status_code==201,post.text
    with TestClient(app) as principal:
        login(principal,'principal')
        data=principal.get('/api/bca/oversight').json()
        assert data['cases_total']==1
        assert data['projects_total']==1
        assert 'cases' not in data
        assert 'Class scheduling concern' not in str(data)
        assert principal.get('/api/bca/cases/'+ref).status_code==403
        assert not any(n['category']=='projects' for n in principal.get('/api/alerts/inbox').json()['items'])
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/alerts/inbox').status_code==401
        assert anonymous.get('/bca/oversight').status_code==401


def test_principal_oversight_aggregates_every_department_without_private_details(client,login):
    from app.community import CollaborationPost
    from app.student_models import StudentCase
    from app.security import hash_password
    with DBSession() as db:
        cse=User(username='cse-student',display_name='CSE Private Name',role='student',
                 department='Computer Science & Engineering',password_hash=hash_password('SecurePassword-123!'),active=True)
        mechanical=User(username='me-student',display_name='ME Private Name',role='student',
                        department='Mechanical Engineering',password_hash=hash_password('SecurePassword-123!'),active=True)
        db.add_all([cse,mechanical]);db.flush()
        db.add_all([
            StudentCase(reference='NCET-REQ-CSE-001',student_id=cse.id,department='Computer Science & Engineering',
                        category='academics',subject='Private CSE subject',description='Private CSE request body.',status='submitted'),
            StudentCase(reference='NCET-REQ-ME-001',student_id=mechanical.id,department='Mechanical Engineering',
                        category='facilities',subject='Private ME subject',description='Private ME request body.',status='in_review'),
            CollaborationPost(student_id=cse.id,department='Computer Science & Engineering',title='CSE collaboration project',
                              description='Private project details for the CSE branch.',help_needed='Find a project contributor',state='open'),
            CollaborationPost(student_id=mechanical.id,department='Mechanical Engineering',title='ME collaboration project',
                              description='Private project details for the ME branch.',help_needed='Find a project contributor',state='closed'),
        ])
        db.commit()

    with TestClient(app) as principal:
        login(principal,'principal')
        response=principal.get('/api/bca/oversight')
        assert response.status_code==200,response.text
        data=response.json()
        assert data['cases_total']==2
        assert data['projects_total']==2
        by_department={row['department']:row for row in data['departments']}
        assert by_department['Computer Science & Engineering']['cases_total']==1
        assert by_department['Computer Science & Engineering']['projects_open']==1
        assert by_department['Mechanical Engineering']['cases_by_status']=={'in_review':1}
        assert by_department['Mechanical Engineering']['projects_open']==0
        rendered=str(data)
        for private_value in ('NCET-REQ-CSE-001','NCET-REQ-ME-001','Private CSE subject',
                              'Private ME subject','Private CSE request body','Private project details'):
            assert private_value not in rendered
        assert 'cases' not in data


def test_missing_bca_hod_routes_setup_alert_to_admin_not_private_complaint(client,login):
    # Preserve department boundaries; escalate to admin rather than exposing
    # the student's confidential request to an unrelated department's HOD.
    with DBSession() as db:
        db.query(User).filter_by(username='hod').one().department='Computer Science & Engineering'
        db.commit()
    admin_csrf=login(client,'admin')
    with DBSession() as db:
        from app.student_models import BCAStudent
        student=db.query(User).filter_by(username='student').first()
        if student is None:
            from app.security import hash_password
            student=User(username='1nc24bca713',display_name='Student Example',role='student',
                department='Computer Applications',password_hash=hash_password('StrongStudentPassword2026!'),active=True)
            db.add(student);db.flush()
            db.add(BCAStudent(user_id=student.id,usn='1NC24BCA713',semester=3,must_change_password=False))
            db.commit()
    with TestClient(app) as student_client:
        logged=student_client.post('/api/auth/login',json={'username':'1nc24bca713',
            'password':'StrongStudentPassword2026!','role':'student'})
        assert logged.status_code==200
        token=logged.json()['csrf']
        result=student_client.post('/api/bca/cases',headers={'X-CSRF-Token':token},json={
            'category':'academics','subject':'Private laboratory issue','description':'This request contains private classroom details.'})
        assert result.status_code==201
    alerts=client.get('/api/alerts/inbox').json()['items']
    assert any(n['category']=='setup' and n['link']=='/app' for n in alerts)
    assert 'Private laboratory issue' not in str(alerts)


def test_bca_oversight_requires_correct_department_and_has_safe_denial_page(client,login):
    # A legitimate HOD from a different department must not see BCA complaints.
    login(client,'hod')
    unauthorized=client.get('/bca/oversight')
    assert unauthorized.status_code==403
    assert 'text/html' in unauthorized.headers['content-type']
    assert 'Open HOD task dashboard' in unauthorized.text
    assert 'href="/tasks"' in unauthorized.text
    assert unauthorized.headers['cache-control']=='no-store'
    assert client.get('/api/bca/oversight').status_code==403
    assert client.get('/api/bca/cases').status_code==200
    assert client.get('/api/bca/cases').json()['all_total']==0

    # A correctly provisioned BCA HOD sees the real oversight workspace.
    make_bca_hod()
    allowed=client.get('/bca/oversight')
    assert allowed.status_code==200,allowed.text
    assert 'Institutional oversight' in allowed.text
    assert client.get('/api/bca/oversight').status_code==200

    # The Principal receives aggregate statistics, not student case identities.
    with TestClient(app) as principal:
        login(principal,'principal')
        assert principal.get('/bca/oversight').status_code==200
        result=principal.get('/api/bca/oversight').json()
        assert result['view']=='summary'
        assert 'cases' not in result
