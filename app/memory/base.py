"""
智能体记忆系统 - 基础记忆实现

实现IMemory接口的基础抽象类，提供通用功能。
"""

from .interfaces import IMemory, MemoryConfig, MemoryType
from typing import Any, Dict, List, Optional, Tuple, Union, Generic, TypeVar
from datetime import datetime, timedelta

T = TypeVar('T')

class BaseMemory(IMemory[T]):
    """基础记忆实现类"""
    
    def __init__(self, 
                memory_id: str,
                owner_id: str,
                config: MemoryConfig):
        self.memory_id = memory_id
        self.owner_id = owner_id
        self.config = config
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        
    async def add(self, key: str, value: T, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加记忆项(需子类实现)"""
        self.last_accessed = datetime.now()
        return False
    
    async def get(self, key: str) -> Optional[T]:
        """获取记忆项(需子类实现)"""
        self.last_accessed = datetime.now()
        return None
    
    async def update(self, key: str, value: T, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新记忆项(需子类实现)"""
        self.last_accessed = datetime.now()
        return False
    
    async def delete(self, key: str) -> bool:
        """删除记忆项(需子类实现)"""
        self.last_accessed = datetime.now()
        return False
    
    async def clear(self) -> bool:
        """清空所有记忆(需子类实现)"""
        self.last_accessed = datetime.now()
        return False
    
    async def query(self, query: str, top_k: int = 5) -> List[Tuple[str, T, float]]:
        """查询最相关记忆(需子类实现)"""
        self.last_accessed = datetime.now()
        return []
    
    def is_expired(self) -> bool:
        """检查记忆是否过期"""
        if self.config.ttl is None:
            return False
        
        expire_time = self.last_accessed + timedelta(seconds=self.config.ttl)
        return datetime.now() > expire_time
