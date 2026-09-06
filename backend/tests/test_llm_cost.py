from app.schemas import TokenUse
from app.services.llm_cost import estimate_fee

def test_v3_fee():
    use = TokenUse(input_tokens=1_000_000, output_tokens=1_000_000)
    assert estimate_fee(use, 'deepseek-ai/DeepSeek-V3.2') == 10.0


def test_v4_fee():
    use = TokenUse(input_tokens=1_000_000, output_tokens=1_000_000)
    model = 'deepseek-ai/DeepSeek-V4-Flash'
    assert estimate_fee(use, model, hour=2) == 6.0
    assert estimate_fee(use, model, hour=8) == 12.0