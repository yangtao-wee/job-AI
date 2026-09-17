import unicodedata

# BOSS 直聘的 JD 会把一部分汉字换成「部首字」：⼯⾏⽆ 看着和 工行无 一样，编码不同，
# 正则认不出来（「英语⽆要求」匹配不到「无要求」）。打分和保存前统一换回普通汉字。
KANGXI = {c: unicodedata.normalize('NFKC', chr(c)) for c in range(0x2F00, 0x2FD6)}
# NFKC 换错或换不了的：⾤ 应该是「采」；简化字部首没有标准对应，手动补上
KANGXI.update({ord(a): b for a, b in zip('⾤⻅⻉⻋⻓⻔⻚⻛⻜⻢⻥⻦⻬⻮⻰⻳', '采见贝车长门页风飞马鱼鸟齐齿龙龟')})


def plain_text(text):
    return text.translate(KANGXI) if text else text
