"""Private, department-scoped project-contributions board. No DMs or public student records.

All endpoints require an active institutional session; students post under their verified USN.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session as DbSession, joinedload, selectinload

from .database import Base, User, AuditLog, get_db, utcnow
from .security import current, csrf_required
from .student_models import BCAStudent

router = APIRouter(prefix='/api/community', tags=['Authenticated department project collaboration'])
READ_ROLES = {'student','staff','hod','principal','iqac','admin'}
MAX_POSTS_PER_DAY = 5
MAX_COMMENTS_PER_DAY = 30


class CollaborationProfile(Base):
    __tablename__ = 'collaboration_profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True)
    bio: Mapped[str] = mapped_column(String(360), default='')
    skills: Mapped[str] = mapped_column(String(220), default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CollaborationPost(Base):
    __tablename__ = 'collaboration_posts'
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    department: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text)
    help_needed: Mapped[str] = mapped_column(String(280))
    state: Mapped[str] = mapped_column(String(18), default='open', index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    author: Mapped[User] = relationship()
    comments: Mapped[list['CollaborationComment']] = relationship(order_by='CollaborationComment.id', back_populates='post')
    __table_args__=(Index('ix_collaboration_posts_department_created','department','created_at','id'),)


class CollaborationComment(Base):
    __tablename__ = 'collaboration_comments'
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey('collaboration_posts.id', ondelete='CASCADE'), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    message: Mapped[str] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    post: Mapped[CollaborationPost] = relationship(back_populates='comments')
    author: Mapped[User] = relationship()


def viewer(user: User = Depends(current)):
    if user.role not in READ_ROLES:
        raise HTTPException(403, 'You cannot access this board.')
    return user


def writer(user: User = Depends(csrf_required)):
    if user.role not in READ_ROLES:
        raise HTTPException(403, 'You cannot participate in this board.')
    return user


def enrolled_student(db, user, *, ready=False):
    if user.role != 'student':
        raise HTTPException(403, 'Only enrolled students can publish projects and edit student profiles.')
    record = db.query(BCAStudent).filter(BCAStudent.user_id == user.id).first()
    if not record:
        raise HTTPException(403, 'Student enrollment is required.')
    if ready and record.must_change_password:
        raise HTTPException(403, 'Change your temporary password before posting.')
    return record


def department_scope(db, user):
    """Return stable code and current label for the viewer's assigned branch."""
    if user.role in {'admin', 'principal', 'iqac'}:
        return None
    from .student_services import department_scope_values
    scope = department_scope_values(db, user.department)
    if not scope:
        raise HTTPException(403, 'Your account has no active department assignment.')
    return scope


def moderator(user, post_department, scope):
    if user.role == 'admin':
        return True
    if user.role != 'hod':
        return False
    return post_department in (scope or set())


def scoped_post_query(db, user):
    query = db.query(CollaborationPost)
    scope = department_scope(db, user)
    return (query if scope is None else query.filter(CollaborationPost.department.in_(scope))), scope


def student_usns(db, user_ids):
    ids={int(user_id) for user_id in user_ids if user_id is not None}
    if not ids:return {}
    return {student.user_id:student.usn for student in
            db.query(BCAStudent.user_id,BCAStudent.usn).filter(BCAStudent.user_id.in_(ids)).all()}


def author_json(user, usns):
    return {'name':user.display_name,
            'usn':usns.get(user.id) if user.role=='student' else None,
            'role':user.role}


def post_json(post, viewer_user, usns, scope, *, include_comments=True):
    obj = {'id':post.id,'title':post.title,'description':post.description,'help_needed':post.help_needed,
           'state':post.state,'created_at':post.created_at.isoformat(),
           'author':author_json(post.author,usns),'mine':post.student_id==viewer_user.id,
           'can_moderate':moderator(viewer_user,post.department,scope)}
    if include_comments:
        obj['comments']=[{'id':c.id,'author':author_json(c.author,usns),'message':c.message,
                          'created_at':c.created_at.isoformat()} for c in post.comments if not c.hidden]
    return obj


class ProfileEdit(BaseModel):
    bio: str = Field(default='',max_length=360)
    skills: str = Field(default='',max_length=220)

class PostCreate(BaseModel):
    title: str = Field(min_length=8,max_length=140)
    description: str = Field(min_length=30,max_length=3000)
    help_needed: str = Field(min_length=8,max_length=280)

class CommentCreate(BaseModel):
    message: str = Field(min_length=2,max_length=1200)

class PostUpdate(BaseModel):
    state: str


def moderation_audit(db, actor, action, target):
    db.add(AuditLog(actor_id=actor.id,event=action,detail=str(target)[:100]))


@router.get('/me')
def my_public_profile(user:User=Depends(viewer),db:DbSession=Depends(get_db)):
    from .departments import branch_name
    if user.role!='student':
        department_scope(db,user)
        return {'role':user.role,'is_student':False,'department':
                'All departments' if user.role in {'admin','principal','iqac'} else branch_name(db,user.department),
                'can_moderate':user.role=='admin'}
    student=enrolled_student(db,user)
    department_scope(db,user)
    extra=db.query(CollaborationProfile).filter(CollaborationProfile.student_id==user.id).first()
    return {'role':'student','is_student':True,'must_change_password':student.must_change_password,
            'usn':student.usn,'name':user.display_name,'semester':student.semester,
            'department':branch_name(db,user.department),'bio':extra.bio if extra else '',
            'skills':extra.skills if extra else '', 'can_moderate':False}


@router.get('/profiles')
def profiles(q:str='',offset:int=0,limit:int=25,user:User=Depends(viewer),db:DbSession=Depends(get_db)):
    if offset<0 or not 1<=limit<=50:raise HTTPException(422,'Invalid pagination.')
    query=db.query(User,BCAStudent).join(BCAStudent,BCAStudent.user_id==User.id).filter(User.active.is_(True))
    scope=department_scope(db,user)
    if scope is not None:
        query=query.filter(User.department.in_(scope))
    if q.strip():
        term='%'+q.strip()[:60].replace('%','\\%').replace('_','\\_')+'%'
        query=query.filter((User.display_name.ilike(term,escape='\\')) | (BCAStudent.usn.ilike(term,escape='\\')))
    users=query.order_by(BCAStudent.usn).offset(offset).limit(limit).all()
    profiles=(db.query(CollaborationProfile).filter(
        CollaborationProfile.student_id.in_([u.id for u,_ in users])).all()) if users else []
    profile_by_student={profile.student_id:profile for profile in profiles}
    return {'items':[{'name':u.display_name,'usn':s.usn,'semester':s.semester,
                      'bio':profile_by_student[u.id].bio if u.id in profile_by_student else '',
                      'skills':profile_by_student[u.id].skills if u.id in profile_by_student else ''}
                      for u,s in users],
            'offset':offset,'limit':limit}


@router.get('/profiles/{usn}')
def get_profile(usn:str,user:User=Depends(viewer),db:DbSession=Depends(get_db)):
    query=db.query(User,BCAStudent).join(BCAStudent,BCAStudent.user_id==User.id).filter(BCAStudent.usn==usn.upper(),User.active.is_(True))
    scope=department_scope(db,user)
    if scope is not None:query=query.filter(User.department.in_(scope))
    found=query.first()
    if not found:raise HTTPException(404,'Student profile not found.')
    u,p=found; extra=db.query(CollaborationProfile).filter(CollaborationProfile.student_id==u.id).first()
    return {'name':u.display_name,'usn':p.usn,'semester':p.semester,'bio':extra.bio if extra else '',
            'skills':extra.skills if extra else ''}


@router.put('/me')
def update_profile(body:ProfileEdit,user:User=Depends(writer),db:DbSession=Depends(get_db)):
    enrolled_student(db,user,ready=True)
    department_scope(db,user)
    bio=body.bio.strip();skills=body.skills.strip()
    existing=db.query(CollaborationProfile).filter(CollaborationProfile.student_id==user.id).first()
    if existing:existing.bio=bio;existing.skills=skills;existing.updated_at=utcnow()
    else:db.add(CollaborationProfile(student_id=user.id,bio=bio,skills=skills))
    moderation_audit(db,user,'community.profile_updated',user.id)
    db.commit()
    return {'ok':True}


@router.get('/posts')
def list_posts(offset:int=0,limit:int=20,state:str='all',user:User=Depends(viewer),db:DbSession=Depends(get_db)):
    if offset<0 or not 1<=limit<=50:raise HTTPException(422,'Invalid pagination.')
    if state not in {'all','open','closed'}:raise HTTPException(422,'Invalid filter.')
    q,scope=scoped_post_query(db,user)
    q=q.filter(CollaborationPost.hidden.is_(False))
    if state!='all':q=q.filter(CollaborationPost.state==state)
    posts=(q.options(joinedload(CollaborationPost.author))
           .order_by(CollaborationPost.created_at.desc(),CollaborationPost.id.desc())
           .offset(offset).limit(limit).all())
    usns=student_usns(db,(post.student_id for post in posts))
    return {'items':[post_json(post,user,usns,scope,include_comments=False) for post in posts],
            'offset':offset,'limit':limit}


@router.post('/posts',status_code=201)
def create_post(body:PostCreate,user:User=Depends(writer),db:DbSession=Depends(get_db)):
    enrolled_student(db,user,ready=True)
    department=department_scope(db,user)
    values=[body.title.strip(),body.description.strip(),body.help_needed.strip()]
    if len(values[0])<8 or len(values[1])<30 or len(values[2])<8:raise HTTPException(422,'Describe your project and the collaboration needed.')
    count=db.query(func.count(CollaborationPost.id)).filter(CollaborationPost.student_id==user.id,CollaborationPost.created_at>=utcnow()-timedelta(days=1)).scalar()
    if count>=MAX_POSTS_PER_DAY:raise HTTPException(429,'Daily project posting limit reached.')
    post=CollaborationPost(student_id=user.id,department=user.department.strip(),title=values[0],description=values[1],help_needed=values[2])
    from .notifications import emit
    recipients=db.query(User.id).filter(User.active.is_(True),User.department.in_(department)).all()
    db.add(post);db.flush();moderation_audit(db,user,'community.post_created',post.id)
    emit(db,(item.id for item in recipients),'New student project collaboration opportunity.','/community','projects',exclude=user.id)
    db.commit()
    return {'id':post.id,'ok':True}


@router.get('/posts/{post_id}')
def get_post(post_id:int,user:User=Depends(viewer),db:DbSession=Depends(get_db)):
    query,scope=scoped_post_query(db,user)
    post=(query.options(
        joinedload(CollaborationPost.author),
        selectinload(CollaborationPost.comments).joinedload(CollaborationComment.author))
        .filter(CollaborationPost.id==post_id).first())
    if not post or post.hidden:raise HTTPException(404,'Project not found.')
    author_ids={post.student_id}
    author_ids.update(comment.author_id for comment in post.comments)
    usns=student_usns(db,author_ids)
    return post_json(post,user,usns,scope)


@router.post('/posts/{post_id}/comments',status_code=201)
def add_comment(post_id:int,body:CommentCreate,user:User=Depends(writer),db:DbSession=Depends(get_db)):
    if user.role=='student':enrolled_student(db,user,ready=True)
    query,_scope=scoped_post_query(db,user)
    post=query.filter(CollaborationPost.id==post_id).first()
    if not post or post.hidden:raise HTTPException(404,'Project not found.')
    if post.state!='open':raise HTTPException(409,'This project is closed to new comments.')
    message=body.message.strip()
    if len(message)<2:raise HTTPException(422,'Write a comment.')
    count=db.query(func.count(CollaborationComment.id)).filter(CollaborationComment.author_id==user.id,
        CollaborationComment.created_at>=utcnow()-timedelta(days=1)).scalar()
    if count>=MAX_COMMENTS_PER_DAY:raise HTTPException(429,'Daily discussion limit reached.')
    comment=CollaborationComment(post_id=post_id,author_id=user.id,message=message)
    from .notifications import emit
    db.add(comment);db.flush();moderation_audit(db,user,'community.comment_added',comment.id)
    emit(db,[post.student_id],'A member replied to your project discussion.','/community','projects',exclude=user.id)
    db.commit()
    return {'id':comment.id,'ok':True}


@router.patch('/posts/{post_id}')
def change_state(post_id:int,body:PostUpdate,user:User=Depends(writer),db:DbSession=Depends(get_db)):
    query,scope=scoped_post_query(db,user)
    post=query.filter(CollaborationPost.id==post_id).first()
    if not post or post.hidden:raise HTTPException(404,'Project not found.')
    if post.student_id!=user.id and not moderator(user,post.department,scope):raise HTTPException(403,'Only the project owner or department HOD can change its status.')
    if body.state not in {'open','closed'}:raise HTTPException(422,'Invalid status.')
    post.state=body.state;post.updated_at=utcnow()
    moderation_audit(db,user,'community.post_state',f'{post.id}:{body.state}');db.commit()
    return {'ok':True,'state':post.state}


@router.post('/posts/{post_id}/hide')
def hide_post(post_id:int,user:User=Depends(writer),db:DbSession=Depends(get_db)):
    query,scope=scoped_post_query(db,user)
    post=query.filter(CollaborationPost.id==post_id).first()
    if not post:raise HTTPException(404,'Project not found.')
    if not moderator(user,post.department,scope):raise HTTPException(403,'Moderator access required.')
    post.hidden=True;moderation_audit(db,user,'community.post_hidden',post.id);db.commit()
    return {'ok':True}


@router.post('/comments/{comment_id}/hide')
def hide_comment(comment_id:int,user:User=Depends(writer),db:DbSession=Depends(get_db)):
    query,scope=scoped_post_query(db,user)
    pair=(query.join(CollaborationComment,CollaborationComment.post_id==CollaborationPost.id)
          .filter(CollaborationComment.id==comment_id)
          .with_entities(CollaborationComment,CollaborationPost).first())
    if not pair:raise HTTPException(404,'Comment not found.')
    comment,post=pair
    if not moderator(user,post.department,scope):raise HTTPException(403,'Moderator access required.')
    comment.hidden=True;moderation_audit(db,user,'community.comment_hidden',comment.id);db.commit()
    return {'ok':True}
