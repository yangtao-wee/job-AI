import logging
from redis.exceptions import RedisError
from .cache_service import cache

log = logging.getLogger(__name__)

def use_limit(key: str, limit: int, window: int) -> int:
    try:
        pipe = cache.pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        count, _ = pipe.execute()
        return 0 if count <= limit else max(cache.ttl(key), 1)
    except RedisError as error:
        log.exception('rate_limit_failed key=%s', key)
        raise RuntimeError('限流服务暂时不可用') from error