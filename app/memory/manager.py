"""
智能体记忆系统 - 记忆管理器

负责全局记忆生命周期管理。
"""

from .factory import MemoryFactory
from .interfaces import IMemory, MemoryConfig
from typing import Dict, Optional, List
import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class MemoryManager:
    """记忆管理器，负责全局记忆生命周期管理"""
    
    def __init__(self):
        self.factory = MemoryFactory()
        self.owner_memories = {}  # 所有者ID到记忆ID列表的映射
        self.agent_memories = {}  # 智能体ID到记忆ID的映射
        self._cleanup_task = None
        
    async def get_or_create_memory(self, 
                            owner_id: str, 
                            memory_config: Optional[MemoryConfig] = None) -> IMemory:
        """获取或创建记忆实例"""
        # 检查所有者是否已有记忆
        if owner_id in self.owner_memories:
            for memory_id in self.owner_memories[owner_id]:
                memory = await self.factory.get_memory(memory_id)
                if memory and not memory.is_expired():
                    return memory
        
        # 创建新记忆
        memory = await self.factory.create_memory(owner_id, memory_config)
        
        # 更新所有者记忆映射
        if owner_id not in self.owner_memories:
            self.owner_memories[owner_id] = []
        self.owner_memories[owner_id].append(memory.memory_id)
        
        return memory
    
    async def create_agent_memory(self, agent_id: str, 
                          config: Optional[MemoryConfig] = None,
                          content: Optional[Dict] = None,
                          db: Optional[Session] = None) -> IMemory:
        """创建智能体记忆并绑定"""
        # 创建记忆
        memory = await self.factory.create_memory(f"agent:{agent_id}", config)
        
        # 绑定智能体ID和记忆ID
        self.agent_memories[agent_id] = memory.memory_id
        
        # 添加初始内容
        if content:
            for key, value in content.items():
                await memory.add(key, value)
        
        # 保存绑定关系到数据库
        if db:
            await self._save_agent_memory_binding(agent_id, memory.memory_id, db)
        
        return memory
    
    async def get_agent_memory(self, agent_id: str, 
                      db: Optional[Session] = None) -> Optional[IMemory]:
        """获取智能体记忆"""
        # 先从内存查找
        if agent_id in self.agent_memories:
            memory_id = self.agent_memories[agent_id]
            memory = await self.factory.get_memory(memory_id)
            if memory and not memory.is_expired():
                return memory
        
        # 从数据库查找绑定关系
        if db:
            binding = await self._load_agent_memory_binding(agent_id, db)
            if binding:
                memory_id = binding.memory_id
                memory = await self.factory.get_memory(memory_id)
                if memory and not memory.is_expired():
                    # 更新内存缓存
                    self.agent_memories[agent_id] = memory_id
                    return memory
        
        # 没找到记忆，返回None
        return None
    
    async def _save_agent_memory_binding(self, agent_id: str, memory_id: str, db: Session):
        """保存智能体记忆绑定关系到数据库"""
        try:
            from app.models.memory import AgentMemory
            
            # 检查是否已存在
            existing = db.query(AgentMemory).filter(AgentMemory.agent_id == agent_id).first()
            
            if existing:
                # 更新
                existing.memory_id = memory_id
            else:
                # 创建
                binding = AgentMemory(
                    agent_id=agent_id,
                    memory_id=memory_id
                )
                db.add(binding)
                
            db.commit()
            logger.info(f"已保存智能体记忆绑定: agent_id={agent_id}, memory_id={memory_id}")
            
        except Exception as e:
            logger.error(f"保存智能体记忆绑定失败: {str(e)}")
    
    async def _load_agent_memory_binding(self, agent_id: str, db: Session):
        """从数据库加载智能体记忆绑定关系"""
        try:
            from app.models.memory import AgentMemory
            
            binding = db.query(AgentMemory).filter(AgentMemory.agent_id == agent_id).first()
            return binding
            
        except Exception as e:
            logger.error(f"加载智能体记忆绑定失败: {str(e)}")
            return None
    
    async def cleanup_expired_memories(self):
        """清理过期记忆"""
        for owner_id, memory_ids in self.owner_memories.items():
            active_memories = []
            for memory_id in memory_ids:
                memory = await self.factory.get_memory(memory_id)
                if memory and not memory.is_expired():
                    active_memories.append(memory_id)
            
            # 更新活跃记忆列表
            self.owner_memories[owner_id] = active_memories
            
        # 清理智能体记忆
        for agent_id in list(self.agent_memories.keys()):
            memory_id = self.agent_memories[agent_id]
            memory = await self.factory.get_memory(memory_id)
            if not memory or memory.is_expired():
                del self.agent_memories[agent_id]
    
    async def start_cleanup_task(self, interval_seconds: int = 3600):
        """启动定期清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_expired_memories()
                except Exception as e:
                    logger.error(f"记忆清理任务出错: {str(e)}")
                await asyncio.sleep(interval_seconds)
                
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"记忆清理任务已启动，间隔: {interval_seconds}秒")
    
    async def stop_cleanup_task(self):
        """停止定期清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("记忆清理任务已停止")


# 全局记忆管理器实例
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """获取全局记忆管理器实例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
