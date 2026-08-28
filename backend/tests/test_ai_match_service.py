from app.services.ai_match_service import make_mock,make_prompt


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
