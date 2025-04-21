import json
from typing import Any, Dict, List, Optional, Union
import redis
from app.config import settings

# 创建Redis连接池
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True
)

def get_redis_client():
    """获取Redis客户端实例"""
    return redis.Redis(connection_pool=redis_pool)

def set_cache(key: str, value: Any, expire: int = 3600):
    """设置缓存值并设置过期时间"""
    client = get_redis_client()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    
    client.set(key, value, ex=expire)

def get_cache(key: str) -> Optional[Any]:
    """获取缓存值"""
    client = get_redis_client()
    value = client.get(key)
    
    if value is None:
        return None
    
    # 尝试解析JSON
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def delete_cache(key: str):
    """删除缓存值"""
    client = get_redis_client()
    client.delete(key)

def increment_counter(key: str, amount: int = 1):
    """递增计数器"""
    client = get_redis_client()
    return client.incrby(key, amount)

def get_counter(key: str) -> int:
    """获取计数器的值"""
    client = get_redis_client()
    value = client.get(key)
    return int(value) if value else 0

def set_hash(key: str, mapping: Dict[str, Any]):
    """设置Redis哈希表"""
    client = get_redis_client()
    client.hset(key, mapping=mapping)

def get_hash(key: str) -> Dict[str, str]:
    """获取Redis哈希表为字典"""
    client = get_redis_client()
    return client.hgetall(key)

def publish_message(channel: str, message: Union[str, Dict, List]):
    """向Redis通道发布消息"""
    client = get_redis_client()
    if isinstance(message, (dict, list)):
        message = json.dumps(message)
    
    client.publish(channel, message)

def get_pubsub():
    """获取Redis PubSub实例用于订阅通道"""
    client = get_redis_client()
    return client.pubsub()
