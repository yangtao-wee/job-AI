from ..config import settings
from ..schemas import TokenUse

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


def calc_fee(use:TokenUse)->float:
    in_fee=use.input_tokens/1_000_000*settings.llm_in_price
    out_fee=use.output_tokens/1_000_000*settings.llm_out_price
    return round(in_fee+out_fee,6)
