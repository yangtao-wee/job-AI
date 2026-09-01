from app.schemas import ResumeAIAnalysis
from app.services import ai_resume_service as ai_resume


def test_resume_fail(monkeypatch):
    # monkeypatch 临时替换程序里面某个东西。测试结束后自动恢复。
    monkeypatch.setattr(ai_resume.settings, 'llm_mock_mode', False)
    monkeypatch.setattr(ai_resume.settings, 'llm_model', 'test-model')

    def fail():
        raise RuntimeError('模拟故障')

    monkeypatch.setattr(ai_resume, 'get_llm_client', fail)
    res = ai_resume.analyze_resume_with_ai(1, '测试简历')
    assert res.ai_ok is False


def test_structured_fail(monkeypatch):
    monkeypatch.setattr(ai_resume.settings, 'llm_mock_mode', False)
    monkeypatch.setattr(ai_resume.settings, 'llm_model', 'test-model')
    monkeypatch.setattr(ai_resume, 'get_llm_client', lambda: 'client')

    def fail_call(client, prompt, schema, model):
        raise RuntimeError('模拟请求故障')

    monkeypatch.setattr(ai_resume, 'call_structured', fail_call)
    res = ai_resume.analyze_resume_with_ai(1, '测试简历')
    assert res.ai_ok is False


# 公司系统不能因为 AI 返回空数据就崩溃。
def test_empty(monkeypatch):
    monkeypatch.setattr(ai_resume.settings, 'llm_mock_mode', False)
    monkeypatch.setattr(ai_resume.settings, 'llm_model', 'test-model')
    monkeypatch.setattr(ai_resume, 'get_llm_client', lambda: 'client')

    def empty_call(client, prompt, schema, model):
        raise RuntimeError('大模型没有返回内容')

    monkeypatch.setattr(ai_resume, 'call_structured', empty_call)
    res = ai_resume.analyze_resume_with_ai(1, '测试简历')
    assert res.ai_ok is False


def test_structured_success(monkeypatch):
    monkeypatch.setattr(ai_resume.settings, 'llm_mock_mode', False)
    monkeypatch.setattr(ai_resume.settings, 'llm_model', 'test-model')
    monkeypatch.setattr(ai_resume, 'get_llm_client', lambda: 'client')
    expected = ResumeAIAnalysis(
        resume_id=999,
        summary='测试总结',
        skills=['Python'],
        work_experience=[],
        strengths=['后端开发'],
        improvement_suggestions=[],
        recommended_positions=['Python后端开发']
    )

    def fake_call(client, prompt, schema, model):
        assert client == 'client'
        assert '简历编号：1' in prompt
        assert '测试简历' in prompt
        assert schema is ResumeAIAnalysis
        assert model == 'test-model'
        return expected, object()

    monkeypatch.setattr(ai_resume, 'call_structured', fake_call)
    result = ai_resume.analyze_resume_with_ai(1, '测试简历')
    assert result is expected
    assert result.resume_id == 1
