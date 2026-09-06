import logging
from types import SimpleNamespace as NS
from app.schemas import ResumeProfile
from app.services import resume_build_service as service

def test_profile_logs_token_use(monkeypatch,caplog):
    monkeypatch.setattr(service.settings,'llm_mock_mode',False)
    monkeypatch.setattr(service.settings,'llm_model','test-model')
    monkeypatch.setattr(service,'get_llm_client',lambda:object())
    response=NS(usage=NS(
        prompt_tokens=100,completion_tokens=20,total_tokens=120
    ))
    monkeypatch.setattr(service,'call_structured',
        lambda client,prompt,schema,model:
        (ResumeProfile(target='Python后端开发工程师'),response))
    with caplog.at_level(logging.INFO):
        service.build_profile('我做过三个Python后端项目','Python后端开发工程师')
    assert 'total=120' in caplog.text