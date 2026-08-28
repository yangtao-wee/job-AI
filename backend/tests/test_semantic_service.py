import pytest
# 自动化测试框架。
from app.services.semantic_service import calc_sim
# 从语义服务部门拿来相似度计算工具。

@pytest.mark.slow
# @：装饰器写法，给函数附加信息
# 【第三方库】pytest.mark：给测试添加标记。
# 【项目约定】slow：我们登记的慢测试类别。
# 删除影响：快速测试无法跳过AI模型，仍会等待很久。
def test_sim():
    near=calc_sim('使用FastAPI开发后端接口','构建Python REST API服务器')
    far=calc_sim('使用FastAPI开发后端接口','负责线下门店销售')
    assert near>far
    # near：接近的意思
# assert：断言，要求后面的条件必须成立。