"""Focused, direct-call regressions for recent HOD and student dashboard work."""
import json

import pytest
from fastapi import HTTPException

from app.database import DBSession, User
from app.student_models import BCAStudent, StudentCase, StudentCaseMessage
from app.student_services import list_cases
from app.taskflow import (
    ChecklistTemplateBody,
    TaskChecklistTemplate,
    archive_checklist_template,
    checklist_template_versions,
    create_checklist_template,
    list_checklist_templates,
    revise_checklist_template,
)


def checklist(name='Annual report', phrase='Department approval'):
    return ChecklistTemplateBody(name=name, rules=[{
        'id': 'approval_heading',
        'title': 'Include the approval heading',
        'type': 'required_heading',
        'required': True,
        'value': phrase,
        'instructions': 'Check the first page.',
    }])


def test_hod_checklist_versions_are_scoped_immutable_and_archivable():
    with DBSession() as db:
        hod=db.query(User).filter_by(username='hod').one()
        other_hod=db.query(User).filter_by(username='hod2').one()

        created=create_checklist_template(checklist(),user=hod,db=db)
        revised=revise_checklist_template(created['id'],
            checklist(phrase='Updated approval heading'),user=hod,db=db)

        versions=checklist_template_versions(created['id'],user=hod,db=db)['items']
        assert [item['version'] for item in versions]==[2,1]
        assert versions[0]['rules'][0]['value']=='Updated approval heading'
        assert versions[1]['rules'][0]['value']=='Department approval'
        assert revised['version']==2

        with pytest.raises(HTTPException) as denied:
            checklist_template_versions(created['id'],user=other_hod,db=db)
        assert denied.value.status_code==404

        archived=archive_checklist_template(created['id'],user=hod,db=db)
        assert archived=={'archived':True}
        assert list_checklist_templates(user=hod,db=db)['items']==[]
        assert len(checklist_template_versions(created['id'],user=hod,db=db)['items'])==2
        stored=db.query(TaskChecklistTemplate).filter_by(template_id=created['id']).order_by(
            TaskChecklistTemplate.version).all()
        assert all(not item.active for item in stored)


def test_checklist_templates_reject_rules_that_cannot_be_applied():
    with DBSession() as db:
        hod=db.query(User).filter_by(username='hod').one()
        invalid=ChecklistTemplateBody(name='Bad template',rules=[{
            'id':'approval_heading','title':'Include the approval heading',
            'type':'required_heading','required':True,'value':'   ',
        }])
        with pytest.raises(HTTPException) as error:
            create_checklist_template(invalid,user=hod,db=db)
        assert error.value.status_code==422
        assert db.query(TaskChecklistTemplate).count()==0


def test_student_case_summary_has_next_step_and_only_own_hod_reply_preview():
    with DBSession() as db:
        hod=db.query(User).filter_by(username='hod').one()
        student=User(username='1nc24bca771',display_name='Portal Student',role='student',
            department='Computer Applications',password_hash='unused',active=True)
        other=User(username='1nc24bca772',display_name='Other Student',role='student',
            department='Computer Applications',password_hash='unused',active=True)
        db.add_all([student,other]);db.flush()
        db.add_all([
            BCAStudent(user_id=student.id,usn=student.username.upper(),semester=3,must_change_password=False),
            BCAStudent(user_id=other.id,usn=other.username.upper(),semester=3,must_change_password=False),
        ])
        mine=StudentCase(reference='NCET-BCA-SMOKE771',student_id=student.id,
            department='Computer Applications',category='documentation',subject='Certificate status',
            description='Please share my certificate status.',status='in_review')
        theirs=StudentCase(reference='NCET-BCA-SMOKE772',student_id=other.id,
            department='Computer Applications',category='academics',subject='Other private case',
            description='Private details must stay private.',status='submitted')
        db.add_all([mine,theirs]);db.flush()
        db.add(StudentCaseMessage(case_id=mine.id,actor_id=hod.id,body='Your document is being checked.'))
        db.add(StudentCaseMessage(case_id=theirs.id,actor_id=hod.id,body='Other student private reply.'))
        db.commit()

        result=list_cases(status='all',category='all',search='',attention='all',from_date=None,
            to_date=None,sort='newest',offset=0,limit=30,user=student,db=db)
        assert result['all_total']==1
        item=result['items'][0]
        assert item['reference']=='NCET-BCA-SMOKE771'
        assert item['next_step']=='Your HOD is reviewing this request. Reply here if you have more details.'
        assert item['latest_hod_reply']=='Your document is being checked.'
        assert item['latest_hod_reply_at']
        assert 'student' not in item
        assert 'Other student' not in json.dumps(result)
