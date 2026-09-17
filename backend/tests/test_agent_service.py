from types import SimpleNamespace as NS
from datetime import datetime
import logging
import json
import pytest
from app.schemas import RagSrc
from app.models import ResumeAnalysis
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

def test_find_jobs_only_returns_current_user():
    db=agent.SessionLocal()
    try:
        now=datetime.now()
        db.add_all([
            agent.JobLead(user_id=901,title='用户A高分岗',company='A',url='agent://a/high',quick_score=88,created_at=now,updated_at=now),
            agent.JobLead(user_id=901,title='用户A低分岗',company='A',url='agent://a/low',quick_score=59,created_at=now,updated_at=now),
            agent.JobLead(user_id=902,title='用户B高分岗',company='B',url='agent://b/high',quick_score=99,created_at=now,updated_at=now)
        ])
        db.commit()
        rows=agent.find_jobs(901,60,10)
        assert [(row['title'],row['score']) for row in rows]==[('用户A高分岗',88)]
        own=agent.get_job(901,rows[0]['id'])
        assert (own['found'],own['title'],own['change'])==(True,'用户A高分岗',0)
        assert '岗位状态不参与评分' in own['evidence_note']
        assert own['formula']=='最终88=基础88+净变化0（含100分上限）'
        assert agent.get_job(902,rows[0]['id'])=={'found':False}
    finally:
        db.rollback()
        db.query(agent.JobLead).filter(agent.JobLead.user_id.in_([901,902])).delete(synchronize_session=False)
        db.commit()
        db.close()

def test_get_resume_only_returns_current_user():
    db=agent.SessionLocal()
    try:
        now=datetime.now()
        resume=agent.Resume(
            user_id=903,original_filename='真实简历.pdf',
            stored_filename='agent_resume_903.pdf',content_type='application/pdf',
            file_size=100,created_at=now
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        db.add(ResumeAnalysis(
            resume_id=resume.id,summary='测试总结',skills=['Python'],
            work_experience=['使用Python开发接口'],
            projects=['使用FastAPI与Agent开发求职助手'],strengths=[],
            improvement_suggestions=[],recommended_positions=['AI应用助理'],
            created_at=now
        ))
        db.commit()
        own=agent.get_resume(903)
        assert own['proofs']==[
            {'id':'S1','text':'Python','source':'skill'},
            {'id':'W1','text':'使用Python开发接口','source':'work'},
            {'id':'P1','text':'使用FastAPI与Agent开发求职助手','source':'project'}
        ]
        assert agent.get_resume(904)=={'found':False,'reason':'未上传简历'}
    finally:
        db.rollback()
        db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id==resume.id).delete()
        db.query(agent.Resume).filter(agent.Resume.id==resume.id).delete()
        db.commit()
        db.close()

def fake_find(q):
    return [RagSrc(text='Docker资料',score=0.8)]

def test_run_tool(monkeypatch):
    monkeypatch.setattr(agent,'find_kb',fake_find)
    data=json.loads(agent.run_tool('find_kb',{'q':'部署'},7))
    # json.loads：【语言标准库】把JSON字符串转换回Python数据。
    assert data==[{'text':'Docker资料','score':0.8}]

def test_run_job_tool_uses_server_user(monkeypatch):
    seen={}
    def fake_jobs(user_id,min_score,limit):
        seen.update(user_id=user_id,min_score=min_score,limit=limit)
        return [{'title':'AI应用助理','score':80}]
    monkeypatch.setattr(agent,'find_jobs',fake_jobs)
    data=json.loads(agent.run_tool(
        'find_jobs',{'min_score':70,'limit':3},7
    ))
    assert data==[{'title':'AI应用助理','score':80}]
    assert seen=={'user_id':7,'min_score':70,'limit':3}

def test_run_detail_tool_uses_server_user(monkeypatch):
    seen={}
    def fake_job(user_id,job_id):
        seen.update(user_id=user_id,job_id=job_id)
        return {'found':True,'title':'AI应用助理'}
    monkeypatch.setattr(agent,'get_job',fake_job)
    data=json.loads(agent.run_tool('get_job',{'job_id':1011},7))
    assert data=={'found':True,'title':'AI应用助理'}
    assert seen=={'user_id':7,'job_id':1011}

def test_run_resume_tool_uses_server_user(monkeypatch):
    seen={}
    def fake_resume(user_id):
        seen['user_id']=user_id
        return {'found':True,'skills':['Python']}
    monkeypatch.setattr(agent,'get_resume',fake_resume)
    data=json.loads(agent.run_tool('get_resume',{},7))
    assert data=={'found':True,'skills':['Python']}
    assert seen=={'user_id':7}

def test_run_compare_tool_uses_server_user(monkeypatch):
    seen={}
    def fake_compare(user_id,job_id):
        seen.update(user_id=user_id,job_id=job_id)
        return {'found':True,'matched':[],'missing':['RPA/业务自动化']}
    monkeypatch.setattr(agent,'compare_job_resume',fake_compare)
    data=json.loads(agent.run_tool(
        'compare_job_resume',{'job_id':1011},7
    ))
    assert data['missing']==['RPA/业务自动化']
    assert seen=={'user_id':7,'job_id':1011}

def test_run_bad():
    with pytest.raises(ValueError):
        # 我期待下面这段代码必须抛出 ValueError。
        agent.run_tool('delete_db',{},7)

class Func:
    name='find_kb'
    arguments='{"q":"部署"}'


class FakeCall:
    id='call_1'
    function=Func()

class JobFunc:
    name='find_jobs'
    arguments='{"min_score":80,"limit":5}'

class DetailFunc:
    name='get_job'
    arguments='{"job_id":1011}'

class JobCall:
    id='call_jobs'
    function=JobFunc()

class DetailCall:
    id='call_detail'
    function=DetailFunc()

class ResumeFunc:
    name='get_resume'
    arguments='{}'

class ResumeCall:
    id='call_resume'
    function=ResumeFunc()

class CompareFunc:
    name='compare_job_resume'
    arguments='{"job_id":1011}'

class CompareCall:
    id='call_compare'
    function=CompareFunc()

def fake_run(name,args,user_id):
    return '测试结果'

def test_run_call(monkeypatch):
    monkeypatch.setattr(agent,'run_tool',fake_run)
    item=agent.run_call(FakeCall(),7)
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
    assert data['tools'][1]['function']['name']=='find_jobs'
    assert data['tools'][2]['function']['name']=='get_job'
    assert data['tools'][3]['function']['name']=='get_resume'
    assert data['tools'][4]['function']['name']=='compare_job_resume'
    assert 'user_id' not in data['tools'][1]['function']['parameters']['properties']
    assert 'user_id' not in data['tools'][2]['function']['parameters']['properties']
    assert 'user_id' not in data['tools'][3]['function']['parameters']['properties']
    assert 'user_id' not in data['tools'][4]['function']['parameters']['properties']
    assert data['tool_choice']=='auto'

def test_ask_model_logs_usage(monkeypatch, caplog):
    response = NS(usage=NS(
        prompt_tokens=50, completion_tokens=10, total_tokens=60
    ))
    monkeypatch.setattr(agent, 'call_model', lambda client, messages, model: response)
    monkeypatch.setattr(agent.settings, 'llm_model', 'main-model')
    with caplog.at_level(logging.INFO):
        result = agent.ask_model(None, [])
    assert result is response
    assert 'LLM调用Token用量 model=main-model' in caplog.text
    assert 'total=60' in caplog.text

class BusyError(Exception):
    pass

def test_ask_backup(monkeypatch,caplog):
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
    with caplog.at_level(logging.INFO):
        result=agent.ask_model(None,[])
    assert result=='备用成功'
    assert models==['main','backup']
    assert 'LLM调用Token用量 model=backup' in caplog.text
    assert 'LLM调用Token用量 model=main' not in caplog.text

def test_ask_other_exception_not_switched(monkeypatch):
    models=[]
    def fake_call(client,messages,model):
        models.append(model)
        raise ValueError('网络错误')
    monkeypatch.setattr(agent,'call_model',fake_call)
    monkeypatch.setattr(agent.settings,'llm_model','main')
    monkeypatch.setattr(agent.settings,'llm_backup_model','backup')
    with pytest.raises(ValueError):
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
    assert agent.run_agent(None,'查Docker',7)=='最终回答'
    assert [m['role'] for m in sent[1]]==['system','user','assistant','tool']
    rules=sent[0][0]['content']
    assert 'hits表示JD命中规则' in rules
    assert '不得声称“你具备”' in rules
    assert '岗位状态不参与评分' in rules
    assert '当前简历未发现' in rules
    assert 'S编号是技能' in rules
    assert 'W编号是经历' in rules
    assert '禁止捏造、串用' in rules
    assert 'FastAPI属于Web框架' in rules
    assert 'MySQL或SQLAlchemy' in rules
    assert '必须调用compare_job_resume' in rules
    assert 'missing只能表述为当前简历未发现' in rules
    assert '能力项名称必须逐字复制' in rules
    assert '禁止再说它缺少' in rules
    assert 'P编号是项目证据' in rules
    assert '不要输出#、*等Markdown符号' in rules

def test_agent_history_order(monkeypatch):
    msg=NS(content='继续回答',tool_calls=None)
    reply=NS(choices=[NS(message=msg)])
    sent=[]
    def fake_ask(client,msgs):
        sent.extend(msgs)
        return reply
    monkeypatch.setattr(agent,'ask_model',fake_ask)
    history=[
        {'role':'user','content':'目标是AI工程师'},
        {'role':'assistant','content':'已经记住'}
    ]
    assert agent.run_agent(None,'继续',7,history)=='继续回答'
    assert [item['role'] for item in sent]==[
        'system','user','assistant','user'
    ]
    assert sent[-1]['content']=='继续'

def test_agent_allows_two_tool_rounds(monkeypatch):
    tool_msg=NS(
        content='',tool_calls=[FakeCall()],
        model_dump=lambda exclude_none:{'role':'assistant'}
    )
    last=NS(content='两轮后完成',tool_calls=None)
    replies=[
        NS(choices=[NS(message=tool_msg)]),
        NS(choices=[NS(message=tool_msg)]),
        NS(choices=[NS(message=last)])
    ]
    monkeypatch.setattr(agent,'ask_model',lambda client,msgs:replies.pop(0))
    monkeypatch.setattr(agent,'run_tool',fake_run)
    assert agent.run_agent(None,'分两步查资料',7)=='两轮后完成'
    assert replies==[]

def test_agent_can_find_then_explain_job(monkeypatch):
    find_msg=NS(
        content='',tool_calls=[JobCall()],
        model_dump=lambda exclude_none:{'role':'assistant','tool_calls':['find']}
    )
    detail_msg=NS(
        content='',tool_calls=[DetailCall()],
        model_dump=lambda exclude_none:{'role':'assistant','tool_calls':['detail']}
    )
    last=NS(content='基础分65，JD加30，最终95',tool_calls=None)
    replies=[
        NS(choices=[NS(message=find_msg)]),
        NS(choices=[NS(message=detail_msg)]),
        NS(choices=[NS(message=last)])
    ]
    calls=[]
    def fake_tool(name,args,user_id):
        calls.append((name,args,user_id))
        return '{}'
    monkeypatch.setattr(agent,'ask_model',lambda client,msgs:replies.pop(0))
    monkeypatch.setattr(agent,'run_tool',fake_tool)
    result=agent.run_agent(None,'查询并解释第一个岗位',7)
    assert result=='基础分65，JD加30，最终95'
    assert calls==[
        ('find_jobs',{'min_score':80,'limit':5},7),
        ('get_job',{'job_id':1011},7)
    ]

def test_agent_can_compare_job_with_resume(monkeypatch):
    find_msg=NS(
        content='',tool_calls=[JobCall()],
        model_dump=lambda exclude_none:{'role':'assistant','tool_calls':['find']}
    )
    compare_msg=NS(
        content='',tool_calls=[CompareCall()],
        model_dump=lambda exclude_none:{'role':'assistant','tool_calls':['compare']}
    )
    replies=[
        NS(choices=[NS(message=find_msg)]),
        NS(choices=[NS(message=compare_msg)])
    ]
    calls=[]
    def fake_tool(name,args,user_id):
        calls.append((name,args,user_id))
        if name == 'compare_job_resume':
            return json.dumps({
                'found':True,
                'matched':[{
                    'name':'个人项目/作品',
                    'proofs':[{'id':'P1','text':'AI求职助手'}]
                }],
                'missing':['AI工具/低代码','库存/仓储经验']
            },ensure_ascii=False)
        return '{}'
    monkeypatch.setattr(agent,'ask_model',lambda client,msgs:replies.pop(0))
    monkeypatch.setattr(agent,'run_tool',fake_tool)
    result=agent.run_agent(None,'比较第一份岗位和我的简历',7)
    assert result == (
        '有简历证据：\n个人项目/作品（证据：P1）\n'
        '当前简历未发现：\nAI工具/低代码\n库存/仓储经验'
    )
    assert replies == []
    assert calls==[
        ('find_jobs',{'min_score':80,'limit':5},7),
        ('compare_job_resume',{'job_id':1011},7)
    ]


# 避免不必要的第二次模型请求，降低延迟和费用。
def test_agent_direct(monkeypatch):
    msg=NS(content='直接回答',tool_calls=None)
    reply=NS(choices=[NS(message=msg)])
    calls=[]
    def fake_ask(client,msgs):
        calls.append(msgs)
        return reply
    monkeypatch.setattr(agent,'ask_model',fake_ask)
    assert agent.run_agent(None,'你好',7)=='直接回答'
    assert len(calls)==1

def fake_client():
    return 'client'

def fake_agent(client,goal,user_id,history=None):
    return f'{client}:{goal}'

def test_agent_mock(monkeypatch):
    monkeypatch.setattr(agent.settings,'llm_mock_mode',True)
    assert agent.ask_agent('查Docker',7)=='模拟Agent回答:查Docker'

def test_agent_real(monkeypatch):
    monkeypatch.setattr(agent.settings,'llm_mock_mode',False)
    monkeypatch.setattr(agent.settings,'llm_model','test-model')
    monkeypatch.setattr(agent,'get_llm_client',fake_client)
    monkeypatch.setattr(agent,'run_agent',fake_agent)
    assert agent.ask_agent('查Docker',7)=='client:查Docker'

def test_agent_no_model(monkeypatch):
    monkeypatch.setattr(agent.settings,'llm_mock_mode',False)
    monkeypatch.setattr(agent.settings,'llm_model',None)
    with pytest.raises(RuntimeError,match='未配置 LLM_MODEL'):
        # match：【pytest提供的参数】检查异常消息是否包含指定文字。
        agent.ask_agent('查Docker',7)
