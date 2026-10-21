"""Safe cleanup of expired sessions and old login throttling history."""
from datetime import timedelta
from .database import DBSession, Session, LoginFailure, utcnow

def main():
    with DBSession() as db:
        sessions = db.query(Session).filter(Session.expires_at < utcnow()).delete()
        failures = db.query(LoginFailure).filter(LoginFailure.at < utcnow()-timedelta(days=30)).delete()
        db.commit()
    print(f'Expired sessions: {sessions}; old failed sign-in records: {failures}')

if __name__=='__main__':main()
