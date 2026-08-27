from app.services.matching_service import calculate_required_skill_score,calculate_skill_score,merge_job_skills,calculate_experience_score,score_role

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