import json

from openai import OpenAI
# 所以这里的 OpenAI 更像一个“会说兼容接口格式的通用请求工具”。
from pydantic import BaseModel

from ..config import settings


# 一个配置好的大模型客户端
def get_llm_client() -> OpenAI:
    if not settings.llm_api_key:
        raise RuntimeError('未配置 LLM_API_KEY')
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries
    )


# 理解怎样要求大模型返回固定结构的数据。
def build_json_messages(
    prompt: str,
    schema: type[BaseModel]
) -> list[dict]:
    schema_text = json.dumps(
        schema.model_json_schema(),
        ensure_ascii=False
    )
    # model_json_schema：【第三方库提供】把数据验证模型转换成数据结构说明。
    # ensure_ascii：【语言标准库固定参数】是否把中文强制转换成转义字符。
    return [
        {
            'role': 'system',
            'content': (
                '只返回JSON，不要输出Markdown代码块。'
                f'结果必须符合以下JSON Schema：{schema_text}'
            )
        },
        # 它告诉模型：不要随意回答，必须按照指定的数据结构返回结果。
        {'role': 'user', 'content': prompt}
        # user：【第三方接口固定值】用户消息。
        # prompt：【自己命名】实际任务提示词。
    ]


# 统一发送结构化模型请求并用Pydantic验证结果。
def call_structured(client, prompt, schema, model):
    response = client.chat.completions.create(
        # 使用大模型客户端创建一次对话请求，并把完整响应保存到 response。
        model=model,
        messages=build_json_messages(prompt, schema),
        response_format={'type': 'json_object'}
        # response_format：【第三方接口固定参数】响应格式。
        # 要求模型返回一个合法的数据对象，而不是普通文字或 Markdown 代码块。
    )
    content = response.choices[0].message.content
    # choices：【第三方接口响应字段】候选回答列表。
    if not content:
        raise RuntimeError('大模型没有返回内容')
    return schema.model_validate_json(content), response


# response_format={'type':'json_object'} = 保证外形是 JSON
# model_validate_json() = 检查 JSON 内部结构是不是你规定的格式
# 第一层：保证外形response_format={'type': 'json_object'}
# 第二层：保证内部结构schema.model_validate_json(content)
