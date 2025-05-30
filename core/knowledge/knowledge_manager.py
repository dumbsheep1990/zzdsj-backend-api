"""
知识库管理器 - 核心业务逻辑
提供知识库的创建、管理、配置等核心功能
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.knowledge import KnowledgeBaseRepository, DocumentRepository, DocumentChunkRepository

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化知识库管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.kb_repository = KnowledgeBaseRepository(db)
        self.doc_repository = DocumentRepository(db)
        self.chunk_repository = DocumentChunkRepository(db)
        
    # ============ 知识库管理方法 ============
    
    async def create_knowledge_base(
        self, 
        name: str, 
        description: str = "",
        embedding_model: str = "text-embedding-ada-002",
        settings: Dict[str, Any] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """创建知识库
        
        Args:
            name: 知识库名称
            description: 知识库描述
            embedding_model: 嵌入模型名称
            settings: 知识库配置
            user_id: 创建者ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "知识库名称不能为空",
                    "error_code": "INVALID_NAME"
                }
            
            # 检查名称是否已存在
            existing_kb = await self.kb_repository.get_by_name(name.strip())
            if existing_kb:
                return {
                    "success": False,
                    "error": "知识库名称已存在",
                    "error_code": "NAME_EXISTS"
                }
            
            # 准备知识库数据
            kb_data = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "description": description.strip() if description else "",
                "embedding_model": embedding_model,
                "settings": settings or {},
                "is_active": True,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建知识库
            kb = await self.kb_repository.create(kb_data)
            
            logger.info(f"知识库创建成功: {kb.id} - {kb.name}")
            
            return {
                "success": True,
                "data": {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "embedding_model": kb.embedding_model,
                    "settings": kb.settings,
                    "is_active": kb.is_active,
                    "created_at": kb.created_at,
                    "updated_at": kb.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建知识库失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_knowledge_base(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库详情
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            kb = await self.kb_repository.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 获取统计信息
            stats = await self._get_knowledge_base_stats(kb_id)
            
            return {
                "success": True,
                "data": {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "embedding_model": kb.embedding_model,
                    "settings": kb.settings,
                    "is_active": kb.is_active,
                    "created_at": kb.created_at,
                    "updated_at": kb.updated_at,
                    "stats": stats
                }
            }
            
        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取知识库失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def list_knowledge_bases(
        self, 
        user_id: str = None,
        is_active: bool = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取知识库列表
        
        Args:
            user_id: 用户ID（用于权限过滤）
            is_active: 是否活跃
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if is_active is not None:
                filters["is_active"] = is_active
            if user_id:
                filters["created_by"] = user_id
            
            # 获取知识库列表
            kbs = await self.kb_repository.list_with_filters(filters, skip, limit)
            total = await self.kb_repository.count_with_filters(filters)
            
            # 为每个知识库添加统计信息
            kb_list = []
            for kb in kbs:
                stats = await self._get_knowledge_base_stats(kb.id)
                kb_data = {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "embedding_model": kb.embedding_model,
                    "is_active": kb.is_active,
                    "created_at": kb.created_at,
                    "updated_at": kb.updated_at,
                    "stats": stats
                }
                kb_list.append(kb_data)
            
            return {
                "success": True,
                "data": {
                    "knowledge_bases": kb_list,
                    "total": total,
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取知识库列表失败: {str(e)}",
                "error_code": "LIST_FAILED"
            }
    
    async def update_knowledge_base(
        self, 
        kb_id: str, 
        name: str = None,
        description: str = None,
        embedding_model: str = None,
        settings: Dict[str, Any] = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """更新知识库
        
        Args:
            kb_id: 知识库ID
            name: 新名称
            description: 新描述
            embedding_model: 新嵌入模型
            settings: 新设置
            is_active: 新状态
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查知识库是否存在
            kb = await self.kb_repository.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 准备更新数据
            update_data = {"updated_at": datetime.utcnow()}
            
            if name is not None:
                name = name.strip()
                if not name:
                    return {
                        "success": False,
                        "error": "知识库名称不能为空",
                        "error_code": "INVALID_NAME"
                    }
                
                # 检查名称冲突（排除当前知识库）
                existing_kb = await self.kb_repository.get_by_name(name)
                if existing_kb and existing_kb.id != kb_id:
                    return {
                        "success": False,
                        "error": "知识库名称已存在",
                        "error_code": "NAME_EXISTS"
                    }
                
                update_data["name"] = name
            
            if description is not None:
                update_data["description"] = description.strip()
            
            if embedding_model is not None:
                update_data["embedding_model"] = embedding_model
            
            if settings is not None:
                update_data["settings"] = settings
            
            if is_active is not None:
                update_data["is_active"] = is_active
            
            # 更新知识库
            updated_kb = await self.kb_repository.update(kb_id, update_data)
            
            logger.info(f"知识库更新成功: {kb_id}")
            
            return {
                "success": True,
                "data": {
                    "id": updated_kb.id,
                    "name": updated_kb.name,
                    "description": updated_kb.description,
                    "embedding_model": updated_kb.embedding_model,
                    "settings": updated_kb.settings,
                    "is_active": updated_kb.is_active,
                    "created_at": updated_kb.created_at,
                    "updated_at": updated_kb.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新知识库失败: {str(e)}")
            return {
                "success": False,
                "error": f"更新知识库失败: {str(e)}",
                "error_code": "UPDATE_FAILED"
            }
    
    async def delete_knowledge_base(self, kb_id: str, force: bool = False) -> Dict[str, Any]:
        """删除知识库
        
        Args:
            kb_id: 知识库ID
            force: 是否强制删除（包括所有文档和向量）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查知识库是否存在
            kb = await self.kb_repository.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 检查是否有文档
            doc_count = await self.doc_repository.count_by_kb(kb_id)
            if doc_count > 0 and not force:
                return {
                    "success": False,
                    "error": f"知识库中还有 {doc_count} 个文档，请先删除文档或使用强制删除",
                    "error_code": "HAS_DOCUMENTS"
                }
            
            # 如果强制删除，先删除所有文档和分块
            if force and doc_count > 0:
                # 删除所有文档分块
                await self.chunk_repository.delete_by_kb(kb_id)
                # 删除所有文档
                await self.doc_repository.delete_by_kb(kb_id)
                logger.info(f"强制删除知识库 {kb_id} 的所有文档和分块")
            
            # 删除知识库
            success = await self.kb_repository.delete(kb_id)
            
            if success:
                logger.info(f"知识库删除成功: {kb_id}")
                return {
                    "success": True,
                    "data": {"deleted_kb_id": kb_id}
                }
            else:
                return {
                    "success": False,
                    "error": "删除知识库失败",
                    "error_code": "DELETE_FAILED"
                }
            
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            return {
                "success": False,
                "error": f"删除知识库失败: {str(e)}",
                "error_code": "DELETE_FAILED"
            }
    
    # ============ 辅助方法 ============
    
    async def _get_knowledge_base_stats(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库统计信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 文档数量
            doc_count = await self.doc_repository.count_by_kb(kb_id)
            
            # 分块数量
            chunk_count = await self.chunk_repository.count_by_kb(kb_id)
            
            # 最后更新时间
            last_doc = await self.doc_repository.get_latest_by_kb(kb_id)
            last_updated = last_doc.updated_at if last_doc else None
            
            return {
                "document_count": doc_count,
                "chunk_count": chunk_count,
                "last_document_updated": last_updated
            }
            
        except Exception as e:
            logger.error(f"获取知识库统计信息失败: {str(e)}")
            return {
                "document_count": 0,
                "chunk_count": 0,
                "last_document_updated": None
            }
    
    async def validate_knowledge_base_access(self, kb_id: str, user_id: str = None) -> bool:
        """验证用户对知识库的访问权限
        
        Args:
            kb_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            bool: 是否有访问权限
        """
        try:
            kb = await self.kb_repository.get_by_id(kb_id)
            if not kb:
                return False
            
            # 如果知识库不活跃，只有创建者可以访问
            if not kb.is_active:
                return user_id and kb.created_by == user_id
            
            # 活跃的知识库，所有用户都可以访问（可根据需要调整权限逻辑）
            return True
            
        except Exception as e:
            logger.error(f"验证知识库访问权限失败: {str(e)}")
            return False 