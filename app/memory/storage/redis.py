"""
智能体记忆系统 - Redis存储后端

实现基于Redis的记忆存储。
"""

from typing import Dict, List, Any, Optional
import json
import hashlib
from datetime import datetime

class RedisMemoryStorage:
    """Redis记忆存储后端"""
    
    def __init__(self, memory_id: str, redis_client=None, ttl: Optional[int] = None):
        """初始化Redis存储
        
        Args:
            memory_id: 记忆ID
            redis_client: Redis客户端实例，如果为None则创建新客户端
            ttl: 记忆生存时间(秒)
        """
        from app.utils.redis_client import get_redis_client
        self.redis = redis_client or get_redis_client()
        self.memory_id = memory_id
        self.ttl = ttl
        self._prefix = f"memory:{memory_id}:"
        
    async def add(self, key: str, value: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加记忆项到Redis"""
        # 组合数据
        data = {
            "value": value,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        # 序列化
        serialized = json.dumps(data)
        
        # 存储到Redis
        redis_key = f"{self._prefix}item:{key}"
        await self.redis.set(redis_key, serialized, ex=self.ttl)
        
        # 添加到索引
        index_key = f"{self._prefix}index"
        await self.redis.sadd(index_key, key)
        
        return True
        
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """从Redis获取记忆项"""
        redis_key = f"{self._prefix}item:{key}"
        data = await self.redis.get(redis_key)
        
        if not data:
            return None
            
        try:
            parsed = json.loads(data)
            return parsed.get("value")
        except json.JSONDecodeError:
            return None
            
    async def delete(self, key: str) -> bool:
        """从Redis删除记忆项"""
        # 删除项
        redis_key = f"{self._prefix}item:{key}"
        await self.redis.delete(redis_key)
        
        # 从索引删除
        index_key = f"{self._prefix}index"
        await self.redis.srem(index_key, key)
        
        return True
        
    async def clear(self) -> bool:
        """清空所有记忆"""
        # 获取所有键
        index_key = f"{self._prefix}index"
        keys = await self.redis.smembers(index_key)
        
        # 删除所有项
        for key in keys:
            await self.delete(key)
            
        # 删除索引
        await self.redis.delete(index_key)
        
        return True
        
    async def get_all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有记忆项"""
        # 获取所有键
        index_key = f"{self._prefix}index"
        keys = await self.redis.smembers(index_key)
        
        # 获取所有项
        result = {}
        for key in keys:
            value = await self.get(key)
            if value:
                result[key] = value
                
        return result
