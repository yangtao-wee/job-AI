from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user
from app.routers import resumes
from app.services import resume_build_service

client=TestClient(app)

def test_profile_build_passes_target(monkeypatch):
    app.dependency_overrides[get_current_user]=lambda:object()
    monkeypatch.setattr(resumes,'build_profile',
        lambda raw,target='':{'name':'测试','target':target})
    res=client.post('/resumes/profile/build',json={
        'raw':'我做过三个Python后端项目',
        'target':'Python后端开发工程师'
    })
    app.dependency_overrides.clear()
    assert (res.status_code,res.json()['target'])==(200,'Python后端开发工程师')

def test_profile_mock_keeps_target(monkeypatch):
    monkeypatch.setattr(
        resume_build_service.settings,'llm_mock_mode',True
    )
    result=resume_build_service.build_profile(
        '我做过三个Python后端项目','Python后端开发工程师'
    )
    assert result.target=='Python后端开发工程师'

def test_profile_build_unauth():
    app.dependency_overrides.clear()
    res=client.post('/resumes/profile/build',json={
        'raw':'我做过三个Python后端项目'
    })
    assert res.status_code==401

def test_profile_build_rejects_short_raw():
    app.dependency_overrides[get_current_user]=lambda:object()
    res=client.post('/resumes/profile/build',json={'raw':'太短'})
    app.dependency_overrides.clear()
    assert res.status_code==422

def fail_profile(raw,target=''):
    raise RuntimeError('模型真实错误')

def test_profile_build_logs_failure(monkeypatch,caplog):
    app.dependency_overrides[get_current_user]=lambda:object()
    monkeypatch.setattr(resumes,'build_profile',fail_profile)
    with caplog.at_level('ERROR'):
        res=client.post('/resumes/profile/build',json={
            'raw':'我做过三个Python后端项目'
        })
    app.dependency_overrides.clear()
    assert res.status_code==502
    assert res.json()['detail']=='简历整理失败，请稍后重试'
    assert '简历整理失败' in caplog.text