from redis.exceptions import RedisError
from app.services import cache_service as cache


class BrokenCache:
    def get(self, key):
        raise RedisError('redis down')

    def set(self, *args, **kwargs):
        raise RedisError('redis down')


def test_cache_failure_falls_back(monkeypatch):
    monkeypatch.setattr(cache, 'cache', BrokenCache())
    assert cache.read_cache('test:key') is None
    assert cache.write_cache('test:key', {}) is False