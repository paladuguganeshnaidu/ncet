"""Admin DeepSeek configuration and private faculty navigation contracts."""
from cryptography.fernet import Fernet
from app.database import DBSession, IntegrationSetting, User


def test_public_students_navigation_hides_faculty(client):
    home=client.get('/')
    student=client.get('/students')
    assert home.status_code==200 and student.status_code==200
    assert '<small>College services</small>' not in home.text
    assert '<a href="/students">Student Portal</a>' in home.text
    assert 'href="/app"' not in home.text
    assert 'href="/app"' not in student.text


def test_bca_faculty_page_cannot_be_fetched_publicly(client,login):
    assert client.get('/bca/manage').status_code==401
    assert client.get('/static/bca-management.html').status_code==404
    assert 'noindex' in client.get('/bca/manage').headers.get('x-robots-tag','')
    login(client,'principal')
    assert client.get('/bca/manage').status_code==403
    token=client.get('/api/auth/me').json()['csrf']
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':token}).status_code==200
    login(client,'staff')
    assert client.get('/bca/manage').status_code==200
    with DBSession() as db:
        staff=db.query(User).filter(User.username=='staff').one()
        staff.department='Computer Applications';db.commit()
    assert client.get('/bca/manage').status_code==200
    assert 'noindex' in client.get('/bca/manage').headers.get('x-robots-tag','')


def test_admin_deepseek_priority_and_fallback(client,login,monkeypatch):
    monkeypatch.setenv('SETTINGS_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    assert client.get('/api/admin/integrations').status_code==401
    token=login(client,'admin')
    initial=client.get('/api/admin/integrations').json()
    assert initial['configured'] is False
    assert initial['deepseek_configured'] is False
    router=client.put('/api/admin/integrations/openrouter',
        headers={'X-CSRF-Token':token},json={'api_key':'test-router-key-long-enough-12345'})
    assert router.status_code==200,router.text
    interim=client.get('/api/admin/integrations').json()
    assert interim['configured'] and not interim['deepseek_configured']
    deepseek=client.put('/api/tasks/ai/key',headers={'X-CSRF-Token':token},
        json={'api_key':'test-deepseek-key-long-enough-12345'})
    assert deepseek.status_code==200,deepseek.text
    selected=client.get('/api/admin/integrations').json()
    assert selected['deepseek_configured'] is True
    assert selected['provider']=='DeepSeek'
    assert selected['model']
    with DBSession() as db:
        assert db.get(IntegrationSetting,'deepseek_key') is not None
        assert db.get(IntegrationSetting,'openrouter_key') is not None
    assert 'test-deepseek' not in str(selected)
