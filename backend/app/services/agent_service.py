import logging
import json
from openai import RateLimitError
from .kb_service import load_parts
from .rag_service import pick_rows
from ..schemas import RagSrc
from ..config import settings
from .llm_service import get_llm_client

log=logging.getLogger(__name__)

# KB_TOOL → 工具说明书
KB_TOOL={
    'type':'function',
    'function':{
        'name':'find_kb',
        'description':'从求职知识库检索相关资料',
        'parameters':{
            'type':'object',
            'properties':{'q':{'type':'string'}},
            'required':['q'],
            'additionalProperties':False
        }
    }
}
# type、name、description、parameters、strict：【第三方SDK接口字段】名称不能随意改。
# properties、required、additionalProperties：【JSON Schema固定字段】不能随意改。
# Strict：严格模式，要求模型生成的工具参数符合我们声明的结构。
# additionalProperties=False 表示不接受未声明的额外参数。

# find_kb 是真正执行任务的工具
def find_kb(q:str)->list[RagSrc]:
    rows=pick_rows(q,load_parts())
    # pick_rows：【自己命名】已有的检索和阈值过滤函数。
    # load_parts：【自己命名】已有的知识库读取函数。
    # RagSrc：【自己命名】已有的来源结构。
    return [RagSrc(text=part,score=score) for score,part in rows]

# run_tool 是分发器。
def run_tool(name:str,args:dict)->str:
    if name != 'find_kb':
        raise ValueError('不支持的工具')
    rows=find_kb(args['q'])
    # rows 列表 + Pydantic对象
    data=[row.model_dump() for row in rows]
#    data # 列表 + Python字典
    # model_dump：【第三方库Pydantic提供】把模型对象转换成Python字典。
    return json.dumps(data,ensure_ascii=False)
# json.dumps：【语言标准库方法】把Python数据转换成JSON字符串。
# ensure_ascii=False：【标准库固定参数】让中文保持中文，而不是变成Unicode转义。

def run_call(call)->dict:
    name=call.function.name
    log.info(
        'Agent执行工具 name=%s call_id=%s',name,call.id)
    args=json.loads(call.function.arguments)
    # function.arguments：【第三方SDK响应字段】JSON字符串形式的工具参数。
    output=run_tool(name,args)
    return{'role':'tool','tool_call_id':call.id,"content":output}
# role、tool_call_id、content：【第三方接口固定字段】组成工具结果消息。

def call_model(client,messages,model):
    return client.chat.completions.create(
        model=model,messages=messages,
        tools=[KB_TOOL],tool_choice='auto'
    )

def ask_model(client,messages):
    try:
        return call_model(client,messages,settings.llm_model)
    except RateLimitError as error:
        if str(error.code)!='1305' or not settings.llm_backup_model:
            raise
        log.warning('主模型繁忙，切换备用模型 model=%s',settings.llm_backup_model)
        return call_model(client,messages,settings.llm_backup_model)

def run_agent(client,goal:str)->str:
    msgs=[
        {'role':'system','content':'你是AI求职助手，需要资料时调用find_kb。'},
        {'role':'user','content':goal}
    ]
    first=ask_model(client,msgs)
    msg=first.choices[0].message
    calls=msg.tool_calls or []
    log.info('Agent首轮完成 tool_calls=%d',len(calls))
    if not calls:
        return msg.content or ''
    msgs.append(msg.model_dump(exclude_none=True))
    msgs.extend(run_call(call) for call in calls)
    second=ask_model(client,msgs)
    return second.choices[0].message.content or ''

def ask_agent(goal:str)->str:
    if settings.llm_mock_mode:
        return f'模拟Agent回答:{goal}'
    if not settings.llm_model:
        raise RuntimeError('未配置 LLM_MODEL')
    return run_agent(get_llm_client(),goal)
# get_llm_client【自己命名】创建配置好的真实客户端。
