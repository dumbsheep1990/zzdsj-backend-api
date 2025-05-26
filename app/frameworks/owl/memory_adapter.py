"""
智能体记忆系统 - OWL框架适配器

提供OWL框架与记忆系统的集成。
"""

from typing import Dict, Any, Optional
from app.memory.interfaces import IMemory, MemoryConfig, MemoryType
from app.memory.manager import get_memory_manager

class OwlMemoryAdapter:
    """OWL框架记忆适配器"""
    
    @staticmethod
    async def get_agent_memory(agent_id: str, config: Optional[Dict[str, Any]] = None) -> IMemory:
        """获取智能体记忆"""
        # 转换配置
        memory_config = None
        if config:
            from app.memory.interfaces import MemoryConfig, MemoryType
            memory_config = MemoryConfig(
                memory_type=MemoryType[config.get("memory_type", "SHORT_TERM")],
                ttl=config.get("ttl"),
                max_items=config.get("max_items"),
                max_tokens=config.get("max_tokens"),
                retrieval_strategy=config.get("retrieval_strategy", "recency"),
                storage_backend=config.get("storage_backend", "in_memory"),
                vector_backend=config.get("vector_backend")
            )
            
        # 获取或创建记忆
        memory_manager = get_memory_manager()
        memory = await memory_manager.get_agent_memory(agent_id)
        
        if not memory:
            # 创建记忆
            memory = await memory_manager.create_agent_memory(agent_id, memory_config)
            
        return memory
    
    @staticmethod
    async def get_conversation_memory(conversation_id: str) -> IMemory:
        """获取会话记忆"""
        memory_manager = get_memory_manager()
        return await memory_manager.get_or_create_memory(f"conversation:{conversation_id}")
    
    @staticmethod
    async def clear_agent_memory(agent_id: str) -> bool:
        """清空智能体记忆"""
        memory_manager = get_memory_manager()
        memory = await memory_manager.get_agent_memory(agent_id)
        if memory:
            return await memory.clear()
        return False
