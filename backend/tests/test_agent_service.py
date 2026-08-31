import json
import pytest
from app.schemas import RagSrc
from app.services import agent_service as agent

def fake_load():
    return ['测试资料']

def fake_pick(q,parts):
    return[(0.8,'Docker资料')]

def test_find_kb(monkeypatch):
    monkeypatch.setattr(agent,'load_parts',fake_load)
    monkeypatch.setattr(agent,'pick_rows',fake_pick)
    rows=agent.find_kb('如何部署')
    assert (rows[0].text,rows[0].score)==('Docker资料',0.8)

def fake_find(q):
    return [RagSrc(text='Docker资料',score=0.8)]

def test_run_tool(monkeypatch):
    monkeypatch.setattr(agent,'find_kb',fake_find)
    data=json.loads(agent.run_tool('find_kb',{'q':'部署'}))
    # json.loads：【语言标准库】把JSON字符串转换回Python数据。
    assert data==[{'text':'Docker资料','score':0.8}]

def test_run_bad():
    with pytest.raises(ValueError):
        # 我期待下面这段代码必须抛出 ValueError。
        agent.run_tool('delete_db',{})

class FakeCall:
    type='function_call'
    # function_call：【第三方SDK固定值】表示这是工具调用，不能随便改。
    name='find_kb'
    arguments='{"q":"部署"}'
    call_id='call_1'

def fake_run(name,args):
    return '测试结果'

def test_run_call(monkeypatch):
    monkeypatch.setattr(agent,'run_tool',fake_run)
    item=agent.run_call(FakeCall())
    assert item['call_id']=='call_1'
    assert item['output']=='测试结果'

class FakeRes:
    def create(self,**kwargs):
# **kwargs：【语言固定】接收所有“参数名=值”形式的参数。
        return kwargs

class FakeClient:
    responses=FakeRes()
    # responses：【第三方SDK接口结构】这里模拟真实客户端的属性名称。

def test_ask_model():
    data=agent.ask_model(FakeClient(),'查Docker')
    assert data['input']=='查Docker'
    assert data['tools'][0]['name']=='find_kb'
    assert data['tool_choice']=='auto'


# 用假模型验证完整的一轮 Agent。
class First:
    id='r1'
    output=[FackCall()]
    output_text=''

class Last:
    output_text='最终回答'

class AgentRes:
    def __init__(self):
        self.count=0

    def create(self,**kwargs):
        self.count+=1
        if self.count==1:
            return First()
        assert kwargs['previous_response_id']=='r1'
        assert kwargs['input'][0]['output']=='测试结果'
        return Last()

class AgentClient:
    def __init__(self):
        self.responses=AgentRes()

def test_run_agent(monkeypatch):
    monkeypatch.setattr(agent,'run_tool',fake_run)
    result=agent.run_agent(AgentClient(),'查Docker')
    assert result=='最终回答'


# 避免不必要的第二次模型请求，降低延迟和费用。
class Msg:
    type='message'

class Direct:
    output=[Msg()]
    output_text='直接回答'

class DirectRes:
    def __init__(self):
        self.count=0

    def create(self,**kwargs):
        self.count+=1
        return Direct()

class DirectClient:
    def __init__(self):
        self.responses=DirectRes()

def test_agent_direct():
    client=DirectClient()
    assert agent.run_agent(client,'你好')=='直接回答'
    assert client.responses.count==1


def fake_client():
    return 'client'

def fake_agent(client,goal):
    return f'{client}:{goal}'

def test_agent_mock(monkeypatch):
    monkeypatch.setattr(agent.settings,'llm_mock_mode',True)
    assert agent.ask_agent('查Docker')=='模拟Agent回答:查Docker'

def test_agent_real(monkeypatch):
    monkeypatch.setattr(agent.settings,'llm_mock_mode',False)
    monkeypatch.setattr(agent.settings,'llm_model','test-model')
    monkeypatch.setattr(agent,'get_llm_client',fake_client)
    monkeypatch.setattr(agent,'run_agent',fake_agent)
    assert agent.ask_agent('查Docker')=='client:查Docker'

def test_agent_no_model(monkeypatch):
    monkeypatch.setattr(agent.settings,'llm_mock_mode',False)
    monkeypatch.setattr(agent.settings,'llm_model',None)
    with pytest.raises(RuntimeError,match='未配置 LLM_MODEL'):
        # match：【pytest提供的参数】检查异常消息是否包含指定文字。
        agent.ask_agent('查Docker')