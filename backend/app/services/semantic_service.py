from sentence_transformers import SentenceTransformer
# SentenceTransformer【第三方库】，负责加载Embedding模型。
MODEL='BAAI/bge-small-zh-v1.5'
# MODEL：【自己命名】，模型地址常量；大写表示团队约定“不随便修改”。
_model=None

def get_model():
    global _model
    # global：【语言固定】，允许函数修改外面的_model。
    if _model is None:
        # 只有第一次才加载模型。

        _model=SentenceTransformer(MODEL,local_files_only=True)
        # 从电脑本地仓库加载指定的Embedding模型，不再访问互联网检查更新。
        # local_files_only：【第三方库固定参数】，中文是“仅使用本地文件”，不能改名。
    return _model

def calc_sim(a:str,b:str)->float:
    # calc_sim【自己命名】，计算相似度。
    vec=get_model().encode([a,b],normalize_embeddings=True)
    # encode：【第三方库】，把文字转换成数字向量。
    # normalize_embeddings=True：把向量统一长度，方便比较。
    return float(vec[0] @ vec[1])
# float()：【语言固定】，把结果转换成普通小数。