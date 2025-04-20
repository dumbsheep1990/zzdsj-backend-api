import json
from typing import Any, Dict, List, Optional, Union
import redis
from app.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True
)

def get_redis_client():
    """Get Redis client instance"""
    return redis.Redis(connection_pool=redis_pool)

def set_cache(key: str, value: Any, expire: int = 3600):
    """Set cache value with expiration"""
    client = get_redis_client()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    
    client.set(key, value, ex=expire)

def get_cache(key: str) -> Optional[Any]:
    """Get cache value"""
    client = get_redis_client()
    value = client.get(key)
    
    if value is None:
        return None
    
    # Try to parse JSON
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def delete_cache(key: str):
    """Delete cache value"""
    client = get_redis_client()
    client.delete(key)

def increment_counter(key: str, amount: int = 1):
    """Increment a counter"""
    client = get_redis_client()
    return client.incrby(key, amount)

def get_counter(key: str) -> int:
    """Get a counter value"""
    client = get_redis_client()
    value = client.get(key)
    return int(value) if value else 0

def set_hash(key: str, mapping: Dict[str, Any]):
    """Set a Redis hash"""
    client = get_redis_client()
    client.hset(key, mapping=mapping)

def get_hash(key: str) -> Dict[str, str]:
    """Get a Redis hash as dictionary"""
    client = get_redis_client()
    return client.hgetall(key)

def publish_message(channel: str, message: Union[str, Dict, List]):
    """Publish a message to a Redis channel"""
    client = get_redis_client()
    if isinstance(message, (dict, list)):
        message = json.dumps(message)
    
    client.publish(channel, message)

def get_pubsub():
    """Get a Redis PubSub instance for subscribing to channels"""
    client = get_redis_client()
    return client.pubsub()
