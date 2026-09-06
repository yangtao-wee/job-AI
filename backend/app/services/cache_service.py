import json
import hashlib
from redis import Redis
from redis.exceptions import RedisError

from ..config import settings

cache = Redis.from_url(settings.redis_url,decode_responses=True)
# from_url：【第三方库】，根据 settings.redis_url 创建客户端。
# decode_responses=True：让读取结果直接成为字符串，否则通常得到字节数据。

def cache_ready()->bool:
    try:
        return bool(cache.ping())
    except RedisError:
        return False

def make_key(prefix:str,text:str)->str:
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return f'{prefix}:{digest}'


def read_cache(key:str)->dict | None:
    # key：缓存数据的唯一名称。
    try:
        text = cache.get(key)
        return json.loads(text) if text else None
    except (RedisError,json.JSONDecodeError):
        return None

def write_cache(key:str,data:dict,ttl:int=3600)->bool:
    try:
        cache.set(key,json.dumps(data,ensure_ascii=False),ex=ttl)
        return True
    except RedisError:
        return False