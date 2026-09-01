import pytest
from pydantic import ValidationError
from types import SimpleNamespace as NS

from app.schemas import RagAnswer
from app.services.llm_service import build_json_messages, call_structured


# Schema有没有放进模型消息
def test_build_json_messages():
    messages = build_json_messages('测试问题', RagAnswer)
    assert [item['role'] for item in messages] == ['system', 'user']
    assert '"answer"' in messages[0]['content']


# 正常JSON能不能变成Pydantic对象
def test_call_structured():
    response = NS(choices=[NS(message=NS(
        content='{"answer":"测试回答","sources":[],"enough":true}'
    ))])
    sent = {}

    def fake_create(**kwargs):
        sent.update(kwargs)
        return response

    client = NS(chat=NS(completions=NS(create=fake_create)))
    result, raw = call_structured(
        client, '测试问题', RagAnswer, 'test-model'
    )
    assert result.answer == '测试回答'
    assert raw is response
    assert sent['model'] == 'test-model'
    assert sent['response_format'] == {'type': 'json_object'}


# 验证空模型结果会被统一适配层明确拒绝。
def test_call_structured_empty():
    response = NS(choices=[NS(message=NS(content=''))])
    client = NS(chat=NS(completions=NS(
        create=lambda **kwargs: response
    )))
    with pytest.raises(RuntimeError, match='没有返回内容'):
        call_structured(client, '测试问题', RagAnswer, 'test-model')


# JSON缺少必填字段时能不能拒绝
def test_call_structured_invalid():
    response = NS(choices=[NS(message=NS(
        content='{"answer":"测试回答","sources":[]}'
    ))])
    client = NS(chat=NS(completions=NS(
        create=lambda **kwargs: response
    )))
    with pytest.raises(ValidationError, match='enough'):
        call_structured(client, '测试问题', RagAnswer, 'test-model')
