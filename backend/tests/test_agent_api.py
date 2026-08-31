from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user
from app.routers import agent

client=TestClient(app)
# TestClient：【框架提供】模拟浏览器或前端请求 FastAPI。
def test_agent_unauth():
    res=client.post('/agent/ask',json={'goal':'查询Docker'})
    # json：【框架提供的参数名】以 JSON 格式提交数据，不能随意改。
    assert res.status_code==401

def fake_user():
    return object()

def fake_answer(goal):
    return f'测试Agent回答:{goal}'

def test_agent_ok(monkeypatch):
    app.dependency_overrides[get_current_user]=fake_user
    # 【框架提供】临时替换 FastAPI 的登录依赖。
    monkeypatch.setattr(agent,'ask_agent',fake_answer)
    res=client.post('/agent/ask',json={'goal':'查询Docker'})
    app.dependency_overrides.clear()
    assert (res.status_code,res.json()['answer'])==(200,'测试Agent回答:查询Docker')
    # res.json()：【框架提供】把响应 JSON 转成 Python 字典。

def test_agent_bad():
    app.dependency_overrides[get_current_user]=fake_user
    res=client.post('/agent/ask',json={'goal':' '})
    app.dependency_overrides.clear()
    assert res.status_code==422

def test_agent_extra():
    app.dependency_overrides[get_current_user]=fake_user
    res=client.post('/agent/ask',json={'goal':'查询Docker','command':'delete_db'})
    app.dependency_overrides.clear()
    assert res.status_code==422
