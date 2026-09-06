import logging
from types import SimpleNamespace as NS
from app.schemas import ResumeProfile
from app.services import resume_build_service as service
from app.services import llm_service as llm

def test_profile_logs_token_use(monkeypatch,caplog):
    monkeypatch.setattr(service.settings,'llm_mock_mode',False)
    monkeypatch.setattr(service.settings,'llm_model','test-model')
    monkeypatch.setattr(service,'get_llm_client',lambda:object())
    profile = ResumeProfile(target='Python后端开发工程师')
    response = NS(
        choices=[NS(message=NS(content=profile.model_dump_json()))],
        usage=NS(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    )
    monkeypatch.setattr(
        llm, 'call_json_model',
        lambda client, messages, model: response
    )
    with caplog.at_level(logging.INFO):
        service.build_profile('我做过三个Python后端项目','Python后端开发工程师')
    assert caplog.text.count('total=120') == 1