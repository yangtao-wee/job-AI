import pytest
from app.schemas import JobRequirementResult,NeedDraft,NeedDrafts
from app.services import ai_job_service as ai_job


# 岗位Service有没有把正确Prompt、Schema、模型传给适配层
def test_call_job_analysis_model(monkeypatch):
    expected = object()
    # 这里创建了一个独一无二的 Python 对象。

    def fake_call(client, prompt, schema, model):
        assert client == 'client'
        assert 'Python岗位' in prompt
        # 因为最终 Prompt 很可能长这样
        assert schema is JobRequirementResult
        assert model == 'test_model'
        return expected, 'response'

    monkeypatch.setattr(ai_job, 'get_llm_client', lambda: 'client')
    # lambda：【语言固定】创建一个简短匿名函数。
    monkeypatch.setattr(ai_job, 'call_structured', fake_call)
    monkeypatch.setattr(ai_job.settings, 'llm_model', 'test_model')
    result = ai_job.call_job_analysis_model('Python岗位')
    assert result is expected
    # 这里用 is，是为了验证：result 和 expected 是不是同一个对象。
    # 岗位服务正确取出了结构化调用返回的第一个结果，没有返回原始响应，也没有偷偷修改结果。

@pytest.mark.parametrize('start,end,quote', [
    (0, 1, '熟练掌握至少一种开发语言，\n例如 Python、Java 或 Go。'),
    (3, 3, '有电商经验者优先。'),
    (1, 0, None),
    (0, 4, None),
    (2, 2, None),
])
def test_need_quote(monkeypatch, start, end, quote):
    jd = '熟练掌握至少一种开发语言，\n例如 Python、Java 或 Go。\n\n有电商经验者优先。'
    draft = NeedDrafts(items=[
        NeedDraft(text='测试要求', kind='技能', start=start, end=end)
    ])
    monkeypatch.setattr(ai_job, 'get_llm_client', lambda: None)
    monkeypatch.setattr(ai_job, 'call_structured', lambda *args: (draft, None))

    if quote is None:
        with pytest.raises(ValueError, match='岗位原文'):
            ai_job.get_needs(jd)
        return

    result = ai_job.get_needs(jd)
    assert len(result.items) == 1
    assert result.items[0].id == 0
    assert result.items[0].quote == quote
    assert result.items[0].quote in jd