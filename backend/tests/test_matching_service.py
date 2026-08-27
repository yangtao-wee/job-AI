from app.services.matching_service import calculate_required_skill_score

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