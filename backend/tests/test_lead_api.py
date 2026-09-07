from types import SimpleNamespace as NS
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user,get_db
from app.routers import leads

client=TestClient(app)


def test_list_leads_returns_page(monkeypatch):
    db=object()
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:db
    run=MagicMock(return_value=([],3))
    monkeypatch.setattr(leads,'list_leads',run)

    response=client.get('/leads?status=待投递&offset=1&limit=2')
    app.dependency_overrides.clear()

    assert response.status_code==200
    assert response.json()=={'items':[],'total':3,'offset':1,'limit':2}
    run.assert_called_once_with(db,7,'待投递',1,2)

def test_list_leads_rejects_large_limit(monkeypatch):
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:object()
    run=MagicMock()
    monkeypatch.setattr(leads,'list_leads',run)

    response=client.get('/leads?limit=201')
    app.dependency_overrides.clear()

    assert response.status_code==422
    run.assert_not_called()


def test_analyze_busy_skips_model(monkeypatch,caplog):
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:object()
    monkeypatch.setattr(leads,'load_proofs',lambda *args:['proof'])
    monkeypatch.setattr(leads,'take_lock',lambda key:None)
    run=MagicMock()
    monkeypatch.setattr(leads,'analyze_next',run)
    response=client.post('/leads/analyze',json={'resume_id':1,'min_score':60})
    app.dependency_overrides.clear()
    assert response.status_code==503
    assert 'lead_analysis_lock_unavailable' in caplog.text
    assert 'user_id=7' in caplog.text
    run.assert_not_called()

def test_analyze_failure_releases_lock(monkeypatch,caplog):
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:object()
    monkeypatch.setattr(leads,'load_proofs',lambda *args:['proof'])
    lock=object()
    monkeypatch.setattr(leads,'take_lock',lambda key:lock)
    fail=MagicMock(side_effect=RuntimeError('model down'))
    release=MagicMock()
    monkeypatch.setattr(leads,'analyze_next',fail)
    monkeypatch.setattr(leads,'free_lock',release)
    response=client.post('/leads/analyze',json={'resume_id':1,'min_score':60})
    app.dependency_overrides.clear()
    assert response.status_code==502
    assert 'lead_analysis_failed' in caplog.text
    assert 'resume_id=1' in caplog.text
    release.assert_called_once_with(lock)

def test_analyze_rate_limited(monkeypatch):
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:object()

    def blocked(*args, **kwargs):
        raise HTTPException(
            status_code=429,
            detail='请求次数过多，请稍后重试',
            headers={'Retry-After':'25'}
        )

    monkeypatch.setattr(leads,'check_limit',blocked)
    load=MagicMock()
    monkeypatch.setattr(leads,'load_proofs',load)

    response=client.post(
        '/leads/analyze',
        json={'resume_id':1,'min_score':60}
    )
    app.dependency_overrides.clear()

    assert response.status_code==429
    assert response.headers['retry-after']=='25'
    load.assert_not_called()