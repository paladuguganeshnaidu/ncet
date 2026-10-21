"""Authenticated student support. Never expose submissions on public routes."""
import csv
import io
import re
import secrets
from datetime import timedelta, datetime, time, timezone, date
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession, selectinload
from .database import User, AuditLog, DBSession, get_db, utcnow
from .student_models import BCAStudent, StudentCase, StudentCaseMessage
from .security import current, csrf_required, as_role, as_role_mutation, hash_password

router=APIRouter(prefix='/api/bca', tags=['BCA student portal'])
BCA_DEPARTMENT='Computer Applications'
BCA_DEPARTMENT_NAMES={'bca','computer applications','bachelor of computer applications'}
USN_RE=re.compile(r'^1NC[A-Z0-9]{5,14}$')
CATEGORIES={'academics','faculty','examinations','facilities','fees','documentation','request','other'}
STATES={'submitted','in_review','resolved','closed'}


def case_department_values(department,db=None):
    """Return current name/code aliases for a department-scoped case query.

    Student accounts store the immutable academic-department code while HOD
    accounts use the current display name. Treat both values as one branch so
    newly configured departments route cases and notifications correctly.
    """
    value=(department or '').strip()
    if not value:return set()
    values={value}
    if value.lower() in BCA_DEPARTMENT_NAMES:
        values.update((BCA_DEPARTMENT,'BCA','Bachelor of Computer Applications'))
    if db is not None:
        from .departments import AcademicDepartment
        record=db.query(AcademicDepartment).filter(or_(
            func.lower(AcademicDepartment.code)==value.lower(),
            func.lower(AcademicDepartment.name)==value.lower())).first()
        if record:values.update((record.code,record.name))
    return values


def department_scope_values(db, department):
    """Resolve the stable code and current label used for one department."""
    value=(department or '').strip()
    if not value:return set()
    values={value}
    from .departments import AcademicDepartment
    record=db.query(AcademicDepartment).filter(or_(
        func.lower(AcademicDepartment.code)==value.lower(),
        func.lower(AcademicDepartment.name)==value.lower())).first()
    if record:values.update((record.code,record.name))
    if value.lower() in BCA_DEPARTMENT_NAMES:
        values.update((BCA_DEPARTMENT,'BCA','Bachelor of Computer Applications'))
    return values


def can_manage_student_roster(actor):
    """Allow roster tools to admins and department-bound faculty roles."""
    department=(actor.department or '').strip()
    if actor.role not in {'staff','hod','admin'} or (actor.role!='admin' and not department):
        raise HTTPException(403,'Only authorized department staff can manage student enrollment.')


def student_roster_department(db, actor):
    """Return the assigned branch for a non-admin roster operation."""
    can_manage_student_roster(actor)
    if actor.role=='admin':return None
    from .departments import AcademicDepartment
    department=(actor.department or '').strip()
    record=db.query(AcademicDepartment).filter(or_(
        func.lower(AcademicDepartment.code)==department.lower(),
        func.lower(AcademicDepartment.name)==department.lower())).first()
    if record:
        if record.active:return record.code
        raise HTTPException(403,'Your department is not active in the academic catalog.')
    if department.lower() in BCA_DEPARTMENT_NAMES:
        return BCA_DEPARTMENT
    raise HTTPException(403,'Your department is not active in the academic catalog.')


def student_profile(db,user):
    if user.role!='student':raise HTTPException(403,'Student access is required.')
    profile=db.query(BCAStudent).filter(BCAStudent.user_id==user.id).first()
    if not profile:raise HTTPException(403,'Student enrollment is incomplete.')
    return profile


def case_access(db,user,ref):
    # Scope resource reads in SQL so private cross-account data is not fetched.
    if user.role=='student':
        query=db.query(StudentCase).filter(StudentCase.student_id==user.id)
    elif user.role=='hod' and user.department.strip():
        query=db.query(StudentCase).filter(StudentCase.department.in_(case_department_values(user.department,db)))
    else:
        raise HTTPException(403,'You cannot access this request.')
    case=(query.options(selectinload(StudentCase.messages).selectinload(StudentCaseMessage.actor))
          .filter(StudentCase.reference==ref).first())
    if not case:raise HTTPException(404,'Request not found.')
    return case


def case_json(case,show_identity=False):
    result={'reference':case.reference,'subject':case.subject,'category':case.category,
            'description':case.description,'status':case.status,'created_at':case.created_at.isoformat(),
            'updated_at':case.updated_at.isoformat(),
            'messages':[{'author':'HOD' if m.actor.role=='hod' else 'Student','body':m.body,'created_at':m.created_at.isoformat()} for m in case.messages]}
    if show_identity:
        result['student']={'name':case.student.display_name,'usn':case.student.username.upper()}
    return result


class NewCase(BaseModel):
    category: str
    subject: str = Field(min_length=6,max_length=160)
    description: str = Field(min_length=15,max_length=4000)

class CaseReply(BaseModel):
    message: str = Field(min_length=2,max_length=2000)

class CaseStatus(BaseModel):
    status: str
    note: str = Field(default='',max_length=1000)


@router.get('/me')
def get_student_profile(user:User=Depends(as_role('student')),db:DbSession=Depends(get_db)):
    p=student_profile(db,user)
    from .departments import branch_name
    return {'usn':p.usn,'name':user.display_name,'branch':branch_name(db,user.department),'semester':p.semester,'must_change_password':p.must_change_password}

@router.post('/complete-account')
def complete_account(user:User=Depends(as_role_mutation('student')),db:DbSession=Depends(get_db)):
    # Password change is performed by the existing password-change endpoint; this only acknowledges it.
    p=student_profile(db,user)
    if p.must_change_password:
        raise HTTPException(409,'Change your initial password in Account Settings before filing a request.')
    return {'ok':True}

@router.post('/students/import')
async def import_students(file:UploadFile=File(...),actor:User=Depends(as_role_mutation('staff','hod','admin')),
                          db:DbSession=Depends(get_db)):
    can_manage_student_roster(actor)
    raw=await file.read(150_001)
    if len(raw)>150_000:raise HTTPException(413,'CSV must be smaller than 150 KB.')
    try:
        text=raw.decode('utf-8-sig')
        reader=csv.DictReader(io.StringIO(text,newline=''))
        headers=tuple(str(h or '').strip().lower() for h in (reader.fieldnames or []))
        aliases={'name':'full_name','department':'branch','sem':'semester'}
        if tuple(aliases.get(h,h) for h in headers)!=('usn','full_name','branch','semester'):
            raise ValueError('CSV headers must be exactly: usn,full_name,branch,semester')
        rows=list(reader)
    except (UnicodeError,csv.Error,ValueError) as exc:
        raise HTTPException(422,str(exc)) from exc
    if not 1<=len(rows)<=100:raise HTTPException(422,'Import 1–100 students per CSV.')
    from .student_profiles import EnrollmentItem,create_students
    parsed=[]
    for i,row in enumerate(rows,2):
        if None in row or len(row)!=4 or any(v is None or not str(v).strip() for v in row.values()):
            raise HTTPException(422,f'Row {i}: USN, Name, Branch, Sem are all required.')
        fields={aliases.get(k.strip().lower(),k.strip().lower()):str(v).strip() for k,v in row.items()}
        try:fields['semester']=int(fields['semester'])
        except ValueError:raise HTTPException(422,f'Row {i}: semester must be a whole number.')
        try:parsed.append(EnrollmentItem(**fields))
        except Exception:raise HTTPException(422,f'Row {i}: invalid USN, name, branch or semester.')
    return create_students(db,actor,parsed)


@router.get('/students')
def list_students(actor:User=Depends(as_role('staff','hod','admin')),db:DbSession=Depends(get_db)):
    can_manage_student_roster(actor)
    query=db.query(User,BCAStudent).join(BCAStudent,BCAStudent.user_id==User.id)
    if actor.role!='admin':
        student_roster_department(db,actor)
        query=query.filter(User.department.in_(department_scope_values(db,actor.department)))
    items=query.order_by(BCAStudent.usn).limit(1000).all()
    from .departments import AcademicDepartment
    branch_codes={u.department for u,_ in items if u.department}
    branch_names={d.code:d.name for d in db.query(AcademicDepartment.code,AcademicDepartment.name)
                  .filter(AcademicDepartment.code.in_(branch_codes)).all()} if branch_codes else {}
    return {'items':[{'usn':p.usn,'name':u.display_name,
                      'branch':u.department,'branch_name':branch_names.get(u.department,u.department),
                      'semester':p.semester,'active':u.active} for u,p in items]}

@router.get('/cases')
def list_cases(status:str=Query('all',pattern='^(all|submitted|in_review|resolved|closed)$'),
               category:str=Query('all',pattern='^(all|academics|faculty|examinations|facilities|fees|documentation|request|other)$'),
               search:str=Query('',max_length=120),
               attention:str=Query('all',pattern='^(all|awaiting_reply|older_than_7d)$'),
               from_date:date|None=None,to_date:date|None=None,
               sort:str=Query('newest',pattern='^(newest|oldest|updated)$'),
               offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),
               user:User=Depends(current),db:DbSession=Depends(get_db)):
    """Private case index. Filter/sort/page in SQL, never load complaint bodies.
    Overview metrics reflect all cases visible to the caller (not current page).
    """
    if user.role=='student':
        student_profile(db,user)
        base=db.query(StudentCase).filter(StudentCase.student_id==user.id)
    elif user.role=='hod' and user.department.strip():
        base=db.query(StudentCase).filter(StudentCase.department.in_(case_department_values(user.department,db)))
    else:
        raise HTTPException(403,'Student or department HOD access required.')
    if from_date and to_date and from_date>to_date:
        raise HTTPException(422,'Start date must not be after end date.')
    # Overall counters are scoped before UI filters, so a selected card keeps
    # its original total visible. Only aggregate columns, never descriptions.
    summary=dict(base.with_entities(StudentCase.status,func.count(StudentCase.id))
                 .group_by(StudentCase.status).all())
    categories=dict(base.with_entities(StudentCase.category,func.count(StudentCase.id))
                    .group_by(StudentCase.category).all())
    latest_author=(select(User.role).join(StudentCaseMessage,StudentCaseMessage.actor_id==User.id)
        .where(StudentCaseMessage.case_id==StudentCase.id)
        .order_by(StudentCaseMessage.id.desc()).limit(1)
        .correlate(StudentCase).scalar_subquery())
    latest_hod_reply=(select(StudentCaseMessage.body)
        .join(User,User.id==StudentCaseMessage.actor_id)
        .where(StudentCaseMessage.case_id==StudentCase.id,User.role=='hod')
        .order_by(StudentCaseMessage.id.desc()).limit(1)
        .correlate(StudentCase).scalar_subquery())
    latest_hod_reply_at=(select(StudentCaseMessage.created_at)
        .join(User,User.id==StudentCaseMessage.actor_id)
        .where(StudentCaseMessage.case_id==StudentCase.id,User.role=='hod')
        .order_by(StudentCaseMessage.id.desc()).limit(1)
        .correlate(StudentCase).scalar_subquery())
    active=StudentCase.status.in_(('submitted','in_review'))
    awaiting=and_(active,or_(latest_author.is_(None),latest_author=='student'))
    seven_days=and_(active,StudentCase.created_at<=utcnow()-timedelta(days=7))
    attention_counts={
        'awaiting_reply':base.filter(awaiting).with_entities(func.count(StudentCase.id)).scalar() or 0,
        'older_than_7d':base.filter(seven_days).with_entities(func.count(StudentCase.id)).scalar() or 0,
    }
    items_query=base
    if attention=='awaiting_reply':items_query=items_query.filter(awaiting)
    elif attention=='older_than_7d':items_query=items_query.filter(seven_days)
    if status!='all':items_query=items_query.filter(StudentCase.status==status)
    if category!='all':items_query=items_query.filter(StudentCase.category==category)
    if from_date:
        items_query=items_query.filter(StudentCase.created_at>=datetime.combine(
            from_date,time.min,tzinfo=timezone.utc))
    if to_date:
        if to_date==date.max:
            items_query=items_query.filter(StudentCase.created_at<=datetime.combine(
                to_date,time.max,tzinfo=timezone.utc))
        else:
            items_query=items_query.filter(StudentCase.created_at<datetime.combine(
                to_date+timedelta(days=1),time.min,tzinfo=timezone.utc))
    if search.strip():
        term='%'+search.strip()+'%'
        items_query=items_query.filter(or_(StudentCase.subject.ilike(term),
                                            StudentCase.reference.ilike(term)))
    total=items_query.with_entities(func.count(StudentCase.id)).scalar() or 0
    order=(StudentCase.created_at.asc(),StudentCase.id.asc()) if sort=='oldest' else (
        (StudentCase.updated_at.desc(),StudentCase.id.desc()) if sort=='updated' else
        (StudentCase.created_at.desc(),StudentCase.id.desc()))
    rows=(items_query.with_entities(StudentCase.id,StudentCase.reference,StudentCase.subject,
            StudentCase.category,StudentCase.status,StudentCase.created_at,
            StudentCase.updated_at,StudentCase.student_id,latest_author.label('last_author_role'))
          .add_columns(latest_hod_reply.label('latest_hod_reply'),
                       latest_hod_reply_at.label('latest_hod_reply_at'))
          .order_by(*order).offset(offset).limit(limit).all())
    identities={}
    if user.role=='hod':
        ids={row.student_id for row in rows}
        identities={u.id:{'name':u.display_name,'usn':u.username.upper()}
                    for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}
    next_steps={'submitted':'Your department HOD will review this request.',
                'in_review':'Your HOD is reviewing this request. Reply here if you have more details.',
                'resolved':'Reviewed by your HOD. Open the request to read the resolution.',
                'closed':'This request is closed. Submit a new request if you need further help.'}
    return {'items':[{'reference':x.reference,'subject':x.subject,'category':x.category,
                      'status':x.status,'created_at':x.created_at.isoformat(),
                      'updated_at':x.updated_at.isoformat(),
                      'next_step':next_steps.get(x.status,''),
                      'latest_hod_reply':(x.latest_hod_reply[:240] if user.role=='student' and x.latest_hod_reply else None),
                      'latest_hod_reply_at':(x.latest_hod_reply_at.isoformat() if user.role=='student' and x.latest_hod_reply_at else None),
                      'awaiting_reply':x.status in ('submitted','in_review') and x.last_author_role in (None,'student'),
                      'older_than_7d':x.status in ('submitted','in_review') and x.created_at.replace(tzinfo=x.created_at.tzinfo or timezone.utc)<=utcnow()-timedelta(days=7),
                      **({'student':identities.get(x.student_id,{'name':'Unknown student','usn':''})}
                         if user.role=='hod' else {})}
                     for x in rows],
            'counts':{k:summary.get(k,0) for k in ('submitted','in_review','resolved','closed')},
            'categories':{k:categories.get(k,0) for k in sorted(CATEGORIES)},
            'all_total':sum(summary.values()),'attention_counts':attention_counts,
            'total':total,'offset':offset,'limit':limit,'has_more':offset+len(rows)<total}

@router.post('/cases',status_code=201)
def create_case(body:NewCase,user:User=Depends(as_role_mutation('student')),db:DbSession=Depends(get_db)):
    profile=student_profile(db,user)
    if profile.must_change_password:raise HTTPException(403,'Change your temporary password before submitting a request.')
    if not user.department.strip():
        raise HTTPException(403,'Your account has no department. Contact the institution administrator.')
    if body.category not in CATEGORIES:raise HTTPException(422,'Select a valid category.')
    recent=db.query(func.count(StudentCase.id)).filter(StudentCase.student_id==user.id,StudentCase.created_at>=utcnow()-timedelta(hours=24)).scalar()
    if recent>=10:raise HTTPException(429,'You have reached the daily request limit. Follow up on an existing request instead.')
    case=StudentCase(reference='NCET-REQ-'+secrets.token_hex(6).upper(),student_id=user.id,
                     department=user.department,category=body.category,subject=body.subject.strip(),description=body.description.strip(),status='submitted')
    if len(case.subject)<6 or len(case.description)<15:raise HTTPException(422,'Add a detailed subject and description.')
    from .notifications import emit, hod_recipients
    db.add(case);db.add(AuditLog(actor_id=user.id,event='bca.case_submitted',detail=case.reference))
    recipients=hod_recipients(db,user.department)
    emit(db,recipients,'New student request awaiting review.','/complaints','complaints')
    if not recipients:
        admins=[u.id for u in db.query(User.id).filter(User.active.is_(True),User.role=='admin').all()]
        emit(db,admins,f'A student request for {user.department} needs a department HOD. Assign an active HOD in User Management.','/app','setup')
    db.commit()
    return {'reference':case.reference,'status':case.status}

@router.get('/cases/{reference}')
def get_case(reference:str,user:User=Depends(current),db:DbSession=Depends(get_db)):
    case=case_access(db,user,reference)
    return case_json(case,show_identity=user.role=='hod')

@router.post('/cases/{reference}/messages')
def send_message(reference:str,body:CaseReply,user:User=Depends(csrf_required),db:DbSession=Depends(get_db)):
    case=case_access(db,user,reference)
    if case.status=='closed':raise HTTPException(409,'Closed requests cannot receive messages.')
    message=body.message.strip()
    if len(message)<2:raise HTTPException(422,'Message must not be empty.')
    reopened=False
    if user.role=='student' and case.status=='resolved':
        latest=case.updated_at
        if latest.tzinfo is None or latest.utcoffset() is None:
            latest=latest.replace(tzinfo=timezone.utc)
        if latest<utcnow()-timedelta(days=14):
            raise HTTPException(409,'This request was resolved more than 14 days ago. Submit a new request for further help.')
        case.status='in_review'
        reopened=True
    from .notifications import emit, hod_recipients
    db.add(StudentCaseMessage(case_id=case.id,actor_id=user.id,body=message))
    if user.role=='student':
        text=('A student reopened a resolved request and added a reply.' if reopened
              else 'A student replied to a request.')
        emit(db,hod_recipients(db,case.department),text,'/complaints','complaints')
    else:
        emit(db,[case.student_id],'Your HOD replied to your request.','/students/portal','complaints')
    case.updated_at=utcnow()
    db.add(AuditLog(actor_id=user.id,event='bca.case_reopened' if reopened else 'bca.case_replied',detail=case.reference))
    db.commit();return {'ok':True,'status':case.status,'reopened':reopened}

@router.patch('/cases/{reference}/status')
def update_case_status(reference:str,body:CaseStatus,user:User=Depends(as_role_mutation('hod')),db:DbSession=Depends(get_db)):
    case=case_access(db,user,reference)
    if body.status not in STATES or body.status=='submitted':raise HTTPException(422,'Invalid status.')
    if case.status=='closed':raise HTTPException(409,'Case is already closed.')
    note=body.note.strip()
    if body.status in {'resolved','closed'} and len(note)<5:
        raise HTTPException(422,'Provide an explanation of at least five characters.')
    from .notifications import emit
    case.status=body.status;case.updated_at=utcnow()
    emit(db,[case.student_id],'Your request status changed to '+body.status.replace('_',' ')+'.','/students/portal','complaints')
    if note:db.add(StudentCaseMessage(case_id=case.id,actor_id=user.id,body=note))
    db.add(AuditLog(actor_id=user.id,event='bca.case_status',detail=f'{case.reference}: {body.status}'))
    db.commit();return {'ok':True,'status':case.status}
