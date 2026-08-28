from app.services.ai_match_service import make_mock,make_prompt
from app.services import ai_match_service as ai_match

# 【整段代码作用】：检查模拟解释最多返回3条内容，并检查提示词包含安全要求和真实分数。
# 【在项目中的用途】：以后修改 AI 解释代码时，pytest 会像“质检员”一样自动检查旧功能有没有坏。

def test_mock_limit():
    note=make_mock(['Python','FastAPI','Vue','MySQL'],['Docker','Redis','RAG','Agent'])
    assert len(note.reasons)==3
    assert len(note.gaps)==3
    assert len(note.actions)==3

def test_prompt_safe():
    text=make_prompt(81,0.737,['Python'],['Docker'])
    assert '不得修改分数' in text
    assert '81/100' in text


# 【整段代码作用】：假装LLM客户端发生故障，确认explain()能够接住错误并返回降级解释。
# 【在项目中的用途】：以后测试不需要真实密钥、网络或模型额度。
def test_fallback(monkeypatch):
    monkeypatch.setattr(ai_match.settings,'llm_mock_mode',False)
    # monkeypatch：【框架提供】，pytest看到这个参数后会自动提供临时替换工具，不需要导入。
    # monkeypatch.setattr(...)：暂时把Mock模式改成False，强制程序进入真实模型分支。
    def fail():
        raise RuntimeError('模拟故障')
    monkeypatch.setattr(ai_match,'get_llm_client',fail)
    note=ai_match.explain(81,0.737,['Python'],['Docker'])
    assert note.summary=='AI解释暂时不可用，当前展示规则结果'
    assert note.gaps==['Docker']
