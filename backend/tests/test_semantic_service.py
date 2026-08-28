import json
# 【语言自带模块】，负责读取JSON，名字不能修改。
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


# 【整段代码作用】：计算3个岗位的语义相似度，并检查推荐排名。
# 【在项目中的用途】：证明Embedding确实把Python岗位排在最前面。
@pytest.mark.slow
def test_sem_rank():
    data=json.load(open('tests/data/match_cases.json',encoding='utf-8'))
    user=data['user']
    cv_text=' '.join(user['skills']+user['work']+user['roles'])
    rows=[]
    for job in data['jobs']:
        job_text=' '.join([job['title'],job['desc']]+job['skills']+job['duties'])
        rows.append((calc_sim(cv_text,job_text),job['id']))
    rows.sort(reverse=True)
    assert [row[1] for row in rows]==[1,2,3]