"""
异步Redis客户端工具

提供与Redis异步交互的功能，使用aioredis库实现。
"""

import json
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as aioredis
from functools import lru_cache
from app.config import settings

# 异步Redis连接池，使用懒加载
_async_redis_pool = None


async def get_async_redis_pool():
    """获取异步Redis连接池，如果不存在则创建"""
    global _async_redis_pool
    if _async_redis_pool is None:
        _async_redis_pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True
        )
    return _async_redis_pool


@lru_cache(maxsize=1)
def get_redis_client():
    """获取异步Redis客户端实例"""
    return AsyncRedisClient()


class AsyncRedisClient:
    """异步Redis客户端封装类"""
    
    def __init__(self):
        """初始化异步Redis客户端"""
        self._client = None
    
    async def _get_client(self):
        """获取异步Redis客户端，懒加载模式"""
        if self._client is None:
            pool = await get_async_redis_pool()
            self._client = aioredis.Redis(connection_pool=pool)
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """异步获取Redis键值"""
        client = await self._get_client()
        value = await client.get(key)
        
        if value is None:
            return None
        
        # 尝试解析JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        异步设置Redis键值
        
        参数:
            key: Redis键
            value: 值(自动序列化字典和列表)
            ex: 过期时间(秒)
            
        返回:
            操作是否成功
        """
        client = await self._get_client()
        
        # 序列化复杂对象
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await client.set(key, value, ex=ex)
    
    async def delete(self, key: str) -> int:
        """
        异步删除Redis键
        
        参数:
            key: Redis键
            
        返回:
            删除的键数量
        """
        client = await self._get_client()
        return await client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        参数:
            key: Redis键
            
        返回:
            键是否存在
        """
        client = await self._get_client()
        return await client.exists(key) > 0
    
    async def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置哈希表字段
        
        参数:
            name: 哈希表名
            key: 字段名
            value: 字段值
            
        返回:
            新创建的字段数量
        """
        client = await self._get_client()
        
        # 序列化复杂对象
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await client.hset(name, key, value)
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """
        获取哈希表字段
        
        参数:
            name: 哈希表名
            key: 字段名
            
        返回:
            字段值
        """
        client = await self._get_client()
        value = await client.hget(name, key)
        
        if value is None:
            return None
        
        # 尝试解析JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取所有哈希表字段
        
        参数:
            name: 哈希表名
            
        返回:
            哈希表所有字段的字典
        """
        client = await self._get_client()
        result = await client.hgetall(name)
        
        # 尝试将每个值解析为JSON
        parsed_result = {}
        for key, value in result.items():
            try:
                parsed_result[key] = json.loads(value)
            except json.JSONDecodeError:
                parsed_result[key] = value
        
        return parsed_result
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        参数:
            key: Redis键
            seconds: 过期秒数
            
        返回:
            操作是否成功
        """
        client = await self._get_client()
        return await client.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        参数:
            key: Redis键
            
        返回:
            剩余秒数
        """
        client = await self._get_client()
        return await client.ttl(key)
    
    async def close(self):
        """关闭Redis连接"""
        if self._client is not None:
            await self._client.close()
            self._client = None
