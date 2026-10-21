"""Performance guardrails for public roster queries and static resource caching."""
from sqlalchemy import event
from app.database import DBSession, User, engine
from app.student_models import BCAStudent
from app.student_profiles import StudentShowcase

def test_directory_and_sitemap_avoid_loading_blob_columns(client):
    with DBSession() as db:
        for index in range(24):
            user=User(username=f'1nc24bca{index:03d}',
                display_name=f'Example Student {index}',role='student',
                department='Computer Applications',active=True,password_hash='test')
            db.add(user);db.flush()
            db.add(BCAStudent(user_id=user.id,usn=f'1NC24BCA{index:03d}',
                              semester=3,must_change_password=False))
            db.add(StudentShowcase(student_id=user.id,published=True,
                photo_bytes=b'x'*100000,photo_mime='image/webp'))
        db.commit()
    statements=[]
    def capture(connection,cursor,statement,parameters,context,executemany):
        if statement.lstrip().lower().startswith('select'):
            statements.append(statement)
    event.listen(engine,'before_cursor_execute',capture)
    try:
        result=client.get('/api/bca/directory?limit=24')
        assert result.status_code==200,result.text
        data=result.json()
        assert data['total']==24 and len(data['items'])==24
        assert all(item['photo_url'] for item in data['items'])
        directory_queries=list(statements)
        assert len(directory_queries)<=4,('directory query budget',len(directory_queries))
        assert not any('photo_bytes' in sql.lower() for sql in directory_queries)
        statements.clear()
        html=client.get('/students/directory')
        assert html.status_code==200
        assert not any('photo_bytes' in sql.lower() for sql in statements)
        statements.clear()
        sitemap=client.get('/sitemap.xml')
        assert sitemap.status_code==200
        assert '1NC24BCA023' in sitemap.text
        assert not any('photo_bytes' in sql.lower() for sql in statements)
    finally:
        event.remove(engine,'before_cursor_execute',capture)
    print(f'PUBLIC QUERY BENCHMARK: directory SELECT statements = {len(directory_queries)} (24 students), image blob reads = 0')


def test_versioned_assets_use_bounded_cache_and_private_routes_do_not(client):
    versioned=client.get('/static/resume-profile.css?v=20261017-2')
    assert versioned.status_code==200
    assert 'max-age=3600' in versioned.headers.get('cache-control','')
    normal=client.get('/static/ncet-brand.svg')
    assert normal.status_code==200
    assert 'max-age=300' in normal.headers.get('cache-control','')
    directory=client.get('/api/bca/directory')
    assert 'no-store' in directory.headers.get('cache-control','')
    assert directory.headers.get('x-robots-tag','').startswith('noindex')
