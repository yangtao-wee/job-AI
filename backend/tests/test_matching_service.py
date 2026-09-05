import pytest

from app.services.matching_service import calculate_required_skill_score,calculate_skill_score,merge_job_skills,calculate_experience_score,score_role,score_pref
from app.services.matching_service import calculate_keyword_score

def test_partial_match():
    result = calculate_required_skill_score(
        ['Python','FastAPI','Vue3'],
        ['Python','FastAPI','RAG']
    )
    assert result.score == 10

def test_empty_requirements():
    result = calculate_required_skill_score(['Python'],[])
    assert result.score==0

def test_no_match():
    result = calculate_required_skill_score(['Vue3'],['Python'])
    assert result.score==0

def test_merged_skills_are_scored_one():
    merged_skills = merge_job_skills(
        'Python,FastAPI', ['Python','RAG']
    )
    result = calculate_skill_score(
        ['Python','FastAPI','Vue3'],merged_skills
    )
    assert merged_skills == ['fastapi','python','rag']
    assert  result.score==23

def test_exp_partial():
    result=calculate_experience_score(
        ['使用FastAPI开发Python接口'],
        ['负责Python接口开发','负责Docker部署']
    )
    assert result.score==15
    assert len(result.matches)==1
    assert result.missing_responsibilities==['负责Docker部署']

def test_exp_empty():
    result = calculate_experience_score(['负责vue页面'],[])
    assert result.score==0

def test_role_hit():
    res=score_role('Python开发工程师',['Python后端开发工程师'])
    assert res.score==10
    assert res.hit is True
    assert res.note=='共同方向:Python'

def test_role_miss():
    res=score_role('销售经理',['Python后端开发工程师'])
    assert res.score==0
    assert res.hit is False

def test_pref_hit():
    res=score_pref('深圳','15-20K','深圳',18)
    assert res.score==15

def test_pref_miss():
    res=score_pref('广州','12-15K','深圳',18)
    assert res.score==0

def test_pay_equal():
    res=score_pref('深圳','15-20K','深圳',20)
    assert res.pay_ok is True

def test_skill_names():
    result = calculate_skill_score(
        ['Python编程','Vue.js'],
        ['Python语言','Vue','Docker']
    )
    assert result.score==23
    assert result.matched_skills==['python','vue']
    assert result.missing_skills==['docker']

def test_skill_state():
    result=calculate_skill_score(
        ['正在学习Python','不会Docker'],
        ['Python','Docker']
    )
    assert result.score==0
    assert result.matched_skills==[]
    assert result.missing_skills==['docker','python']


# 关键词评分也应识别别名，保留原有返回文字的大小写。
def test_keyword_names():
    result = calculate_keyword_score(
        [' Python编程 ', 'Vue.js'], '要求Python、Vue和Docker'
    )
    assert result.score == 7
    assert result.matched_keywords == ['Python', 'Vue']
    assert result.missing_keywords == ['Docker']


# 同一要求的两个名称只能算一项，避免扩大分母而压低得分。
def test_required_names():
    result = calculate_required_skill_score(
        ['Python编程', 'Vue.js'],
        ['Python', 'Python语言', 'Vue', 'Docker', '   ']
    )
    assert result.score == 10
    assert result.matched_skills == ['python', 'vue']
    assert result.missing_skills == ['docker']


# 合并手填技能与AI提取技能时，先统一名称，再去重。
def test_merge_names():
    result = merge_job_skills(
        'Python编程,Vue.js, ', ['Python语言', 'Vue', '   ']
    )
    assert result == ['python', 'vue']


# 其余两个评分入口也不能把这两个状态描述当成技能命中。
def test_other_states():
    skills = ['正在学习Python', '不会Docker']
    keyword = calculate_keyword_score(skills, '要求Python和Docker')
    required = calculate_required_skill_score(skills, ['Python', 'Docker'])
    assert keyword.score == required.score == 0
    assert keyword.matched_keywords == required.matched_skills == []
    assert keyword.missing_keywords == ['Docker', 'Python']
    assert required.missing_skills == ['docker', 'python']


# 共同的宽泛词不足以给技术职责加分；未命中不等于候选人一定不会。
@pytest.mark.parametrize('work,need', [
    ('运用AI工具批量生成营销短视频', '负责AI平台架构设计'),
    ('负责客户接口沟通', '负责FastAPI接口开发'),
    ('整理客户数据库资料', '负责MySQL数据库性能优化'),
    ('部署门店运营活动', '负责Docker部署'),
    ('测试营销文案效果', '负责Python自动化测试'),
    ('收集客户需求', '根据需求开发FastAPI服务'),
    ('编写运营文档', '编写Redis技术文档'),
])
def test_exp_wide(work, need):
    result = calculate_experience_score([work], [need])
    assert result.score == 0
    assert result.matches == []
    assert result.missing_responsibilities == [need]


# 收紧规则后，明确技术词仍能命中，并返回原经历，不改写原文。
@pytest.mark.parametrize('work,need', [
    ('使用Python开发数据脚本', '负责Python脚本开发'),
    ('使用fastapi开发用户接口', '负责FastAPI接口开发'),
    ('使用Docker部署服务', '负责Docker部署'),
])
def test_exp_tech(work, need):
    result = calculate_experience_score([work], [need])
    assert result.score == 30
    assert len(result.matches) == 1
    assert result.matches[0].responsibility == need
    assert result.matches[0].resume_evidence == work
    assert result.missing_responsibilities == []


@pytest.mark.parametrize('work', [[], ['   ']])
def test_exp_no_work(work):
    result = calculate_experience_score(work, ['负责Python接口开发'])
    assert result.score == 0
    assert result.matches == []
    assert result.missing_responsibilities == ['负责Python接口开发']


# 方向词既要排除宽泛AI误判，也要保留真实存在的全栈方向线索。
@pytest.mark.parametrize('title,roles,score,note', [
    ('AIAgent全栈开发工程师', ['AI驱动的新媒体运营专家'], 0, '岗位方向未匹配'),
    ('AIAgent全栈开发工程师',
     ['AI驱动的新媒体运营专家', '数据分析师', '全栈开发工程师'], 10, '共同方向:全栈'),
    ('AIAgent全栈开发工程师', ['全栈开发工程师'], 10, '共同方向:全栈'),
    ('AI产品经理', ['产品经理'], 10, '共同方向:产品'),
    ('Vue前端工程师', ['Vue前端开发'], 10, '共同方向:Vue,前端'),
    ('AIAgent全栈开发工程师', [], 0, '岗位方向未匹配'),
])
def test_role_keys(title, roles, score, note):
    result = score_role(title, roles)
    assert result.score == score
    assert result.hit is (score > 0)
    assert result.note == note
