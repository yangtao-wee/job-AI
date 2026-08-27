from app.services.matching_service import calculate_required_skill_score,calculate_skill_score,merge_job_skills

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