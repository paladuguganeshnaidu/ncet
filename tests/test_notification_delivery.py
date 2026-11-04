"""Notification totals, delivery state and recipient isolation."""
from fastapi.testclient import TestClient
from app.main import app
from app.database import DBSession,User
from app.notifications import AppNotification
from app.taskflow import TaskNotification


def test_read_all_is_csrf_protected_and_scoped_to_current_recipient(client,login):
    token=login(client,'staff')
    with DBSession() as db:
        users={u.username:u.id for u in db.query(User).all()}
        for recipient in ('staff','staff2'):
            db.add(AppNotification(recipient_id=users[recipient],text='Private academic request',link='/tasks',category='requests'))
            db.add(TaskNotification(user_id=users[recipient],text='Private assignment'))
        db.commit()
    inbox=client.get('/api/alerts/inbox').json()
    assert inbox['unread']==2
    assert all(item['at'].endswith('+00:00') for item in inbox['items'])
    assert client.post('/api/alerts/read-all').status_code==403
    assert client.get('/api/alerts/inbox').json()['unread']==2
    assert client.post('/api/alerts/read-all',headers={'X-CSRF-Token':token}).status_code==200
    assert client.get('/api/alerts/inbox').json()['unread']==0
    assert client.get('/api/tasks/notifications/inbox').json()['unread']==0
    assert len(client.get('/api/alerts/inbox').json()['items'])==2
    with TestClient(app) as other:
        login(other,'staff2')
        assert other.get('/api/alerts/inbox').json()['unread']==2
        assert other.post('/api/alerts/'+inbox['items'][0]['id']+'/read',headers={'X-CSRF-Token':other.get('/api/auth/me').json()['csrf']}).status_code==404
    with TestClient(app) as anonymous:
        assert anonymous.post('/api/alerts/read-all').status_code==401


def test_unread_total_includes_notifications_outside_bounded_history(client,login):
    token=login(client,'staff')
    with DBSession() as db:
        user=db.query(User).filter_by(username='staff').one()
        db.add_all([AppNotification(recipient_id=user.id,text=f'Update {i}',link='/tasks',category='tasks') for i in range(90)])
        db.add_all([TaskNotification(user_id=user.id,text=f'Assignment {i}') for i in range(110)])
        db.commit()
    inbox=client.get('/api/alerts/inbox').json()
    assert inbox['unread']==200
    assert len(inbox['items'])==100
    assert client.get('/api/tasks/notifications/inbox').json()['unread']==110
    assert client.post('/api/alerts/read-all',headers={'X-CSRF-Token':token}).status_code==200
    assert client.get('/api/alerts/inbox').json()['unread']==0
