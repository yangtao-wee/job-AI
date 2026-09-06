from fastapi.testclient import TestClient
from app.main import app
from app import main

client=TestClient(app)


def test_health_ok(monkeypatch):
    monkeypatch.setattr(main,'check_db',lambda:True)
    monkeypatch.setattr(main,'cache_ready',lambda:True)
    res=client.get('/health')
    assert res.status_code==200
    assert res.json()=={'status':'ok','database':'up','cache':'up'}


def test_health_cache_down_stays_200(monkeypatch):
    monkeypatch.setattr(main,'check_db',lambda:True)
    monkeypatch.setattr(main,'cache_ready',lambda:False)
    res=client.get('/health')
    assert res.status_code==200
    assert res.json()['status']=='degraded'
    assert res.json()['cache']=='down'


def test_health_db_down_returns_503(monkeypatch):
    monkeypatch.setattr(main,'check_db',lambda:False)
    monkeypatch.setattr(main,'cache_ready',lambda:True)
    res=client.get('/health')
    assert res.status_code==503