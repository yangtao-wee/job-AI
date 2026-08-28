from app.services.semantic_service import calc_sim
# 从语义服务部门拿来相似度计算工具。

def test_sim():
    near=calc_sim('使用FastAPI开发后端接口','构建Python REST API服务器')
    far=calc_sim('使用FastAPI开发后端接口','负责线下门店销售')
    assert near>far
    # near：接近的意思
# assert：断言，要求后面的条件必须成立。