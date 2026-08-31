import json
from .kb_service import load_parts
from .rag_service import pick_rows
from ..schemas import RagSrc
from ..config import settings
from .ai_resume_service import get_llm_client

# KB_TOOL → 工具说明书
KB_TOOL={
    'type':'function',
    'name':'find_kb',
    'description':'从求职知识库检索相关资料',
    'parameters':{
        'type':'object',
        'properties':{'q':{'type':'string'}},
        'required':['q'],
        'additionalProperties':False
    },
    'strict':True
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
    args=json.loads(call.arguments)
    # call.arguments通常返回str
# call.arguments、call.name、call.call_id：【第三方SDK响应字段】不能随意改。
    output=run_tool(call.name,args)
    # call.name模型想调用哪个工具。
    return{'type':'function_call_output','call_id':call.call_id,"output":output}
# function_call_output：【第三方SDK固定值】表示这是工具执行结果。

def ask_model(client,goal:str):
    return client.responses.create(
    # client.responses.create：【第三方SDK提供】发送Responses API请求。
        model=settings.llm_model,
        instructions='你是AI求职助手，需要资料时调用find_kb。',
        input=goal,
        tools=[KB_TOOL],
        tool_choice='auto'
# 【第三方SDK固定参数】
# model       → 使用哪个模型
# instructions → Agent角色和工具使用规则
# input       → 用户目标
# tools       → 模型可以选择的工具
# tool_choice → 是否由模型自己选择
    )

def run_agent(client,goal:str)->str:
    first=ask_model(client,goal)
    calls=[item for item in first.output if item.type=='function_call']
# 第1项：普通输出
# 第2项：工具调用function_call
# 第3项：其他输出
    if not calls:
        return first.output_text
    outputs=[run_call(call) for call in calls]
    second=client.responses.create(
        model=settings.llm_model,
        instructions='根据工具结果回答用户，不要编造资料',
        previous_response_id=first.id,
        input=outputs,
        tools=[KB_TOOL]
    )
    return second.output_text

def ask_agent(goal:str)->str:
    if settings.llm_mock_mode:
        return f'模拟Agent回答:{goal}'
    if not settings.llm_model:
        raise RuntimeError('未配置 LLM_MODEL')
    return run_agent(get_llm_client(),goal)
# get_llm_client【自己命名】创建配置好的真实客户端。
