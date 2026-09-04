from fastapi.testclient import TestClient
from app.main import app
from  types import SimpleNamespace as NS
from app.routers import jobs
from app.dependencies import get_current_user,get_db
from app.schemas import JobAssistResponse,TailorResult,Scoreminxi
client=TestClient(app)

def test_job_assist_unauth():
    response=client.post('/jobs/assist',json={
        'resume_id':1,
        'job_title':'Python后端',
        'company':'某公司',
        'jd_text':'负责Python和FastAPI后端开发，要求掌握Docker'
    })
    assert response.status_code==401

def test_job_assist_ok(monkeypatch):
    expected=JobAssistResponse(
        resume_id=1,
        score=80,
        parts=Scoreminxi(skill=35, exp=20, role=5),
        matched_skills=['Python'],
        missing_skills=['docker'],
        tailoring=TailorResult(
            summary='建议',suggestions=[],missing_requirements=['Docker']
        ),
        greeting='您好'
    )
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:object()
    monkeypatch.setattr(
        jobs,'get_user_resume_analysis',lambda db,resume_id,user_id:NS())
    monkeypatch.setattr(jobs,'assist_job',lambda request,analysis:expected)
    response=client.post('/jobs/assist',json={
        'resume_id':1,
        'job_title':'Python后端',
        'company':'某公司',
        'jd_text':'负责Python和FastAPI后端开发，要求掌握Docker。'
    })
    app.dependency_overrides.clear()
    assert(response.status_code,response.json()['score'])==(200,80)
    assert response.json()['parts'] == {'skill': 35, 'exp': 20, 'role': 5}

def test_job_assist_resume_not_found(monkeypatch):
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    # dependency_overrides这是 FastAPI 专门给测试用的“依赖替换表”。
    app.dependency_overrides[get_db]=lambda:object()
    monkeypatch.setattr(
        jobs,'get_user_resume_analysis',
        lambda db,resume_id,user_id:None
    )
    response=client.post('/jobs/assist',json={
        'resume_id':99,
        'job_title':'Python后端',
        'company':'某公司',
        'jd_text':'负责Python和FastAPI后端开发，要求掌握Docker。'
    })
    app.dependency_overrides.clear()
    assert response.status_code==404
