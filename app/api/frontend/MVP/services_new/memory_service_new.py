"""
记忆服务层
"""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.services.base import BaseService
from app.memory.manager import MemoryManager
from app.memory.interfaces import MemoryConfig, MemoryType
from app.schemas.memory import MemoryCreateRequest, MemoryQueryRequest


class MemoryService(BaseService):
    """记忆服务"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.memory_manager = MemoryManager()

    async def create(self, agent_id: str, config: Optional[MemoryConfig] = None) -> Dict[str, Any]:
        """创建代理记忆"""
        memory = await self.memory_manager.create_agent_memory(
            agent_id=agent_id,
            config=config,
            db=self.db
        )

        return self._format_memory_response(memory)

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取代理记忆"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            return None

        return self._format_memory_response(memory)

    async def query(
            self,
            agent_id: str,
            query: str,
            top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """查询记忆内容"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        memory_items = await memory.query(query, top_k)

        return [
            {
                "key": key,
                "content": value,
                "relevance_score": score
            }
            for key, value, score in memory_items
        ]

    async def add_item(
            self,
            agent_id: str,
            key: str,
            value: Any
    ) -> Dict[str, Any]:
        """添加记忆项"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        await memory.add(key, value)

        return self._format_memory_response(memory)

    async def delete_item(self, agent_id: str, key: str) -> bool:
        """删除记忆项"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        return await memory.delete(key)

    async def clear(self, agent_id: str) -> Dict[str, Any]:
        """清空记忆"""
        memory = await self.memory_manager.get_agent_memory(agent_id, self.db)

        if not memory:
            raise NotFoundError(f"未找到智能体 {agent_id} 的记忆")

        await memory.clear()

        return self._format_memory_response(memory)

    def _format_memory_response(self, memory) -> Dict[str, Any]:
        """格式化记忆响应"""
        return {
            "memory_id": memory.memory_id,
            "agent_id": memory.agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__ if memory.config else None,
            "status": "active"
        }