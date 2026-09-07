import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routers import users as users_router

client = TestClient(app)
CODE = 'test-invite-code'


@pytest.fixture(autouse=True)
def fixed_code(monkeypatch):
    monkeypatch.setattr(users_router.settings, 'register_code', CODE)


def new_user():
    tag = uuid.uuid4().hex[:8]
    return {
        'username': f'u_{tag}',
        'email': f'{tag}@example.com',
        'password': 'Test123456',
    }

def test_register_ok():
    res = client.post('/users/register', json={**new_user(), 'invite_code': CODE})
    assert res.status_code == 201
    assert 'password' not in res.json()


def test_register_wrong_code():
    res = client.post('/users/register', json={**new_user(), 'invite_code': 'wrong'})
    assert res.status_code == 403


def test_register_no_code():
    res = client.post('/users/register', json=new_user())
    assert res.status_code == 403


def test_register_duplicate():
    user = new_user()
    client.post('/users/register', json={**user, 'invite_code': CODE})
    res = client.post('/users/register', json={**user, 'invite_code': CODE})
    assert res.status_code == 409

def test_login_ok():
    user = new_user()
    client.post('/users/register', json={**user, 'invite_code': CODE})
    res = client.post('/users/login', json={
        'username': user['username'], 'password': user['password']
    })
    assert res.status_code == 200
    assert res.json().get('access_token')


def test_login_wrong_password():
    user = new_user()
    client.post('/users/register', json={**user, 'invite_code': CODE})
    res = client.post('/users/login', json={
        'username': user['username'], 'password': 'WrongPass999'
    })
    assert res.status_code == 401


def test_login_no_such_user():
    res = client.post('/users/login', json={
        'username': 'nobody_here_at_all', 'password': 'Test123456'
    })
    assert res.status_code == 401


def login(user):
    client.post('/users/register', json={**user, 'invite_code': CODE})
    res = client.post('/users/login', json={
        'username': user['username'], 'password': user['password']
    })
    return res.json()['access_token']


def test_token_works():
    token = login(new_user())
    res = client.get('/users/me', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200


def test_logout_all_invalidates_old_token():
    token = login(new_user())
    head = {'Authorization': f'Bearer {token}'}

    assert client.post('/users/logout-all', headers=head).status_code == 204
    assert client.get('/users/me', headers=head).status_code == 401


def test_new_token_works_after_logout_all():
    user = new_user()
    old = login(user)
    client.post('/users/logout-all', headers={'Authorization': f'Bearer {old}'})

    res = client.post('/users/login', json={
        'username': user['username'], 'password': user['password']
    })
    new = res.json()['access_token']

    assert client.get('/users/me', headers={'Authorization': f'Bearer {new}'}).status_code == 200
    assert client.get('/users/me', headers={'Authorization': f'Bearer {old}'}).status_code == 401