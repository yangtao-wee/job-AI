from ..config import settings
from ..schemas import TokenUse

def read_use(res)->TokenUse:
    if getattr(res,'usage',None) is None:
# getattr：【语言固定，Python内置】安全获取对象属性，不需要导入
        return TokenUse()
    return TokenUse(
        input_tokens=res.usage.input_tokens,
        output_tokens=res.usage.output_tokens,
        total_tokens=res.usage.total_tokens
    )

def calc_fee(use:TokenUse)->float:
    in_fee=use.input_tokens/1_000_000*settings.llm_in_price
    out_fee=use.output_tokens/1_000_000*settings.llm_out_price
    return round(in_fee+out_fee,6)