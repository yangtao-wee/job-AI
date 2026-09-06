import pytest
import logging
from pydantic import ValidationError
from types import SimpleNamespace as NS

from app.schemas import RagAnswer
from app.services import llm_service as llm
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
    assert sent['temperature'] == 0

def test_unknown_fee_log(caplog):
    response = NS(
        usage=NS(prompt_tokens=10, completion_tokens=2, total_tokens=12)
    )
    with caplog.at_level(logging.INFO, logger=llm.__name__):
        llm.log_use(response, 'unknown-model')
    assert 'model=unknown-model' in caplog.text
    assert 'estimated_fee=unknown' in caplog.text


def test_call_structured_logs_usage(monkeypatch, caplog):
    response = NS(
        choices=[NS(message=NS(content='{"answer":"ok","sources":[],"enough":true}'))],
        usage=NS(prompt_tokens=100, completion_tokens=20, total_tokens=120)
    )
    model = 'deepseek-ai/DeepSeek-V3.2'
    monkeypatch.setattr(llm, 'call_json_model', lambda client, messages, model: response)
    with caplog.at_level(logging.INFO, logger=llm.__name__):
        llm.call_structured(None, '测试问题', RagAnswer, model)
    assert f'model={model}' in caplog.text
    assert 'total=120' in caplog.text
    assert 'estimated_fee=0.000520' in caplog.text

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


class BusyError(Exception):
    pass


class OtherError(Exception):
    pass


def test_call_structured_uses_backup(monkeypatch,caplog):
    models = []
    response = NS(choices=[NS(message=NS(
        content='{"answer":"备用回答","sources":[],"enough":true}'
    ))])

    def fake_call(client, messages, model):
        models.append(model)
        if model == 'main-model':
            raise BusyError()
        return response

    monkeypatch.setattr(llm, 'RateLimitError', BusyError)
    monkeypatch.setattr(llm, 'call_json_model', fake_call)
    monkeypatch.setattr(llm.settings, 'llm_backup_model', 'backup-model')
    with caplog.at_level(logging.INFO, logger=llm.__name__):
        result, raw = llm.call_structured(
            None, '测试问题', RagAnswer, 'main-model'
        )
    assert result.answer == '备用回答'
    assert raw is response
    assert models == ['main-model', 'backup-model']
    assert 'LLM调用Token用量 model=backup-model' in caplog.text
    assert 'LLM调用Token用量 model=main-model' not in caplog.text


def test_call_structured_does_not_hide_other_error(monkeypatch):
    models = []

    def fake_call(client, messages, model):
        models.append(model)
        raise OtherError()
    monkeypatch.setattr(llm, 'call_json_model', fake_call)
    monkeypatch.setattr(llm.settings, 'llm_backup_model', 'backup-model')
    with pytest.raises(OtherError):
        llm.call_structured(None, '测试问题', RagAnswer, 'main-model')
    assert models == ['main-model']


def test_call_structured_busy_without_backup(monkeypatch):
    models = []

    def fake_call(client, messages, model):
        models.append(model)
        raise BusyError()

    monkeypatch.setattr(llm, 'RateLimitError', BusyError)
    monkeypatch.setattr(llm, 'call_json_model', fake_call)
    monkeypatch.setattr(llm.settings, 'llm_backup_model', None)
    with pytest.raises(BusyError):
        llm.call_structured(None, '测试问题', RagAnswer, 'main-model')
    assert models == ['main-model']
