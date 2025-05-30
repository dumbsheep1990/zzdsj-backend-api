"""
记忆管理器 - 核心业务逻辑
提供智能体记忆的核心管理功能
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化记忆管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.memory_repository = MemoryRepository()
        
    # ============ 记忆管理方法 ============
    
    async def create_memory(
        self,
        agent_id: str,
        memory_type: str,
        content: str,
        importance: float = 0.5,
        metadata: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """创建新记忆
        
        Args:
            agent_id: 智能体ID
            memory_type: 记忆类型 (episodic/semantic/procedural)
            content: 记忆内容
            importance: 重要性分数 (0.0-1.0)
            metadata: 记忆元数据
            context: 记忆上下文
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not content or not content.strip():
                return {
                    "success": False,
                    "error": "记忆内容不能为空",
                    "error_code": "INVALID_CONTENT"
                }
            
            # 验证记忆类型
            valid_types = ["episodic", "semantic", "procedural", "emotional"]
            if memory_type not in valid_types:
                return {
                    "success": False,
                    "error": f"无效的记忆类型: {memory_type}",
                    "error_code": "INVALID_TYPE"
                }
            
            # 验证重要性分数
            if not (0.0 <= importance <= 1.0):
                return {
                    "success": False,
                    "error": "重要性分数必须在0.0-1.0之间",
                    "error_code": "INVALID_IMPORTANCE"
                }
            
            # 准备记忆数据
            memory_data = {
                "id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "memory_type": memory_type,
                "content": content.strip(),
                "importance": importance,
                "access_count": 0,
                "last_accessed": None,
                "metadata": metadata or {},
                "context": context or {},
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建记忆
            memory = await self.memory_repository.create(memory_data, self.db)
            
            logger.info(f"记忆创建成功: {memory.id} for agent {agent_id}")
            
            return {
                "success": True,
                "data": {
                    "id": memory.id,
                    "agent_id": memory.agent_id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "importance": memory.importance,
                    "created_at": memory.created_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建记忆失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆详情
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            memory = await self.memory_repository.get_by_id(memory_id, self.db)
            if not memory:
                return {
                    "success": False,
                    "error": "记忆不存在",
                    "error_code": "MEMORY_NOT_FOUND"
                }
            
            # 更新访问计数和时间
            await self._update_memory_access(memory_id)
            
            return {
                "success": True,
                "data": {
                    "id": memory.id,
                    "agent_id": memory.agent_id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "importance": memory.importance,
                    "access_count": memory.access_count,
                    "last_accessed": memory.last_accessed,
                    "metadata": memory.metadata,
                    "context": memory.context,
                    "is_active": memory.is_active,
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取记忆失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def search_memories(
        self,
        agent_id: str,
        query: str = None,
        memory_type: str = None,
        min_importance: float = None,
        limit: int = 10,
        context_filter: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """搜索记忆
        
        Args:
            agent_id: 智能体ID
            query: 搜索查询
            memory_type: 记忆类型过滤
            min_importance: 最小重要性过滤
            limit: 返回数量限制
            context_filter: 上下文过滤条件
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建搜索条件
            search_filters = {"agent_id": agent_id, "is_active": True}
            
            if memory_type:
                search_filters["memory_type"] = memory_type
            
            if min_importance is not None:
                search_filters["min_importance"] = min_importance
            
            # 执行搜索
            memories = await self.memory_repository.search(
                search_filters, query, limit, self.db
            )
            
            # 应用上下文过滤
            if context_filter:
                filtered_memories = []
                for memory in memories:
                    if self._match_context(memory.context, context_filter):
                        filtered_memories.append(memory)
                memories = filtered_memories
            
            # 更新访问记录（异步）
            for memory in memories:
                await self._update_memory_access(memory.id)
            
            # 转换为标准格式
            memory_list = []
            for memory in memories:
                memory_data = {
                    "id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "importance": memory.importance,
                    "relevance_score": getattr(memory, 'relevance_score', 0.0),
                    "created_at": memory.created_at,
                    "last_accessed": memory.last_accessed
                }
                memory_list.append(memory_data)
            
            return {
                "success": True,
                "data": {
                    "memories": memory_list,
                    "total": len(memory_list),
                    "query": query,
                    "filters": search_filters
                }
            }
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"搜索记忆失败: {str(e)}",
                "error_code": "SEARCH_FAILED"
            }
    
    async def get_recent_memories(
        self,
        agent_id: str,
        memory_type: str = None,
        hours: int = 24,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取最近的记忆
        
        Args:
            agent_id: 智能体ID
            memory_type: 记忆类型过滤
            hours: 时间范围（小时）
            limit: 返回数量限制
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 计算时间范围
            since_time = datetime.utcnow() - timedelta(hours=hours)
            
            # 构建过滤条件
            filters = {
                "agent_id": agent_id,
                "is_active": True,
                "since_time": since_time
            }
            
            if memory_type:
                filters["memory_type"] = memory_type
            
            # 获取最近记忆
            memories = await self.memory_repository.get_recent(filters, limit, self.db)
            
            # 转换为标准格式
            memory_list = []
            for memory in memories:
                memory_data = {
                    "id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "importance": memory.importance,
                    "created_at": memory.created_at
                }
                memory_list.append(memory_data)
            
            return {
                "success": True,
                "data": {
                    "memories": memory_list,
                    "total": len(memory_list),
                    "time_range_hours": hours
                }
            }
            
        except Exception as e:
            logger.error(f"获取最近记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取最近记忆失败: {str(e)}",
                "error_code": "GET_RECENT_FAILED"
            }
    
    async def get_important_memories(
        self,
        agent_id: str,
        memory_type: str = None,
        min_importance: float = 0.7,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取重要记忆
        
        Args:
            agent_id: 智能体ID
            memory_type: 记忆类型过滤
            min_importance: 最小重要性阈值
            limit: 返回数量限制
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {
                "agent_id": agent_id,
                "is_active": True,
                "min_importance": min_importance
            }
            
            if memory_type:
                filters["memory_type"] = memory_type
            
            # 获取重要记忆
            memories = await self.memory_repository.get_by_importance(filters, limit, self.db)
            
            # 转换为标准格式
            memory_list = []
            for memory in memories:
                memory_data = {
                    "id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "importance": memory.importance,
                    "access_count": memory.access_count,
                    "created_at": memory.created_at
                }
                memory_list.append(memory_data)
            
            return {
                "success": True,
                "data": {
                    "memories": memory_list,
                    "total": len(memory_list),
                    "min_importance": min_importance
                }
            }
            
        except Exception as e:
            logger.error(f"获取重要记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取重要记忆失败: {str(e)}",
                "error_code": "GET_IMPORTANT_FAILED"
            }
    
    async def update_memory_importance(
        self,
        memory_id: str,
        importance: float,
        reason: str = None
    ) -> Dict[str, Any]:
        """更新记忆重要性
        
        Args:
            memory_id: 记忆ID
            importance: 新的重要性分数
            reason: 更新原因
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证重要性分数
            if not (0.0 <= importance <= 1.0):
                return {
                    "success": False,
                    "error": "重要性分数必须在0.0-1.0之间",
                    "error_code": "INVALID_IMPORTANCE"
                }
            
            # 检查记忆是否存在
            memory = await self.memory_repository.get_by_id(memory_id, self.db)
            if not memory:
                return {
                    "success": False,
                    "error": "记忆不存在",
                    "error_code": "MEMORY_NOT_FOUND"
                }
            
            # 准备更新数据
            update_data = {
                "importance": importance,
                "updated_at": datetime.utcnow()
            }
            
            # 添加更新原因到元数据
            if reason:
                metadata = memory.metadata.copy()
                if "importance_updates" not in metadata:
                    metadata["importance_updates"] = []
                
                metadata["importance_updates"].append({
                    "old_importance": memory.importance,
                    "new_importance": importance,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                update_data["metadata"] = metadata
            
            # 更新记忆
            updated_memory = await self.memory_repository.update(memory_id, update_data, self.db)
            
            logger.info(f"记忆重要性更新成功: {memory_id} -> {importance}")
            
            return {
                "success": True,
                "data": {
                    "id": updated_memory.id,
                    "old_importance": memory.importance,
                    "new_importance": updated_memory.importance,
                    "updated_at": updated_memory.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新记忆重要性失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新记忆重要性失败: {str(e)}",
                "error_code": "UPDATE_IMPORTANCE_FAILED"
            }
    
    async def delete_memory(self, memory_id: str, soft_delete: bool = True) -> Dict[str, Any]:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            soft_delete: 是否软删除（设置为非活跃）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查记忆是否存在
            memory = await self.memory_repository.get_by_id(memory_id, self.db)
            if not memory:
                return {
                    "success": False,
                    "error": "记忆不存在",
                    "error_code": "MEMORY_NOT_FOUND"
                }
            
            if soft_delete:
                # 软删除：设置为非活跃
                update_data = {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
                await self.memory_repository.update(memory_id, update_data, self.db)
                logger.info(f"记忆软删除成功: {memory_id}")
            else:
                # 硬删除：从数据库中删除
                success = await self.memory_repository.delete(memory_id, self.db)
                if not success:
                    return {
                        "success": False,
                        "error": "删除记忆失败",
                        "error_code": "DELETE_FAILED"
                    }
                logger.info(f"记忆硬删除成功: {memory_id}")
            
            return {
                "success": True,
                "data": {
                    "deleted_memory_id": memory_id,
                    "soft_delete": soft_delete
                }
            }
            
        except Exception as e:
            logger.error(f"删除记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除记忆失败: {str(e)}",
                "error_code": "DELETE_FAILED"
            }
    
    async def cleanup_old_memories(
        self,
        agent_id: str,
        days_old: int = 30,
        keep_important: bool = True,
        importance_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """清理旧记忆
        
        Args:
            agent_id: 智能体ID
            days_old: 超过多少天的记忆被认为是旧的
            keep_important: 是否保留重要记忆
            importance_threshold: 重要性阈值
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 计算时间阈值
            cutoff_time = datetime.utcnow() - timedelta(days=days_old)
            
            # 获取需要清理的记忆
            filters = {
                "agent_id": agent_id,
                "is_active": True,
                "before_time": cutoff_time
            }
            
            if keep_important:
                filters["max_importance"] = importance_threshold
            
            old_memories = await self.memory_repository.get_old_memories(filters, self.db)
            
            # 执行清理
            cleaned_count = 0
            for memory in old_memories:
                # 软删除旧记忆
                update_data = {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
                
                # 添加清理信息到元数据
                metadata = memory.metadata.copy()
                metadata["cleanup_info"] = {
                    "cleaned_at": datetime.utcnow().isoformat(),
                    "reason": "old_memory_cleanup",
                    "days_old": (datetime.utcnow() - memory.created_at).days
                }
                update_data["metadata"] = metadata
                
                await self.memory_repository.update(memory.id, update_data, self.db)
                cleaned_count += 1
            
            logger.info(f"记忆清理完成: {cleaned_count} memories for agent {agent_id}")
            
            return {
                "success": True,
                "data": {
                    "cleaned_count": cleaned_count,
                    "days_old": days_old,
                    "keep_important": keep_important
                }
            }
            
        except Exception as e:
            logger.error(f"清理旧记忆失败: {str(e)}")
            return {
                "success": False,
                "error": f"清理旧记忆失败: {str(e)}",
                "error_code": "CLEANUP_FAILED"
            }
    
    # ============ 私有辅助方法 ============
    
    async def _update_memory_access(self, memory_id: str):
        """更新记忆访问记录"""
        try:
            update_data = {
                "access_count": "access_count + 1",  # SQL表达式
                "last_accessed": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await self.memory_repository.update(memory_id, update_data, self.db)
        except Exception as e:
            logger.warning(f"更新记忆访问记录失败: {str(e)}")
    
    def _match_context(self, memory_context: Dict[str, Any], filter_context: Dict[str, Any]) -> bool:
        """检查记忆上下文是否匹配过滤条件"""
        for key, value in filter_context.items():
            if key not in memory_context:
                return False
            
            memory_value = memory_context[key]
            
            # 支持不同类型的匹配
            if isinstance(value, str) and isinstance(memory_value, str):
                if value.lower() not in memory_value.lower():
                    return False
            elif isinstance(value, list):
                if memory_value not in value:
                    return False
            elif memory_value != value:
                return False
        
        return True 