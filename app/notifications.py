"""Persistent in-app alerts, scoped to accounts and roles."""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from .database import Base, User, get_db, utcnow
from .security import current, csrf_required

router=APIRouter(tags=['In-app notifications'])

class AppNotification(Base):
    __tablename__='app_notifications'
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    recipient_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    text:Mapped[str]=mapped_column(String(280))
    link:Mapped[str]=mapped_column(String(220))
    category:Mapped[str]=mapped_column(String(32),index=True)
    seen:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)


def emit(db,users,text,link,category,exclude=None):
    if not link.startswith('/') or link.startswith('//'):raise ValueError('A local link is required.')
    for user_id in set(users):
        if user_id and user_id!=exclude:
            db.add(AppNotification(recipient_id=user_id,text=text[:280],link=link[:220],category=category[:32]))


def hod_recipients(db,department):
    if not department:
        return []
    from .student_services import case_department_values
    return [item.id for item in db.query(User.id).filter(
        User.active.is_(True),User.role=='hod',
        User.department.in_(case_department_values(department,db))).all()]


def all_members(db):
    return [item.id for item in db.query(User.id).filter(User.active.is_(True)).all()]


@router.get('/api/alerts/inbox')
def inbox(user:User=Depends(current),db:Session=Depends(get_db)):
    from .taskflow import TaskNotification
    current_items=db.query(AppNotification).filter(AppNotification.recipient_id==user.id).order_by(AppNotification.id.desc()).limit(80).all()
    tasks=db.query(TaskNotification).filter(TaskNotification.user_id==user.id).order_by(TaskNotification.id.desc()).limit(50).all()
    items=[{'id':f'a-{n.id}','text':n.text,'link':n.link,'category':n.category,'seen':n.seen,'at':n.created_at.isoformat()} for n in current_items]
    items.extend({'id':f't-{n.id}','text':n.text,'link':'/tasks','category':'tasks','seen':n.seen,'at':n.created_at.isoformat()} for n in tasks)
    items.sort(key=lambda n:n['at'],reverse=True)
    return {'unread':sum(not n['seen'] for n in items),'items':items[:100]}


@router.post('/api/alerts/{notification_id}/read')
def read(notification_id:str,user:User=Depends(csrf_required),db:Session=Depends(get_db)):
    try:prefix,key=notification_id.split('-',1);identity=int(key)
    except (ValueError,TypeError):raise HTTPException(422,'Invalid notification identifier.')
    if prefix=='a':
        notice=db.query(AppNotification).filter_by(id=identity,recipient_id=user.id).first()
    elif prefix=='t':
        from .taskflow import TaskNotification
        notice=db.query(TaskNotification).filter_by(id=identity,user_id=user.id).first()
    else:raise HTTPException(422,'Invalid notification identifier.')
    if not notice:raise HTTPException(404,'Notification not found.')
    notice.seen=True
    db.commit()
    return {'ok':True}


def oversight_access(user):
    from .student_services import BCA_DEPARTMENT_NAMES
    if user.role=='principal':return
    if user.role=='hod' and user.department.strip().lower() in BCA_DEPARTMENT_NAMES:return
    raise HTTPException(403,'BCA oversight is restricted to the Computer Applications HOD or Principal. Other HODs can use /tasks for their department dashboard.')


def case_dashboard_access(user):
    if user.role=='hod' and user.department.strip():
        return
    if user.role=='principal':
        return
    raise HTTPException(403,'Student request management is restricted to department HODs.')


@router.get('/api/bca/oversight')
def bca_oversight(user:User=Depends(current),db:Session=Depends(get_db)):
    from .student_models import StudentCase
    from .community import CollaborationPost
    oversight_access(user)
    state_counts=dict(db.query(StudentCase.status,func.count(StudentCase.id))
        .filter(StudentCase.department=='Computer Applications')
        .group_by(StudentCase.status).all())
    from .student_services import case_department_values
    bca_departments=case_department_values('Computer Applications',db)
    project_counts=dict(db.query(CollaborationPost.state,func.count(CollaborationPost.id))
        .filter(CollaborationPost.hidden.is_(False),CollaborationPost.department.in_(bca_departments))
        .group_by(CollaborationPost.state).all())
    result={'cases_total':sum(state_counts.values()),
            'cases_by_status':{status:state_counts.get(status,0)
                for status in ('submitted','in_review','resolved','closed')},
            'projects_total':sum(project_counts.values()),
            'projects_open':project_counts.get('open',0),
            'projects_closed':project_counts.get('closed',0),
            'view':'summary' if user.role=='principal' else 'department'}
    if user.role=='hod':
        recent=(db.query(StudentCase.reference,StudentCase.subject,StudentCase.status)
            .filter(StudentCase.department=='Computer Applications')
            .order_by(StudentCase.created_at.desc(),StudentCase.id.desc())
            .limit(30).all())
        result['cases']=[{'reference':c.reference,'subject':c.subject,'status':c.status}
                         for c in recent]
    return result


@router.get('/bca/oversight',include_in_schema=False)
def bca_oversight_page(user:User=Depends(current)):
    try:
        oversight_access(user)
    except HTTPException as exc:
        if exc.status_code!=403:
            raise
        # Authenticated non-BCA HODs were previously shown raw JSON by the
        # browser. Keep the 403 and privacy boundary, but explain the safe route.
        return FileResponse(Path(__file__).resolve().parents[1]/'static'/'bca-access-denied.html',
            status_code=403,headers={'Cache-Control':'no-store',
                                     'X-Robots-Tag':'noindex,nofollow,noarchive'})
    return FileResponse(Path(__file__).resolve().parents[1]/'static'/'bca-oversight.html',
        headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex,nofollow,noarchive'})
