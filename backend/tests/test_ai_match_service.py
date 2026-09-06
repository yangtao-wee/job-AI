from types import SimpleNamespace as N
# SimpleNamespace：【标准库提供】，快速制造一个假的响应对象。
from app.schemas import TokenUse,MatchExplain
from app.services.ai_match_service import make_mock,make_prompt
from app.services.llm_cost import read_use,calc_fee
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
    assert '面向求职者本人' in text
    assert '不得擅自扩大' in text

def test_structured_success(monkeypatch):
    expected=MatchExplain(
        summary='匹配成功',reasons=['模型编造理由'],
        gaps=['模型编造缺口'],actions=['补充Docker项目']
    )
    monkeypatch.setattr(ai_match.settings,'llm_mock_mode',False)
    monkeypatch.setattr(ai_match,'get_llm_client',lambda:'client')
    def fake_call(client,prompt,schema,model):
        assert schema is MatchExplain
        return expected,N(usage=None)
    monkeypatch.setattr(ai_match,'call_structured',fake_call)
    result=ai_match.explain(81,0.737,['Python'],['Docker'])
    assert result is expected
    assert result.reasons==['Python']
    assert result.gaps==['Docker']


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


# Token自动化测试 自动化测试可以防止以后修改代码时破坏Token统计。
def test_token_use():
    res=N(usage=N(input_tokens=100,output_tokens=20,total_tokens=120))
    # 外层 N 制造响应，内层 N 制造 usage。
    use=read_use(res)
    assert use.total_tokens==120

def test_chat_completion_token_use():
    res=N(usage=N(prompt_tokens=100,completion_tokens=20,total_tokens=120))
    use=read_use(res)
    assert use.input_tokens==100
    assert use.output_tokens==20
    assert use.total_tokens==120


def test_token_empty():
    use=read_use(N(usage=None))
    assert use.total_tokens==0


def test_fee(monkeypatch):
    # monkeypatch：【框架提供】，临时修改配置，测试结束自动恢复。
    monkeypatch.setattr(ai_match.settings,'llm_in_price',1)
    monkeypatch.setattr(ai_match.settings,'llm_out_price',2)
    use=TokenUse(input_tokens=1_000_000,output_tokens=1_000_000)
    assert calc_fee(use)==3.0

def test_fee_empty():
    assert calc_fee(TokenUse())==0.0