"""Faculty sessions can enter the protected task workspace after sign-in."""


def test_tasks_landing_is_protected_and_supports_all_faculty_roles(client,login):
    assert client.get('/tasks').status_code==401
    for username in ('admin','hod','staff','principal','iqac'):
        login(client,username)
        response=client.get('/tasks')
        assert response.status_code==200,(username,response.text[:300])
        assert '<h1 id="heading">Task management</h1>' in response.text
