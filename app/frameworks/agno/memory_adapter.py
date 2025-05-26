"""
智能体记忆系统 - AGNO框架适配器

提供AGNO框架与记忆系统的集成。
"""

from typing import Dict, Any, List, Optional
from app.memory.interfaces import IMemory, MemoryConfig
from app.memory.manager import get_memory_manager

class AGNOMemoryAdapter:
    """AGNO框架记忆适配器"""
    
    @staticmethod
    async def get_agent_memory(agent_id: str, memory_type: str = "short_term") -> Dict[str, Any]:
        """获取AGNO格式的智能体记忆"""
        # 获取系统记忆
        memory_manager = get_memory_manager()
        memory = await memory_manager.get_agent_memory(agent_id)
        
        if not memory:
            # 创建记忆
            from app.memory.interfaces import MemoryConfig, MemoryType
            memory_config = MemoryConfig(
                memory_type=MemoryType[memory_type.upper()],
                storage_backend="in_memory"
            )
            memory = await memory_manager.create_agent_memory(agent_id, memory_config)
        
        # 查询所有记忆
        memory_items = await memory.query("", top_k=100)  # 获取所有记忆
        
        # 转换为AGNO格式
        agno_memory = {
            "chat_history": [],
            "contexts": [],
            "metadata": {}
        }
        
        for _, item, _ in memory_items:
            if "type" in item:
                if item["type"] == "chat":
                    agno_memory["chat_history"].append(item)
                elif item["type"] == "context":
                    agno_memory["contexts"].append(item)
                elif item["type"] == "metadata":
                    agno_memory["metadata"].update(item.get("data", {}))
                    
        return agno_memory
    
    @staticmethod
    async def save_agent_memory(agent_id: str, agno_memory: Dict[str, Any]) -> bool:
        """保存AGNO记忆到系统记忆"""
        # 获取系统记忆
        memory_manager = get_memory_manager()
        memory = await memory_manager.get_agent_memory(agent_id)
        
        if not memory:
            # 创建记忆
            memory = await memory_manager.create_agent_memory(agent_id)
        
        # 清空现有记忆
        await memory.clear()
        
        # 保存聊天历史
        for i, msg in enumerate(agno_memory.get("chat_history", [])):
            msg["type"] = "chat"
            await memory.add(f"chat_{i}", msg)
            
        # 保存上下文
        for i, ctx in enumerate(agno_memory.get("contexts", [])):
            ctx["type"] = "context"
            await memory.add(f"context_{i}", ctx)
            
        # 保存元数据
        if "metadata" in agno_memory and agno_memory["metadata"]:
            await memory.add("metadata", {
                "type": "metadata",
                "data": agno_memory["metadata"]
            })
            
        return True
