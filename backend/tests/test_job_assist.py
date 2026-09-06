import pytest
from pydantic import ValidationError
from types import SimpleNamespace as NS
# SimpleNamespace：简单对象容器，【语言固定·标准库】，用来模拟数据库简历对象。

from app.services.job_assist_service import make_tailor_prompt
from app.schemas import JobAssistRequest,RewriteAdvice,TailorResult,JobAssistResponse,GreetingResult,JobRequirementResult,AdviceDraft,TailorDraft,Scoreminxi
from app.services import job_assist_service as assist

def test_job_assist_request_ok():
    request=JobAssistRequest(
        resume_id=1,
        job_title='Python后端',
        company='某公司',
        jd_text='负责Python和FastAPI后端开发，要求掌握Docker和MySQL。'
    )
    assert request.resume_id==1
    assert request.job_title=='Python后端'
    assert request.company=='某公司'

def test_job_assist_rejects_zero_resume_id():
    with pytest.raises(ValidationError):
        JobAssistRequest(
            resume_id=0,
            job_title='Python后端',
            company='某公司',
            jd_text='负责Python和FastAPI后端开发，要求掌握Docker和MySQL。'
        )

def test_job_assist_rejects_short_jd():
    with pytest.raises(ValidationError):
        JobAssistRequest(
            resume_id=1,
            job_title='Python后端',
            company='某公司',
            jd_text='太短'
        )

def test_job_assist_rejects_extra_field():
    with pytest.raises(ValidationError):
        JobAssistRequest(
            resume_id=1,
            job_title='Python后端',
            company='某公司',
            jd_text='负责Python和FastAPI后端开发，要求掌握Docker和MySQL。',
            unknown='不允许的字段'
        )

def test_tailor_result_ok():
    result=TailorResult(
        summary='建议突出后端开发经验',
        suggestions=[RewriteAdvice(
            requirement='掌握FastAPI',
            evidence='开发过FastAPI接口',
            rewrite='使用FastAPI完成认证和岗位接口开发'
        )],
        missing_requirements=['Docker']
    )
    assert result.suggestions[0].evidence=='开发过FastAPI接口'


def test_job_assist_response_rejects_high_score():
    with pytest.raises(ValidationError) as error:
        JobAssistResponse(
            resume_id=1,
            score=101,
            parts=Scoreminxi(skill=35, exp=30, role=10),
            matched_skills=[],
            missing_skills=[],
            tailoring=TailorResult(
                summary='',suggestions=[],missing_requirements=[]
            ),
            greeting=''
        )
    assert any(item['loc'] == ('score',) for item in error.value.errors())

def test_tailor_prompt_uses_evidence():
    text=make_tailor_prompt(
        '要求掌握Docker','掌握Python',['开发过FastAPI接口']
    )
    assert '不得编造' in text
    assert '不要生成改写文字' in text
    assert '<jd>要求掌握Docker</jd>' in text
    assert '开发过FastAPI接口' in text


def test_tailor_resume_calls_structured(monkeypatch):
    draft = TailorDraft(
        summary='建议', missing=['Docker'],
        items=[AdviceDraft(need='FastAPI', proof_id=1)]
    )
    def fake_call(client, prompt, schema, model):
        assert schema is TailorDraft
        assert '1:FastAPI项目' in prompt
        return draft, None
    monkeypatch.setattr(assist, 'get_llm_client', lambda: 'client')
    monkeypatch.setattr(assist, 'call_structured', fake_call)
    result = assist.tailor_resume('要求FastAPI和Docker', '总结', ['运营账号', 'FastAPI项目'])
    assert isinstance(result, TailorResult)
    assert len(result.suggestions) == 1
    assert result.suggestions[0].evidence == 'FastAPI项目'
    assert result.suggestions[0].rewrite == ''
    assert result.missing_requirements == ['Docker']

def test_draft_greeting_calls_structured(monkeypatch):
    expected=GreetingResult(greeting='您好，我有Python项目经验')
    def fake_call(client,prompt,schema,model):
        assert schema is  GreetingResult
        return expected,None
    monkeypatch.setattr(assist,'get_llm_client',lambda:'client')
    monkeypatch.setattr(assist,'call_structured',fake_call)
    result=assist.draft_greeting(
        'Python后端','某公司','FastAPI项目',['Python']
    )
    assert result=='您好，我有Python项目经验'

def test_greeting_without_skills(monkeypatch):
    def must_not_call():
        raise AssertionError('空技能时不应该创建大模型客户端')
    monkeypatch.setattr(assist,'get_llm_client',must_not_call)
    result=assist.draft_greeting('AI产品工程师','某公司','',[])
    assert result=='您好，我关注到某公司的AI产品工程师岗位，希望进一步了解岗位要求，期待与您沟通。'



def test_to_percent():
    assert assist.to_percent(85)==100
    assert assist.to_percent(42)==49
    assert assist.to_percent(100)==100
    with pytest.raises(ValueError):
        assist.to_percent(1,0)


def test_score_job_uses_rules():
    requirements=JobRequirementResult(
        responsibilities=['负责FastAPI接口开发'],
        required_skills=['Python','Docker'],
        experience=[],
        education=[],
        bonus_points=[]
    )
    score,matched,missing,parts=assist.score_job(
        ['Python'],['负责FastAPI接口开发'],['Python后端'],
        'Python后端','要求Python、FastAPI和Docker',requirements
    )
    assert score==69
    assert matched==['python']
    assert missing==['docker','fastapi']
    assert parts.model_dump() == {'skill': 12, 'exp': 30, 'role': 10}
    assert score == assist.to_percent(parts.skill + parts.exp + parts.role, 75)


def test_filter_advice_removes_fake_evidence():
    result=TailorResult(
        summary='建议',
        suggestions=[
            RewriteAdvice(
                requirement='Docker',
                evidence='虚构Docker项目',
                rewrite='突出Docker经验'
            ),
            RewriteAdvice(
                requirement='FastAPI',
                evidence='真实FastAPI项目',
                rewrite='突出接口经验'
            )
        ],
        missing_requirements=[]
    )
    filtered=assist.filter_advice(result,['真实FastAPI项目'])
    assert [item.requirement for item in filtered.suggestions]==['FastAPI']
    assert filtered.missing_requirements==['Docker']


def test_assist_job_combines_result(monkeypatch):
    request=JobAssistRequest(
        resume_id=1,job_title='Python后端',company='某公司',
        jd_text='负责Python和FastAPI后端开发，要求掌握Docker。'
    )
    analysis=NS(summary='FastAPI项目',
                skills=['Python'],
                work_experience=[],
                recommended_positions=[])
    requirements=JobRequirementResult(
                    responsibilities=[],
                    required_skills=[],
                    experience=[],
                    education=[],
                    bonus_points=[])
    tailoring=TailorResult(
                    summary='建议',
                    suggestions=[],
                    missing_requirements=[])
    monkeypatch.setattr(assist,'analyze_job_with_ai',lambda jd:requirements)
    parts = Scoreminxi(skill=35, exp=20, role=5)
    monkeypatch.setattr(assist,'score_job',lambda *args:(80,['Python'],['docker'],parts))
    monkeypatch.setattr(assist,'tailor_resume',lambda *args:tailoring)
    monkeypatch.setattr(assist,'draft_greeting',lambda *args:'您好')
    result=assist.assist_job(request,analysis)
    assert result.score==80
    assert result.greeting=='您好'
    assert result.parts.model_dump() == {'skill': 35, 'exp': 20, 'role': 5}

def test_tailor_resume_rejects_summary_as_evidence(monkeypatch):
    fake=TailorDraft(
        summary='建议',
        items=[AdviceDraft(
            need='Docker',
            proof_id=0
        )],
        missing=[]
    )
    monkeypatch.setattr(assist,'get_llm_client',lambda:'client')
    monkeypatch.setattr(
        assist,'call_structured',lambda *args:(fake,None)
    )
    result=assist.tailor_resume('要求Docker','模拟总结',[])
    assert result.suggestions==[]
    assert result.missing_requirements==['Docker']


# 发给模型的条目格式只保留岗位要求与引用编号。
def test_draft_fields():
    assert set(AdviceDraft.model_fields) == {'need', 'proof_id'}


# 故意模拟旧适配器仍带回rewrite字段，检查后端不能把它交给前端。
# 这里使用NS保留额外字段，避免测试仅因Schema忽略字段而意外通过。
def test_no_rewrite(monkeypatch):
    proof = '某公司 新媒体运营 2023.10-2026.07'
    draft = NS(
        summary='待核对资料',
        items=[NS(need='AI架构设计', proof_id=0, rewrite='负责大模型架构设计和编码')],
        missing=['Docker']
    )
    monkeypatch.setattr(assist, 'get_llm_client', lambda: 'client')
    monkeypatch.setattr(assist, 'call_structured', lambda *args: (draft, None))
    result = assist.tailor_resume('要求AI架构设计与Docker', '总结', [proof])
    assert len(result.suggestions) == 1
    assert result.suggestions[0].requirement == 'AI架构设计'
    assert result.suggestions[0].evidence == proof
    assert result.suggestions[0].rewrite == ''
    assert result.missing_requirements == ['Docker']


# 分项的边界属于接口约定，防止把百分制总分误传到某一个分项。
@pytest.mark.parametrize('field,value', [
    ('skill', -1), ('skill', 36),
    ('exp', -1), ('exp', 31),
    ('role', -1), ('role', 11),
])
def test_parts_limits(field, value):
    data = {'skill': 0, 'exp': 0, 'role': 0}
    data[field] = value
    with pytest.raises(ValidationError) as error:
        Scoreminxi(**data)
    assert any(item['loc'] == (field,) for item in error.value.errors())


def test_parts_endpoints():
    assert Scoreminxi(skill=0, exp=0, role=0).model_dump() == {
        'skill': 0, 'exp': 0, 'role': 0
    }
    assert Scoreminxi(skill=35, exp=30, role=10).model_dump() == {
        'skill': 35, 'exp': 30, 'role': 10
    }


def test_make_report_mock_skips_llm(monkeypatch):
    monkeypatch.setattr(assist.settings,'llm_mock_mode',True)
    monkeypatch.setattr(assist,'read_cache',lambda key:None)
    monkeypatch.setattr(
        assist,'get_needs',
        lambda jd:pytest.fail('Mock模式不应该调用真实模型')
    )
    result=assist.make_report('负责Python开发，要求掌握FastAPI。',['Python项目'])
    assert result.proofs==['Python项目']