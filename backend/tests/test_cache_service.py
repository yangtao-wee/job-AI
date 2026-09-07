from unittest.mock import MagicMock
from redis.exceptions import RedisError
from app.services import cache_service as cache


class BrokenCache:
    def get(self, key):
        raise RedisError('redis down')

    def set(self, *args, **kwargs):
        raise RedisError('redis down')
    
    def lock(self, *args, **kwargs):
        raise RedisError('redis down')


def test_cache_failure_falls_back(monkeypatch):
    monkeypatch.setattr(cache, 'cache', BrokenCache())
    assert cache.read_cache('test:key') is None
    assert cache.write_cache('test:key', {}) is False

def test_lock_acquire_and_release(monkeypatch):
    fake_cache = MagicMock()
    fake_lock = MagicMock()
    fake_lock.acquire.return_value = True
    fake_cache.lock.return_value = fake_lock
    monkeypatch.setattr(cache, 'cache', fake_cache)
    lock = cache.take_lock('lead:1', 180)
    assert lock is fake_lock
    cache.free_lock(lock)
    fake_cache.lock.assert_called_once_with('lead:1', timeout=180)
    fake_lock.acquire.assert_called_once_with(blocking=False)
    fake_lock.release.assert_called_once_with()

def test_lock_failure_is_logged(monkeypatch,caplog):
    monkeypatch.setattr(cache,'cache',BrokenCache())
    assert cache.take_lock('lead:1') is None
    assert 'redis_lock_failed' in caplog.text