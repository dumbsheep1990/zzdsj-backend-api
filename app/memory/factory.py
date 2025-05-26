"""
智能体记忆系统 - 记忆工厂

负责创建不同类型的记忆实例。
"""

from .interfaces import IMemoryFactory, IMemory, MemoryConfig, MemoryType
from .short_term import ShortTermMemory
from .semantic import SemanticMemory
from .null import NullMemory
from typing import Dict, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class MemoryFactory(IMemoryFactory):
    """记忆工厂实现"""
    
    def __init__(self):
        self.memories = {}  # 记忆ID到记忆实例的映射
        
    async def create_memory(self, 
                     owner_id: str, 
                     memory_config: Optional[MemoryConfig] = None) -> IMemory:
        """创建记忆实例"""
        # 使用默认配置
        if memory_config is None:
            from app.config import settings
            memory_config = MemoryConfig(
                memory_type=getattr(MemoryType, settings.MEMORY_TYPE, MemoryType.SHORT_TERM),
                ttl=getattr(settings, "MEMORY_TTL", 3600),
                max_items=getattr(settings, "MEMORY_MAX_ITEMS", 50)
            )
            
        # 生成记忆ID
        memory_id = str(uuid.uuid4())
        
        # 根据记忆类型创建不同实现
        if memory_config.memory_type == MemoryType.NONE:
            # 无记忆模式，不实际创建记忆
            memory = NullMemory(memory_id, owner_id, memory_config)
        elif memory_config.memory_type == MemoryType.SHORT_TERM:
            memory = ShortTermMemory(memory_id, owner_id, memory_config)
        elif memory_config.memory_type == MemoryType.SEMANTIC:
            memory = SemanticMemory(memory_id, owner_id, memory_config)
        else:
            # 默认使用短期记忆
            memory = ShortTermMemory(memory_id, owner_id, memory_config)
            
        # 存储记忆实例
        self.memories[memory_id] = memory
        
        logger.info(f"创建记忆: ID={memory_id}, 所有者={owner_id}, 类型={memory_config.memory_type}")
        
        return memory
    
    async def get_memory(self, memory_id: str) -> Optional[IMemory]:
        """获取已存在的记忆实例"""
        return self.memories.get(memory_id)
