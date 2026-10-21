"""Four scheduled UTC+05:30 collaboration topic summaries per day.

Content-based, not personality/emotion profiling. Comments and posts are shared
with the institution already; no private complaints or student identifiers go
to the model. Moderation flags are advisory and require human review.
"""
import json
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, Session as DbSession
from fastapi import APIRouter, Depends, HTTPException
from .database import Base, DBSession, get_db, User, utcnow, AuditLog
from .security import current, csrf_required
from .community import CollaborationPost, CollaborationComment
from .ai_gateway import select_provider, review_json

router=APIRouter(prefix='/api/insights/discussions',tags=['Shared discussion overview'])
IST=ZoneInfo('Asia/Kolkata')


class DiscussionDigest(Base):
    __tablename__='discussion_digests'
    id:Mapped[int]=mapped_column(primary_key=True)
    slot:Mapped[str]=mapped_column(String(20),unique=True,index=True)
    status:Mapped[str]=mapped_column(String(20),default='processing')
    summary:Mapped[str]=mapped_column(Text,default='')
    topics_json:Mapped[str]=mapped_column(Text,default='[]')
    review_flags_json:Mapped[str]=mapped_column(Text,default='[]')
    post_count:Mapped[int]=mapped_column(Integer,default=0)
    comment_count:Mapped[int]=mapped_column(Integer,default=0)
    model:Mapped[str|None]=mapped_column(String(130),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)


def current_slot(when=None):
    loc=(when or utcnow()).astimezone(IST)
    period=(loc.hour//6)*6
    return f'{loc:%Y-%m-%d}-{period:02d}'


def _redact(value):
    return re.sub(r'\b1NC[A-Z0-9]{4,20}\b','[USN]',
                  re.sub(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}','[EMAIL]',value,flags=re.I),flags=re.I)


def summarize_slot(force=False):
    slot=current_slot()
    with DBSession() as db:
        existing=db.query(DiscussionDigest).filter(DiscussionDigest.slot==slot).first()
        if existing:return False
        digest=DiscussionDigest(slot=slot,status='processing');db.add(digest);db.commit()
    try:
        with DBSession() as db:
            since=utcnow()-timedelta(hours=6)
            posts=db.query(CollaborationPost).filter(CollaborationPost.created_at>=since,CollaborationPost.hidden.is_(False)).limit(75).all()
            comments=db.query(CollaborationComment).join(CollaborationPost).filter(CollaborationComment.created_at>=since,
               CollaborationComment.hidden.is_(False),CollaborationPost.hidden.is_(False)).limit(150).all()
            provider=select_provider(db)
            payload={'posts':[{'title':_redact(p.title),'description':_redact(p.description),'help_needed':_redact(p.help_needed)} for p in posts],
                     'comments':[_redact(c.message) for c in comments]}
        count=len(posts)+len(comments)
        if not count:
            result={'summary':'No new shared project discussions in this reporting period.','topics':[], 'review_flags':[]}
            status='complete'
        elif not provider:
            result={'summary':'Automated discussion summary unavailable: no DeepSeek integration configured.','topics':[], 'review_flags':[]}
            status='unavailable'
        else:
            result=review_json(provider,
              'Summarize shared NCET BCA project discussions objectively. Do not infer individual mental state, personality, character, or discipline. '
              'Return summary (string), topics (short list of strings), review_flags (list of factual rule-violation concerns requiring human moderation). '
              'No automatic blocking. Do not include names, USNs or private information.',payload,max_tokens=1300)
            if not isinstance(result.get('summary'),str) or not isinstance(result.get('topics'),list) or not isinstance(result.get('review_flags'),list):
                raise ValueError('Invalid discussion summary response.')
            status='complete'
        summary=str(result['summary'])[:2200]
        topics=[str(x)[:140] for x in result.get('topics',[])[:12] if isinstance(x,str)]
        flags=[str(x)[:260] for x in result.get('review_flags',[])[:12] if isinstance(x,str)]
    except Exception:
        summary='AI summary could not be completed. HOD can inspect the shared discussions directly.'
        topics=[];flags=[];status='unavailable'
    with DBSession() as db:
        row=db.query(DiscussionDigest).filter(DiscussionDigest.slot==slot).first()
        if not row:return False
        row.summary=summary;row.status=status;row.topics_json=json.dumps(topics)
        row.review_flags_json=json.dumps(flags);row.post_count=len(posts) if 'posts' in locals() else 0
        row.comment_count=len(comments) if 'comments' in locals() else 0
        row.model=provider.model if 'provider' in locals() and provider else None
        row.completed_at=utcnow();db.commit()
    return True


@router.get('')
def digest_history(user:User=Depends(current),db:DbSession=Depends(get_db)):
    if user.role!='hod':raise HTTPException(403,'Only the department HOD may read moderation summaries.')
    if user.department.strip().lower() not in {'bca','computer applications','bachelor of computer applications'}:
        raise HTTPException(403,'BCA department only.')
    records=db.query(DiscussionDigest).order_by(DiscussionDigest.id.desc()).limit(30).all()
    return {'items':[{'slot':r.slot,'status':r.status,'summary':r.summary,'topics':json.loads(r.topics_json),
                      'review_flags':json.loads(r.review_flags_json),'posts':r.post_count,'comments':r.comment_count} for r in records]}


@router.post('/review-now')
def request_review(user:User=Depends(csrf_required),db:DbSession=Depends(get_db)):
    if user.role!='hod' or user.department.strip().lower() not in {'bca','computer applications','bachelor of computer applications'}:
        raise HTTPException(403,'BCA HOD only.')
    # Run in background worker next polling interval; cannot bypass one review per 6h slot.
    return {'slot':current_slot(),'message':'Scheduled summary is generated once per six-hour reporting interval while the worker is running.'}
