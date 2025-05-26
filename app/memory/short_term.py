"""
智能体记忆系统 - 短期记忆实现

实现基于最近N轮对话的短期记忆。
"""

from .base import BaseMemory
from .interfaces import MemoryConfig, MemoryType
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime

class ShortTermMemory(BaseMemory[Dict[str, Any]]):
    """短期记忆实现，基于最近N轮对话"""
    
    def __init__(self, memory_id: str, owner_id: str, config: MemoryConfig):
        super().__init__(memory_id, owner_id, config)
        self.max_items = config.max_items or 10
        self.items = deque(maxlen=self.max_items)
        self.key_index = {}  # 键到索引的映射
        
    async def add(self, key: str, value: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加记忆项"""
        await super().add(key, value, metadata)
        
        # 创建记忆项
        memory_item = {
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        # 如果键已存在，先删除旧项
        if key in self.key_index:
            old_index = self.key_index[key]
            self.items[old_index] = None  # 标记为删除
        
        # 添加新项
        self.items.append(memory_item)
        self.key_index[key] = len(self.items) - 1
        
        return True
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取记忆项"""
        await super().get(key)
        
        if key not in self.key_index:
            return None
        
        index = self.key_index[key]
        if index >= len(self.items):
            return None
            
        item = self.items[index]
        
        if item is None:  # 已删除
            return None
            
        return item["value"]
    
    async def update(self, key: str, value: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新记忆项"""
        return await self.add(key, value, metadata)
    
    async def delete(self, key: str) -> bool:
        """删除记忆项"""
        await super().delete(key)
        
        if key not in self.key_index:
            return False
        
        index = self.key_index[key]
        if index < len(self.items):
            self.items[index] = None  # 标记为删除
        del self.key_index[key]
        
        return True
    
    async def clear(self) -> bool:
        """清空所有记忆"""
        await super().clear()
        
        self.items.clear()
        self.key_index.clear()
        
        return True
    
    async def query(self, query: str, top_k: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        """查询最相关记忆，短期记忆简单返回最近的几项"""
        await super().query(query)
        
        # 收集非空项
        valid_items = [item for item in self.items if item is not None]
        
        # 按最近顺序返回
        results = []
        for item in reversed(valid_items[-top_k:]):
            results.append((item["key"], item["value"], 1.0))  # 简单实现，所有项权重相同
            
        return results
