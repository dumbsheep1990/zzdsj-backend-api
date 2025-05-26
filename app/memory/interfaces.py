"""
智能体记忆系统 - 核心接口定义

定义记忆系统的基础接口和数据类型。
"""

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar, Tuple
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
import uuid

T = TypeVar('T')  # 记忆内容类型

class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"      # 短期记忆，基于对话轮次
    WORKING = "working"            # 工作记忆，当前任务相关
    EPISODIC = "episodic"          # 情景记忆，保存特定事件
    SEMANTIC = "semantic"          # 语义记忆，保存事实和概念
    PROCEDURAL = "procedural"      # 程序记忆，保存操作步骤
    NONE = "none"                  # 无记忆模式

class MemoryConfig:
    """记忆配置类"""
    def __init__(
        self,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        ttl: Optional[int] = None,        # 记忆生存时间(秒)
        max_tokens: Optional[int] = None, # 最大记忆token数
        max_items: Optional[int] = None,  # 最大记忆项数
        retrieval_strategy: str = "recency", # 检索策略：recency, relevance
        storage_backend: str = "in_memory", # 存储后端：in_memory, redis, postgres
        vector_backend: Optional[str] = None, # 向量后端：milvus, elasticsearch, pgvector
    ):
        self.memory_type = memory_type
        self.ttl = ttl
        self.max_tokens = max_tokens
        self.max_items = max_items
        self.retrieval_strategy = retrieval_strategy
        self.storage_backend = storage_backend
        self.vector_backend = vector_backend

class IMemory(ABC, Generic[T]):
    """记忆接口抽象类"""
    
    @abstractmethod
    async def add(self, key: str, value: T, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加记忆项"""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[T]:
        """获取记忆项"""
        pass
    
    @abstractmethod
    async def update(self, key: str, value: T, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新记忆项"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除记忆项"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """清空所有记忆"""
        pass
    
    @abstractmethod
    async def query(self, query: str, top_k: int = 5) -> List[Tuple[str, T, float]]:
        """查询最相关记忆"""
        pass

class IMemoryFactory(ABC):
    """记忆工厂接口"""
    
    @abstractmethod
    async def create_memory(self, 
                     owner_id: str, 
                     memory_config: Optional[MemoryConfig] = None) -> IMemory:
        """创建记忆实例"""
        pass
    
    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[IMemory]:
        """获取已存在的记忆实例"""
        pass
