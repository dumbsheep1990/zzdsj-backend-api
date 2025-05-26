"""
智能体记忆系统 - 无记忆模式实现

实现不保存任何记忆的模式，适用于隐私场景。
"""

from .base import BaseMemory
from .interfaces import MemoryConfig
from typing import Any, Dict, List, Optional, Tuple

class NullMemory(BaseMemory[Dict[str, Any]]):
    """无记忆模式实现，不保存任何记忆"""
    
    async def add(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加记忆项(不执行任何操作)"""
        await super().add(key, value, metadata)
        return True
        
    async def get(self, key: str) -> Optional[Any]:
        """获取记忆项(始终返回None)"""
        await super().get(key)
        return None
        
    async def update(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新记忆项(不执行任何操作)"""
        await super().update(key, value, metadata)
        return True
        
    async def delete(self, key: str) -> bool:
        """删除记忆项(不执行任何操作)"""
        await super().delete(key)
        return True
        
    async def clear(self) -> bool:
        """清空所有记忆(不执行任何操作)"""
        await super().clear()
        return True
        
    async def query(self, query: str, top_k: int = 5) -> List[Tuple[str, Any, float]]:
        """查询最相关记忆(始终返回空列表)"""
        await super().query(query)
        return []
