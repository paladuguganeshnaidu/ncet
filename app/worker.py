"""Crash-recoverable simple DB-backed verifier; deploy one worker replica."""
import logging
import os
import signal
import time
from datetime import timedelta
from sqlalchemy import or_
from .database import DBSession, Verification, utcnow
from .verification import run_job
from .taskflow import run_task_once, run_task_reminder_once
from .reference_rules import run_rule_draft_once
from .discussion_digest import summarize_slot

logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'))
stop=False

def shutdown(*_):
    global stop
    stop=True


def run_once():
    with DBSession() as db:
        deadline=utcnow()-timedelta(minutes=25)
        # PostgreSQL SKIP LOCKED avoids double-claiming if you later add workers.
        query=(db.query(Verification).filter(or_(Verification.state=='queued',
                 (Verification.state=='processing') & (Verification.started_at<deadline)))
               .order_by(Verification.id).with_for_update(skip_locked=True))
        job=query.first()
        if not job:return False
        job.state='processing';job.started_at=utcnow();job_id=job.id
        db.commit()
    run_job(job_id)
    return True

def main():
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    next_reminder_check=0.0
    reminder_check_interval=15*60
    reminder_batches_per_check=10
    while not stop:
        try:
            now=time.monotonic()
            if now>=next_reminder_check:
                for _ in range(reminder_batches_per_check):
                    if not run_task_reminder_once():break
                next_reminder_check=now+reminder_check_interval
            if run_once():continue
            if run_task_once():continue
            if run_rule_draft_once():continue
            summarize_slot()
            time.sleep(3)
        except Exception:
            logging.exception('Document verifier iteration failed')
            time.sleep(6)

if __name__=='__main__':main()
