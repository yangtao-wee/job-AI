from pathlib import Path
# pathlib 专门帮助 Python 处理文件路径。
KB_FILE=Path(__file__).resolve().parent.parent/'data'/'job_guide.txt'
# resolve() 【Path提供的方法】负责得到更加完整、规范的绝对路径。
# parent返回上一层目录。
# 现在资料开始由后端文件管理，
# 为下一步“前端只发送问题，后端自己检索资料”做准备
def load_parts()->list[str]:
    text=KB_FILE.read_text(encoding='utf-8')
    # read_text读取文件内容
    return [p.strip() for p in text.split('\n\n') if p.strip()]
# 空字符串在 if 判断里相当于 False，所以不要它。
# \n\n每遇到一个空行，就切一刀