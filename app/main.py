"""NCET VerifyFlow: server-authorized AI-assisted document verification and approval."""
import csv
import io
import os
import re
import secrets
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler
from starlette.concurrency import run_in_threadpool
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy import func, or_, select, delete
from sqlalchemy.orm import Session as DbSession, selectinload
from pydantic import BaseModel, Field
from .database import (User, Session, Document, DocumentEvent, Attachment, AuditLog, LoginFailure, RulePolicy, Verification, IntegrationSetting,
                       get_db, utcnow, DBSession, engine, Base)
from .security import (ROLES, COOKIE, hash_secret, hash_password, verify_password, set_session,
                       current, csrf_required, as_role, as_role_mutation)
from .storage import read_upload, store, retrieve, remove_key, digest
from .verification import Rule, encrypt_key, read_api_key, MODEL

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / 'static'
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', '').rstrip('/')
ENV = os.getenv('APP_ENV', 'development')
app = FastAPI(title='NCET VerifyFlow', docs_url=None if ENV == 'production' else '/api/docs',
              redoc_url=None, openapi_url=None if ENV == 'production' else '/api/openapi.json')
app.mount('/static', StaticFiles(directory=STATIC), name='static')

@app.exception_handler(StarletteHTTPException)
async def render_not_found(request:Request,exc:StarletteHTTPException):
    """Real 404 HTML for navigation; API, XML, and asset errors remain machine-readable."""
    path=request.url.path
    leaf=path.rsplit('/',1)[-1]
    is_navigation=(request.method in ('GET','HEAD') and
                   not path.startswith(('/api/','/static/','/sitemap/')) and
                   not path.endswith(('.xml','.txt','.json','.js','.css','.png','.svg','.webp','.ico')) and
                   not leaf.startswith('.'))
    wants_json='application/json' in request.headers.get('accept','')
    if exc.status_code==404 and is_navigation and not wants_json:
        return FileResponse(STATIC/'404.html',status_code=404,media_type='text/html',
                            headers={'Cache-Control':'no-store',
                                     'X-Robots-Tag':'noindex, nofollow, noarchive'})
    return await http_exception_handler(request,exc)

app.add_middleware(GZipMiddleware, minimum_size=1024)
from .student_services import router as bca_router
app.include_router(bca_router)
from .student_removal import router as student_removal_router
app.include_router(student_removal_router)
from .student_profiles import router as showcase_router
app.include_router(showcase_router)
from .departments import router as department_router, AcademicDepartment
app.include_router(department_router)
from .notifications import router as alert_router
app.include_router(alert_router)
from .community import router as community_router
app.include_router(community_router)
from .taskflow import router as task_router
app.include_router(task_router)
from .reference_rules import router as rule_draft_router
app.include_router(rule_draft_router)
from .discussion_digest import router as digest_router
app.include_router(digest_router)
from .admin_cleanup import router as cleanup_router
app.include_router(cleanup_router)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    if request.url.path in ('/static/bca-management.html','/static/complaints-dashboard.html','/static/bca-oversight.html'):
        return Response(status_code=404, headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow, noarchive'})
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        if request.url.path.startswith('/api/documents') and int(request.headers.get('content-length','0') or 0) > 12*1024*1024:
            return JSONResponse({'detail':'Upload exceeds the 10 MB attachment limit.'},status_code=413)
        # Defends cookie-based endpoints in addition to CSRF token verification.
        origin = request.headers.get('origin')
        if origin:
            expected = PUBLIC_ORIGIN or f'{request.url.scheme}://{request.headers.get("host", "")}'
            # Render reverse proxy uses HTTP internally; specify PUBLIC_ORIGIN in production.
            if origin.rstrip('/') != expected:
                return JSONResponse({'detail': 'Origin is not permitted.'}, status_code=403)
    res = await call_next(request)
    res.headers['X-Content-Type-Options'] = 'nosniff'
    res.headers['X-Frame-Options'] = 'DENY'
    res.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    res.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    res.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    res.headers['Content-Security-Policy'] = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                              "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
                                              "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
    if request.url.path.startswith('/static/'):
        # Versioned styles/scripts are reused across same-origin page transitions.
        # Keep non-versioned URLs short-lived so branding changes propagate.
        if request.query_params.get('v'):
            res.headers['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
        else:
            res.headers['Cache-Control'] = 'public, max-age=300'
    if request.url.path.startswith('/api/') or request.url.path in ('/app','/students/portal','/bca/manage','/bca/complaints','/complaints','/bca/oversight','/community','/tasks'):
        res.headers['Cache-Control'] = 'no-store'
        res.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    if ENV == 'production':
        res.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return res


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)
    role: str | None = None

class ReviewBody(BaseModel):
    decision: str
    note: str = Field(default='', max_length=1500)

class UserBody(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9._-]+$')
    display_name: str = Field(min_length=3, max_length=130)
    role: str
    department: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=12, max_length=128)

class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=12, max_length=128)

class RuleBookBody(BaseModel):
    rules: list[Rule] = Field(max_length=45)

class IntegrationBody(BaseModel):
    api_key: str = Field(min_length=15, max_length=300)

class UserPatch(BaseModel):
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)
    display_name: str | None = Field(default=None, min_length=3, max_length=130)
    department: str | None = Field(default=None, min_length=3, max_length=160)


def user_json(u: User):
    return {'id':u.id,'username':u.username,'name':u.display_name,'role':u.role,
            'department':u.department,'active':u.active}


def audit(db, actor, event, detail=''):
    db.add(AuditLog(actor_id=actor.id if actor else None, event=event, detail=str(detail)[:500]))


def doc_query(db, user):
    q = db.query(Document)
    if user.role == 'staff':
        q = q.filter(Document.submitter_id == user.id)
    elif user.role == 'hod':
        q = q.filter(Document.department == user.department)
    elif user.role in ('principal', 'iqac'):
        q = q.filter(Document.status == 'approved')
    else:
        raise HTTPException(403, 'Role not supported.')
    return q


def authorized_doc(db, user, public_id):
    doc = doc_query(db,user).filter(Document.public_id == public_id).options(
        selectinload(Document.events).selectinload(DocumentEvent.actor),
        selectinload(Document.attachments), selectinload(Document.submitter),selectinload(Document.verifications)).first()
    if not doc:
        raise HTTPException(404,'Document not found.')
    return doc


def doc_json(d):
    attachment = d.attachments[-1] if d.attachments else None
    v = d.verifications[-1] if d.verifications else None
    return {'verification': {'status':v.state,'revision':v.revision} if v else None, 'id':d.public_id, 'title':d.title, 'category':d.category,
            'department':d.department, 'year':d.academic_year, 'description':d.description,
            'status':d.status, 'submitted':d.created_at.isoformat(),
            'author':d.submitter.display_name, 'fileName':attachment.name if attachment else '',
            'fileSize':attachment.size if attachment else 0, 'hasLocalFile': bool(attachment),
            'version':d.version,
            'history':[{'kind':event.action,'by':event.actor.display_name,
                        'at':event.happened_at.isoformat(),'note':event.note} for event in d.events]}

@app.get('/favicon.ico', include_in_schema=False)
def favicon_compat():
    return RedirectResponse('/static/ncet-brand.png',status_code=302)

@app.get('/healthz')
def health():
    with engine.connect() as connection:
        connection.execute(select(1))
    return {'ok':True}

@app.get('/', response_class=HTMLResponse)
def landing():
    return FileResponse(STATIC/'public-home.html')

@app.get('/students', response_class=HTMLResponse)
def public_student_services():
    return FileResponse(STATIC/'student-services.html')

@app.get('/students/portal', response_class=HTMLResponse)
def student_portal():
    return FileResponse(STATIC/'student-portal.html', headers={'X-Robots-Tag':'noindex,nofollow'})

@app.get('/community', response_class=HTMLResponse)
def community_page(user:User=Depends(current)):
    return FileResponse(STATIC/'community.html', headers={'X-Robots-Tag':'noindex,nofollow'})

@app.get('/bca/manage', response_class=HTMLResponse)
def bca_desk(user:User=Depends(current)):
    from .student_services import can_manage_student_roster
    can_manage_student_roster(user)
    return FileResponse(STATIC/'bca-management.html', headers={'X-Robots-Tag':'noindex,nofollow','Cache-Control':'no-store'})

@app.get('/complaints',response_class=HTMLResponse)
@app.get('/bca/complaints',response_class=HTMLResponse)
def bca_complaint_management(user:User=Depends(current)):
    from .notifications import case_dashboard_access
    try:
        case_dashboard_access(user)
    except HTTPException as exc:
        if exc.status_code!=403:
            raise
        return FileResponse(STATIC/'bca-access-denied.html',status_code=403,
                            headers={'Cache-Control':'no-store',
                                     'X-Robots-Tag':'noindex,nofollow,noarchive'})
    if user.role!='hod':
        # Principals retain aggregate access via /bca/oversight, not case bodies.
        return RedirectResponse('/bca/oversight',status_code=303)
    return FileResponse(STATIC/'complaints-dashboard.html',
                        headers={'X-Robots-Tag':'noindex,nofollow,noarchive','Cache-Control':'no-store'})


@app.get('/tasks',response_class=HTMLResponse)
def task_portal(user:User=Depends(current)):
    return FileResponse(STATIC/'tasks.html',headers={'X-Robots-Tag':'noindex,nofollow','Cache-Control':'no-store'})

@app.get('/app', response_class=HTMLResponse)
def workspace():
    return FileResponse(STATIC/'index.html', headers={'X-Robots-Tag':'noindex, nofollow'})

@app.get('/about', response_class=HTMLResponse)
def about():
    return FileResponse(STATIC/'about.html')

@app.get('/plot', response_class=HTMLResponse)
def performance_plot():
    """Render a privacy-preserving, browser-local performance report."""
    return FileResponse(STATIC/'plot.html', headers={
        'Cache-Control':'no-store',
        'X-Robots-Tag':'noindex,nofollow,noarchive',
    })

@app.get('/robots.txt')
def robots():
    origin=PUBLIC_ORIGIN or 'https://ncet-verifyflow.onrender.com'
    return Response('User-agent: *\nDisallow: /api/\nDisallow: /app\nDisallow: /plot\nDisallow: /students/portal\nDisallow: /bca/manage\nDisallow: /bca/complaints\nDisallow: /complaints\nDisallow: /bca/oversight\nDisallow: /community\nDisallow: /tasks\nSitemap: '+origin+'/sitemap.xml\n',media_type='text/plain')

def _sitemap_xml(records):
    from xml.sax.saxutils import escape as xml_escape
    origin=PUBLIC_ORIGIN or 'https://ncet-verifyflow.onrender.com'
    urls=''.join('<url><loc>'+xml_escape(origin+path)+'</loc>'+
                 ('<lastmod>'+xml_escape(modified[:10])+'</lastmod>' if modified else '')+
                 '</url>' for path,modified in records)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'+
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>',
                    media_type='application/xml',headers={'Cache-Control':'no-store'})


def _published_sitemap_batch(db,limit=50000,offset=0):
    from .student_profiles import public_query
    from .student_models import BCAStudent
    from .student_profiles import StudentShowcase
    from sqlalchemy.orm import defer
    rows=(public_query(db).options(defer(StudentShowcase.photo_bytes))
          .order_by(BCAStudent.usn).offset(offset).limit(limit).all())
    return [
        ('/students/profile/'+student.usn,
         showcase.updated_at.isoformat() if showcase.updated_at else '')
        for user,student,showcase in rows
    ]


@app.get('/sitemap.xml')
def sitemap():
    """Newly published, consented profiles appear on the next sitemap request."""
    from .student_profiles import public_query
    with DBSession() as db:
        from .student_profiles import StudentShowcase
        total=public_query(db).with_entities(func.count(StudentShowcase.id)).scalar() or 0
        if total<=50000:
            return _sitemap_xml([('/', ''),('/students',''),('/about',''),
                                 ('/students/directory','')]+_published_sitemap_batch(db))
    from xml.sax.saxutils import escape as xml_escape
    origin=PUBLIC_ORIGIN or 'https://ncet-verifyflow.onrender.com'
    paths=['/sitemap/base.xml']+[
        '/sitemap/students/'+str(page)+'.xml' for page in range(1,(total+9999)//10000+1)]
    nodes=''.join('<sitemap><loc>'+xml_escape(origin+path)+'</loc></sitemap>' for path in paths)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'+
                    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+
                    nodes+'</sitemapindex>',media_type='application/xml',
                    headers={'Cache-Control':'no-store'})


@app.get('/sitemap/base.xml')
def sitemap_base():
    return _sitemap_xml([('/', ''),('/students',''),('/about',''),
                         ('/students/directory','')])


@app.get('/sitemap/students/{page}.xml')
def sitemap_students(page:int):
    if page<1:raise HTTPException(404,'Sitemap not found.')
    with DBSession() as db:
        from .student_profiles import public_query
        from .student_profiles import StudentShowcase
        total=public_query(db).with_entities(func.count(StudentShowcase.id)).scalar() or 0
        if (page-1)*10000>=total:raise HTTPException(404,'Sitemap not found.')
        return _sitemap_xml(_published_sitemap_batch(db,limit=10000,
                                                      offset=(page-1)*10000))


@app.get('/api/auth/me')
def me(request:Request,user:User=Depends(current)):
    return {'user':user_json(user),'csrf':request.state.session.csrf_token}

@app.post('/api/auth/login')
def login(body:LoginBody, request:Request, response:Response, db:DbSession=Depends(get_db)):
    name = body.username.strip().lower()
    ip = request.client.host if request.client else 'unknown'
    # IP-based rate limit uses a digest and never logs the raw password.
    iphash=hashlib.sha256(ip.encode()).hexdigest()
    window = utcnow()-timedelta(minutes=15)
    attempt_count=db.query(func.count(LoginFailure.id)).filter(LoginFailure.ip_hash==iphash,
                                                                LoginFailure.at>window).scalar()
    if attempt_count >= 12:
        raise HTTPException(429,'Too many attempts. Try again after 15 minutes.')
    user=db.query(User).filter(User.username==name, User.active.is_(True)).first()
    valid = bool(user and verify_password(body.password,user.password_hash))
    if not valid or (body.role and body.role!=user.role):
        db.add(LoginFailure(ip_hash=iphash,username=name[:80]));db.commit()
        raise HTTPException(401,'Invalid username, password or role.')
    csrf=set_session(db,user,response)
    audit(db,user,'auth.login');db.commit()
    return {'user':user_json(user),'csrf':csrf}

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user:User=Depends(csrf_required),db:DbSession=Depends(get_db)):
    db.delete(request.state.session)
    audit(db,user,'auth.logout')
    db.commit()
    response.delete_cookie(COOKIE,path='/')
    return {'ok':True}

@app.post('/api/auth/change-password')
def change_password(body:ChangePassword,request:Request,response:Response,
                    user:User=Depends(csrf_required),db:DbSession=Depends(get_db)):
    if not verify_password(body.old_password,user.password_hash):
        raise HTTPException(400,'Current password is incorrect.')
    if body.old_password==body.new_password:
        raise HTTPException(422,'Choose a new password.')
    user.password_hash=hash_password(body.new_password)
    if user.role=='student':
        from .student_models import BCAStudent
        student=db.query(BCAStudent).filter(BCAStudent.user_id==user.id).first()
        if student:student.must_change_password=False
    user.password_changed_at=utcnow()
    db.query(Session).filter(Session.user_id==user.id,Session.id!=request.state.session.id).delete()
    audit(db,user,'auth.password_changed');db.commit()
    return {'ok':True}

@app.get('/api/documents')
def documents(q:str='', status:str='all',offset:int=0, limit:int=100,
              user:User=Depends(current),db:DbSession=Depends(get_db)):
    if not 0 <= offset <= 100000 or not 1 <= limit <= 200:raise HTTPException(422,'Invalid pagination.')
    base=doc_query(db,user)
    if status in ('verifying','pending','manual_review','needs_correction','approved','rejected'):base=base.filter(Document.status==status)
    if q.strip():
        needle=f'%{q.strip()[:80]}%'
        base=base.filter(or_(Document.title.ilike(needle),Document.public_id.ilike(needle),
                             Document.category.ilike(needle)))
    total=base.with_entities(func.count(Document.id)).scalar()
    records=base.options(selectinload(Document.events).selectinload(DocumentEvent.actor),
                         selectinload(Document.attachments),selectinload(Document.submitter),selectinload(Document.verifications)).order_by(
                         Document.created_at.desc(),Document.id.desc()).offset(offset).limit(limit).all()
    return {'items':[doc_json(d) for d in records], 'total':total}

@app.post('/api/documents',status_code=201)
async def upload(title:str=Form(...),category:str=Form(...),year:str=Form(...),description:str=Form(...),
                 file:UploadFile=File(...),user:User=Depends(as_role_mutation('staff')),
                 db:DbSession=Depends(get_db)):
    title=title.strip(); description=description.strip()
    if not 5<=len(title)<=140: raise HTTPException(422,'Document title must contain 5 to 140 characters.')
    if not 10<=len(description)<=2000: raise HTTPException(422,'Description must contain 10 to 2,000 characters.')
    if not 3<=len(category)<=100: raise HTTPException(422,'Select a valid document category.')
    if not re.fullmatch(r'20\d{2}[-–]\d{2,4}',year): raise HTTPException(422,'Select a valid academic year.')
    name,mime,data=await read_upload(file)
    key,content=await run_in_threadpool(store,data,mime)
    try:
        policy=db.query(RulePolicy).filter(RulePolicy.department==user.department).order_by(RulePolicy.version.desc()).first()
        doc=Document(public_id='NCET-'+str(utcnow().year)+'-'+secrets.token_hex(5).upper(),
                     title=title,category=category, academic_year=year, description=description,
                     department=user.department,submitter_id=user.id,status='verifying')
        db.add(doc);db.flush()
        db.add(Attachment(document_id=doc.id, version=1,name=name,mime=mime,size=len(data),
                          sha256=digest(data),storage_key=key,bytes_content=content))
        db.add(Verification(document_id=doc.id,revision=1,policy_id=policy.id if policy else None,state='queued'))
        db.add(DocumentEvent(document_id=doc.id,actor_id=user.id,action='submitted',
                             note='Queued for automated checks; human review follows when evidence is missing or AI is unavailable.'))
        audit(db,user,'document.created',doc.public_id)
        db.commit()
        return {'id':doc.public_id,'ok':True}
    except Exception:
        db.rollback();remove_key(key);raise

@app.post('/api/documents/{public_id}/review')
def review(public_id:str,body:ReviewBody,user:User=Depends(as_role_mutation('hod')),
           db:DbSession=Depends(get_db)):
    if body.decision not in ('approved','rejected'):
        raise HTTPException(422,'Decision must be approved or rejected.')
    note=body.note.strip()
    if body.decision=='rejected' and len(note)<10:
        raise HTTPException(422,'A specific reason of at least 10 characters is required.')
    # Locking prevents two concurrent HOD decisions on PostgreSQL.
    doc=db.query(Document).filter(Document.public_id==public_id,
                                  Document.department==user.department).with_for_update().first()
    if not doc:
        raise HTTPException(404,'Document not found.')
    if doc.status not in ('pending','manual_review'):
        raise HTTPException(409,'Only verified or manually flagged documents can be reviewed by the HOD.')
    doc.status=body.decision
    doc.updated_at=utcnow()
    db.add(DocumentEvent(document_id=doc.id,actor_id=user.id,action=body.decision,
                         note=note or 'Reviewed and approved for institutional oversight.'))
    audit(db,user,'document.'+body.decision,doc.public_id)
    db.commit()
    return {'ok':True,'status':doc.status}

@app.post('/api/documents/{public_id}/resubmit')
async def resubmit(public_id:str,note:str=Form(...),file:UploadFile=File(...),
                   user:User=Depends(as_role_mutation('staff')),db:DbSession=Depends(get_db)):
    note=note.strip()
    if not 10 <= len(note) <= 900:
        raise HTTPException(422,'Describe your corrections (10-900 characters).')
    name,mime,data=await read_upload(file)
    doc=db.query(Document).filter(Document.public_id==public_id,
                                  Document.submitter_id==user.id).with_for_update().first()
    if not doc:
        raise HTTPException(404,'Document not found.')
    if doc.status not in ('rejected','needs_correction'):
        raise HTTPException(409,'Document is not waiting for revision.')
    key,content=await run_in_threadpool(store,data,mime)
    try:
        policy=db.query(RulePolicy).filter(RulePolicy.department==doc.department).order_by(RulePolicy.version.desc()).first()
        doc.status='verifying';doc.version+=1;doc.updated_at=utcnow()
        db.add(Verification(document_id=doc.id,revision=doc.version,policy_id=policy.id if policy else None,state='queued'))
        db.add(Attachment(document_id=doc.id,version=doc.version,name=name,mime=mime,size=len(data),
                          sha256=digest(data),storage_key=key,bytes_content=content))
        db.add(DocumentEvent(document_id=doc.id,actor_id=user.id,action='resubmitted',note=note))
        audit(db,user,'document.resubmitted',doc.public_id)
        db.commit()
        return {'ok':True,'version':doc.version}
    except Exception:
        db.rollback();remove_key(key);raise

@app.get('/api/documents/{public_id}/file')
def download_file(public_id:str,version:int|None=None,user:User=Depends(current),db:DbSession=Depends(get_db)):
    doc=authorized_doc(db,user,public_id)
    if version is not None and version < 1:
        raise HTTPException(422,'Invalid revision.')
    files=[f for f in doc.attachments if version is None or f.version==version]
    if not files:
        raise HTTPException(404,'Attachment not found.')
    file=files[-1]
    try:raw=retrieve(file)
    except (FileNotFoundError,KeyError):raise HTTPException(503,'Attachment storage unavailable.')
    if raw is None:
        raise HTTPException(503,'Attachment is unavailable.')
    audit(db,user,'document.download',f'{public_id} v{file.version}');db.commit()
    safe_name=quote(file.name,safe='')
    headers={'Content-Disposition':f"attachment; filename*=UTF-8''{safe_name}",
             'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
    return Response(raw,media_type='application/octet-stream',headers=headers)

@app.get('/api/users')
def list_users(user:User=Depends(as_role('admin','hod')),db:DbSession=Depends(get_db)):
    query=db.query(User)
    if user.role=='hod':query=query.filter(User.role=='staff',User.department==user.department)
    users=query.order_by(User.id).limit(1000).all()
    return {'items':[user_json(u) for u in users]}

@app.post('/api/users',status_code=201)
def create_user(body:UserBody,user:User=Depends(as_role_mutation('admin','hod')),
                db:DbSession=Depends(get_db)):
    if body.role not in ROLES:raise HTTPException(422,'Invalid role.')
    if body.role=='student':raise HTTPException(422,'Enroll BCA students through the authorized CSV import.')
    department=body.department.strip()
    if user.role=='hod':
        if body.role!='staff' or department!=user.department:
            raise HTTPException(403,'You may add faculty members only to your own department.')
        department=user.department
    else:
        canonical=db.query(AcademicDepartment).filter(
            func.lower(AcademicDepartment.name)==department.lower(),
            AcademicDepartment.active.is_(True)).first()
        if not canonical:
            raise HTTPException(422,'Choose an active department from Academic Department settings.')
        department=canonical.name
    if db.query(User).filter(User.username==body.username.lower()).first():
        raise HTTPException(409,'Username already exists.')
    created=User(username=body.username.lower(),display_name=body.display_name.strip(),
                 role=body.role,department=department,password_hash=hash_password(body.password))
    db.add(created)
    audit(db,user,'account.created',f'{created.username} ({created.role})')
    db.commit();return user_json(created)

@app.patch('/api/users/{uid}')
def edit_user(uid:int,body:UserPatch,user:User=Depends(as_role_mutation('admin','hod')),
              db:DbSession=Depends(get_db)):
    target=db.get(User,uid)
    if not target or (user.role=='hod' and (target.role!='staff' or target.department!=user.department)):
        raise HTTPException(404,'User not found.')
    if user.role=='hod' and body.department is not None and body.department.strip()!=user.department:
        raise HTTPException(403,'Staff cannot be transferred to another department.')
    if user.role=='admin' and body.department is not None:
        canonical=db.query(AcademicDepartment).filter(
            func.lower(AcademicDepartment.name)==body.department.strip().lower(),
            AcademicDepartment.active.is_(True)).first()
        if not canonical:
            raise HTTPException(422,'Choose an active department from Academic Department settings.')
        body.department=canonical.name
    if target.id==user.id and body.active is False:raise HTTPException(409,'Cannot disable your own account.')
    if target.role=='admin' and body.active is False and db.query(User).filter(User.role=='admin',User.active.is_(True)).count()<=1:
        raise HTTPException(409,'At least one active administrator is required.')
    if body.active is not None:target.active=body.active
    if body.password is not None:
        target.password_hash=hash_password(body.password)
        if target.role=='student':
            from .student_models import BCAStudent
            record=db.query(BCAStudent).filter(BCAStudent.user_id==target.id).first()
            if record:record.must_change_password=True
        target.password_changed_at=utcnow()
        db.query(Session).filter(Session.user_id==target.id).delete()
    if body.display_name is not None:target.display_name=body.display_name.strip()
    if body.department is not None:target.department=body.department.strip()
    audit(db,user,'account.updated',target.username)
    db.commit();return user_json(target)

@app.get('/api/audit')
def audit_log(limit:int=100,user:User=Depends(as_role('admin')),
              db:DbSession=Depends(get_db)):
    if not 1<=limit<=300:raise HTTPException(422,'Invalid limit.')
    rows=db.query(AuditLog,User.username).outerjoin(User,User.id==AuditLog.actor_id).order_by(
         AuditLog.id.desc()).limit(limit).all()
    return {'items':[{'event':a.event,'actor':name or 'System','detail':a.detail,
                       'at':a.at.isoformat()} for a,name in rows]}


@app.get('/api/rules')
def get_rules(user:User=Depends(as_role('hod','staff')),db:DbSession=Depends(get_db)):
    policies=db.query(RulePolicy).filter(RulePolicy.department==user.department).order_by(RulePolicy.version.desc()).limit(15).all()
    if not policies:return {'version':0,'rules':[],'history':[],'department':user.department}
    return {'version':policies[0].version,'rules':json.loads(policies[0].rules_json),'department':user.department,
            'history':[{'version':p.version,'created':p.created_at.isoformat()} for p in policies]}

@app.put('/api/rules')
def save_rules(body:RuleBookBody,user:User=Depends(as_role_mutation('hod')),db:DbSession=Depends(get_db)):
    if len({r.id for r in body.rules})!=len(body.rules):raise HTTPException(422,'Every rule ID must be unique.')
    for rule in body.rules:
        if rule.type in ('min_pages','max_pages') and (not rule.value.isdecimal() or int(rule.value)>2000 or int(rule.value)<1):
            raise HTTPException(422,'Page limits must be integers between 1 and 2000.')
        if rule.type not in ('required_heading','required_phrase','max_pages','min_pages','date_present','signature','formatting','grammar','semantic','other'):
            raise HTTPException(422,f'Unsupported rule type: {rule.type}')
        if rule.type in ('required_heading','required_phrase','max_pages','min_pages') and not rule.value.strip():
            raise HTTPException(422,f'A value is required for: {rule.title}')
    # Strong serialization on PostgreSQL: concurrent HOD edits cannot write same version.
    db.query(User).filter(User.id==user.id).with_for_update().first()
    last=db.query(func.max(RulePolicy.version)).filter(RulePolicy.department==user.department).scalar() or 0
    policy=RulePolicy(department=user.department,version=last+1,
                      rules_json=json.dumps([r.model_dump() for r in body.rules],ensure_ascii=False),created_by=user.id)
    db.add(policy);audit(db,user,'rules.updated',f'{user.department} v{policy.version}; {len(body.rules)} rules')
    db.commit()
    return {'ok':True,'version':policy.version,'rules':len(body.rules)}

@app.get('/api/rules/versions/{version}')
def get_rule_version(version:int,user:User=Depends(as_role('hod')),db:DbSession=Depends(get_db)):
    p=db.query(RulePolicy).filter(RulePolicy.department==user.department,RulePolicy.version==version).first()
    if not p:raise HTTPException(404,'Rule version not found.')
    return {'version':p.version,'rules':json.loads(p.rules_json),'created':p.created_at.isoformat()}

@app.get('/api/documents/{public_id}/verification')
def verification_report(public_id:str,user:User=Depends(current),db:DbSession=Depends(get_db)):
    doc=authorized_doc(db,user,public_id)
    v=doc.verifications[-1] if doc.verifications else None
    if not v:raise HTTPException(404,'No verification record exists.')
    return {'document_id':doc.public_id,'revision':v.revision,'status':v.state,
            'policy_version':db.get(RulePolicy,v.policy_id).version if v.policy_id else None,
            'created':v.created_at.isoformat(),'completed':v.completed_at.isoformat() if v.completed_at else None,
            'report':json.loads(v.report_json or '{}')}

@app.get('/api/admin/integrations')
def integration_status(user:User=Depends(as_role('admin')),db:DbSession=Depends(get_db)):
    from .ai_gateway import select_provider
    provider=select_provider(db)
    return {'configured':bool(provider),
            'provider':provider.name if provider else None,
            'model':provider.model if provider else None,
            'deepseek_configured':bool(provider and provider.name=='DeepSeek'),
            'openrouter_configured':bool(db.get(IntegrationSetting,'openrouter_key')) or bool(os.getenv('OPENROUTER_API_KEY')),
            'key_stored':bool(db.get(IntegrationSetting,'deepseek_key') or db.get(IntegrationSetting,'openrouter_key'))}

@app.put('/api/admin/integrations/openrouter')
def integration_update(body:IntegrationBody,user:User=Depends(as_role_mutation('admin')),db:DbSession=Depends(get_db)):
    if not body.api_key.strip():raise HTTPException(422,'API key is required.')
    try:encrypted=encrypt_key(body.api_key.strip())
    except (ValueError,TypeError):raise HTTPException(503,'Encryption key missing or invalid. Configure SETTINGS_ENCRYPTION_KEY on the server.')
    row=db.get(IntegrationSetting,'openrouter_key')
    if row:row.encrypted_value=encrypted;row.updated_by=user.id;row.updated_at=utcnow()
    else:db.add(IntegrationSetting(key='openrouter_key',encrypted_value=encrypted,updated_by=user.id))
    audit(db,user,'integration.openrouter.updated','API key was changed (value is not logged)')
    db.commit();return {'ok':True}

@app.delete('/api/admin/integrations/openrouter')
def integration_delete(user:User=Depends(as_role_mutation('admin')),db:DbSession=Depends(get_db)):
    row=db.get(IntegrationSetting,'openrouter_key')
    if row:db.delete(row)
    audit(db,user,'integration.openrouter.deleted');db.commit();return {'ok':True}
