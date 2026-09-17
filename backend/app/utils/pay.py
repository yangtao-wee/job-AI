import re

# BOSS 列表页的工资数字用了自定义字体：页面上看是数字，文字里是 U+E031 起的特殊字符，依次对应 0-9
PUA_ZERO = 0xE031
PAY = re.compile(r'(\d+(?:\.\d+)?)\s*[-~～—–]\s*(\d+(?:\.\d+)?)\s*[kK]')


def decode_pay(raw:str|None)->str:
    return ''.join(
        str(ord(c)-PUA_ZERO) if PUA_ZERO<=ord(c)<=PUA_ZERO+9 else c
        for c in (raw or '')
    )


def parse_pay_range(raw:str|None)->tuple[float,float]|None:
    # 月薪范围（K）；「元/天」「面议」这种读不到月薪的返回 None
    m=PAY.search(decode_pay(raw))
    return (float(m.group(1)),float(m.group(2))) if m else None


def parse_pay(raw:str|None)->float|None:
    pay=parse_pay_range(raw)
    return pay[0] if pay else None
