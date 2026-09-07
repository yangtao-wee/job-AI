from unittest.mock import MagicMock
import pytest
from redis.exceptions import RedisError
from fastapi import HTTPException

from app import dependencies as deps
from app.services import rate_service as rate


def fake_cache(count: int, ttl: int = 25):
    cache = MagicMock()
    pipe = cache.pipeline.return_value
    pipe.execute.return_value = (count, True)
    cache.ttl.return_value = ttl
    return cache, pipe


def test_rate_allowed(monkeypatch):
    cache, pipe = fake_cache(3)
    monkeypatch.setattr(rate, 'cache', cache)

    retry = rate.use_limit('rate:test:7', 3, 60)

    assert retry == 0
    cache.pipeline.assert_called_once_with(transaction=True)
    pipe.incr.assert_called_once_with('rate:test:7')
    pipe.expire.assert_called_once_with(
        'rate:test:7', 60, nx=True
    )


def test_rate_blocked_returns_ttl(monkeypatch):
    cache, _ = fake_cache(4, ttl=25)
    monkeypatch.setattr(rate, 'cache', cache)

    retry = rate.use_limit('rate:test:7', 3, 60)

    assert retry == 25
    cache.ttl.assert_called_once_with('rate:test:7')


def test_rate_redis_failure(monkeypatch, caplog):
    broken = MagicMock()
    broken.pipeline.side_effect = RedisError('redis down')
    monkeypatch.setattr(rate, 'cache', broken)

    with pytest.raises(RuntimeError, match='限流服务暂时不可用'):
        rate.use_limit('rate:test:7', 3, 60)

    assert 'rate_limit_failed' in caplog.text


def test_check_limit_returns_429(monkeypatch):
    monkeypatch.setattr(
        deps, 'use_limit', lambda *args, **kwargs: 25
    )

    with pytest.raises(HTTPException) as caught:
        deps.check_limit('agent', 7, 3, 60)

    assert caught.value.status_code == 429
    assert caught.value.headers['Retry-After'] == '25'


def test_check_limit_returns_503(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('限流服务暂时不可用')

    monkeypatch.setattr(deps, 'use_limit', fail)

    with pytest.raises(HTTPException) as caught:
        deps.check_limit('agent', 7, 3, 60)

    assert caught.value.status_code == 503