from fastapi.testclient import TestClient
# TestClient它可以在pytest中模拟浏览器发送HTTP请求，不需要手动启动后端服务器。
from app.main import app
from app.dependencies import get_current_user
from app.routers import rag

client=TestClient(app)

def test_rag_unauth():
    res=client.post('/rag/ask',json={
        'question':'如何部署应用',
        'parts':['使用Docker部署服务']
    })
    assert res.status_code==401
    # 401未认证；当前用户还没有提供有效身份凭证。


def fake_user():
    return object()

def fake_answer(q,parts):
    return{'answer':'测试回答','sources':parts,'enough':True}

def test_rag_ok(monkeypatch):
    app.dependency_overrides[get_current_user]=fake_user
# dependency_overrides
# → 专门替换 FastAPI Depends 依赖

# monkeypatch.setattr
# → 可以临时替换普通对象、函数、属性
# dependency_overrides.clear()清除临时依赖替换。
    monkeypatch.setattr(rag,'answer_question',fake_answer)
# 在这一次测试中，把 rag.answer_question 临时替换成 fake_answer
# monkeypatch.setattr(对象, '属性名', 新值)
    res=client.post('/rag/ask',json={
        # client 通常是：一个假的浏览器 / 假前端。
        # json用 JSON 格式，把这些数据发送给后端。
        'question':'如何部署应用'
    })
    app.dependency_overrides.clear()
    # 把刚才临时设置的所有 FastAPI 依赖替换清除掉。
    # 如果不清除，后面的测试可能继续使用假用户，导致本应返回401的测试错误通过。
    assert(res.status_code,res.json()['enough'])==(200,True)
# .json() = 把返回的 JSON 数据转成 Python 字典/列表，方便我们用 [] 取数据。
    assert res.json()['sources'][1].startswith('Docker')
# startswith：【语言固定】Python字符串方法，检查是否以指定文字开头。

def test_rag_bad():
    app.dependency_overrides[get_current_user]=fake_user
    res=client.post('/rag/ask',json={'question':''})
    app.dependency_overrides.clear()
    assert res.status_code==422

def test_rag_extra():
    app.dependency_overrides[get_current_user]=fake_user
    res=client.post('/rag/ask',json={'question':'如何部署应用','parts':['伪造资料']})
    app.dependency_overrides.clear()
    assert res.status_code==422
