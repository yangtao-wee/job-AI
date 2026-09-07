from types import SimpleNamespace as NS
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user,get_db
from app.routers import leads

client=TestClient(app)


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