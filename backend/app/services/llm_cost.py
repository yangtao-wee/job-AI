from datetime import datetime, timedelta, timezone

from ..config import settings
from ..schemas import TokenUse

BEIJING_TZ = timezone(timedelta(hours=8))

def read_use(res)->TokenUse:
    usage=getattr(res,'usage',None)
    # getattr(对象, '属性名', 默认值)
    if usage is None:
        return TokenUse()
    return TokenUse(
        input_tokens=getattr(usage,'input_tokens',getattr(usage,'prompt_tokens',0)),
        output_tokens=getattr(usage,'output_tokens',getattr(usage,'completion_tokens',0)),
        total_tokens=getattr(usage,'total_tokens',0)
    )


def calc_fee(use: TokenUse, in_price=None, out_price=None) -> float:
    in_price = settings.llm_in_price if in_price is None else in_price
    out_price = settings.llm_out_price if out_price is None else out_price
    in_fee = use.input_tokens / 1_000_000 * in_price
    out_fee = use.output_tokens / 1_000_000 * out_price
    return round(in_fee + out_fee, 6)


def estimate_fee(
    use: TokenUse, model: str, hour: int | None = None
) -> float | None:
    if model == 'deepseek-ai/DeepSeek-V3.2':
        price = (4.0, 6.0)
    elif model == 'deepseek-ai/DeepSeek-V4-Flash':
        if hour is None:
            hour = datetime.now(BEIJING_TZ).hour
        price = (1.5, 4.5) if 2 <= hour < 8 else (3.0, 9.0)
    else:
        return None
    in_price, out_price = price
    return calc_fee(use, in_price, out_price)
