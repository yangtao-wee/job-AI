from types import SimpleNamespace as NS
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

class Func:
    name='find_kb'
    arguments='{"q":"部署"}'


class FakeCall:
    id='call_1'
    function=Func()

def fake_run(name,args):
    return '测试结果'

def test_run_call(monkeypatch):
    monkeypatch.setattr(agent,'run_tool',fake_run)
    item=agent.run_call(FakeCall())
    assert item['tool_call_id']=='call_1'
    assert item['content']=='测试结果'

class FakeComp:
    def create(self,**kwargs):
# **kwargs：【语言固定】接收所有“参数名=值”形式的参数。
        return kwargs

class FakeChat:
    completions=FakeComp()

class FakeClient:
    chat=FakeChat()

def test_ask_model():
    msgs=[{'role':'user','content':'查Docker'}]
    data=agent.ask_model(FakeClient(),msgs)
    assert data['messages']==msgs
    assert data['tools'][0]['function']['name']=='find_kb'
    assert data['tool_choice']=='auto'

class BusyError(Exception):
    code='1305'

def test_ask_backup(monkeypatch):
    models=[]
    def fake_call(client,messages,model):
        models.append(model)
        if model=='main':
            raise BusyError()
        return '备用成功'
    monkeypatch.setattr(agent,'RateLimitError',BusyError)
    monkeypatch.setattr(agent,'call_model',fake_call)
    monkeypatch.setattr(agent.settings,'llm_model','main')
    monkeypatch.setattr(agent.settings,'llm_backup_model','backup')
    result=agent.ask_model(None,[])
    assert result=='备用成功'
    assert models==['main','backup']

class OtherRateError(Exception):
    code='9999'

def test_ask_non_busy_error(monkeypatch):
    models=[]
    def fake_call(client,messages,model):
        models.append(model)
        raise OtherRateError()
    monkeypatch.setattr(agent,'RateLimitError',OtherRateError)
    monkeypatch.setattr(agent,'call_model',fake_call)
    monkeypatch.setattr(agent.settings,'llm_model','main')
    monkeypatch.setattr(agent.settings,'llm_backup_model','backup')
    with pytest.raises(OtherRateError):
        # 我预期 agent.ask_model() 必须抛出 OtherRateError。
        agent.ask_model(None,[])
    assert models==['main']

def test_ask_busy_without_backup(monkeypatch):
    models=[]
    def fake_call(client,messages,model):
        models.append(model)
        raise BusyError()
    monkeypatch.setattr(agent,'RateLimitError',BusyError)
    monkeypatch.setattr(agent,'call_model',fake_call)
    monkeypatch.setattr(agent.settings,'llm_model','main')
    monkeypatch.setattr(agent.settings,'llm_backup_model',None)
    with pytest.raises(BusyError):
        agent.ask_model(None,[])
    assert models==['main']


# 用假模型验证完整的一轮 Agent。
def test_run_agent(monkeypatch):
    first=NS(
        content='',tool_calls=[FakeCall()],
        model_dump=lambda exclude_none:{'role':'assistant'}
    )
    last=NS(content='最终回答',tool_calls=None)
    replies=[
        NS(choices=[NS(message=first)]),
        NS(choices=[NS(message=last)])
    ]
    sent=[]
    def fake_ask(client,msgs):
        sent.append(list(msgs))
        return replies.pop(0)
    monkeypatch.setattr(agent,'ask_model',fake_ask)
    monkeypatch.setattr(agent,'run_tool',fake_run)
    assert agent.run_agent(None,'查Docker')=='最终回答'
    assert [m['role'] for m in sent[1]]==['system','user','assistant','tool']


# 避免不必要的第二次模型请求，降低延迟和费用。
def test_agent_direct(monkeypatch):
    msg=NS(content='直接回答',tool_calls=None)
    reply=NS(choices=[NS(message=msg)])
    calls=[]
    def fake_ask(client,msgs):
        calls.append(msgs)
        return reply
    monkeypatch.setattr(agent,'ask_model',fake_ask)
    assert agent.run_agent(None,'你好')=='直接回答'
    assert len(calls)==1

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