"""
统一知识库服务
整合原有的两个KnowledgeService类，提供统一的知识库管理接口
遵循分层架构：API层 -> 服务层 -> 核心业务逻辑层 -> 数据访问层 -> 数据库
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status, UploadFile
import os
import json
import uuid
import logging
from datetime import datetime

# 导入数据模型和schema
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    DocumentCreate,
    DocumentUpdate,
    KnowledgeBaseStats
)

# 导入Repository层
from app.repositories.knowledge import KnowledgeBaseRepository, DocumentRepository, DocumentChunkRepository

# 导入核心业务逻辑层
from core.knowledge import (
    KnowledgeBaseManager,
    DocumentProcessor,
    ChunkingManager,
    VectorManager,
    RetrievalManager
)

# 导入工具和框架
from app.utils.object_storage import upload_file, get_file_url
from app.utils.vector_store import get_vector_store
from app.frameworks.agno import KnowledgeBaseProcessor

# 导入统一的知识库管理工具
from app.tools.base.knowledge_management import (
    get_knowledge_manager,
    KnowledgeBaseConfig,
    DocumentProcessingConfig
)

# 导入统一的切分工具
from app.tools.base.document_chunking import (
    get_chunking_tool,
    ChunkingConfig
)

from app.config import settings
from app.utils.service_decorators import register_service

logger = logging.getLogger(__name__)

@register_service(service_type="knowledge", priority="high", description="统一知识库管理服务")
class UnifiedKnowledgeService:
    """
    统一知识库服务类
    整合业务逻辑和数据访问，提供完整的知识库管理功能
    """
    
    def __init__(self, db: Session):
        """
        初始化统一知识库服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        
        # Repository层（数据访问）
        self.kb_repo = KnowledgeBaseRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        
        # 核心业务逻辑层
        self.kb_manager = KnowledgeBaseManager(db)
        self.doc_processor = DocumentProcessor(db)
        self.chunking_manager = ChunkingManager(db)
        self.vector_manager = VectorManager(db)
        self.retrieval_manager = RetrievalManager(db)
        
        # 统一管理工具
        self.unified_manager = get_knowledge_manager(db)
        self.chunking_tool = get_chunking_tool()
        
        logger.info("统一知识库服务初始化完成")
    
    # ========== 知识库管理方法 ==========
    
    async def get_knowledge_bases(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取知识库列表，支持过滤和搜索
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            is_active: 可选的活跃状态过滤
            search: 可选的搜索关键词
            user_id: 用户ID（用于权限控制）
            
        Returns:
            List[Dict[str, Any]]: 知识库列表及其统计信息
        """
        try:
            # 使用核心业务逻辑层获取知识库列表
            result = await self.kb_manager.list_knowledge_bases(
                user_id=user_id,
                is_active=is_active,
                skip=skip,
                limit=limit
            )
            
            if not result["success"]:
                logger.error(f"获取知识库列表失败: {result['error']}")
                return []
            
            # 应用搜索过滤
            knowledge_bases = result["data"]["knowledge_bases"]
            if search:
                search_lower = search.lower()
                knowledge_bases = [
                    kb for kb in knowledge_bases
                    if search_lower in kb["name"].lower() or 
                       search_lower in kb.get("description", "").lower()
                ]
            
            return knowledge_bases
            
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return []
    
    async def get_knowledge_base(self, kb_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取单个知识库详情
        
        Args:
            kb_id: 知识库ID
            user_id: 用户ID（用于权限控制）
            
        Returns:
            Optional[Dict[str, Any]]: 知识库详情
        """
        try:
            # 验证访问权限
            if user_id:
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    logger.warning(f"用户 {user_id} 无权访问知识库 {kb_id}")
                    return None
            
            # 使用核心业务逻辑层获取知识库
            result = await self.kb_manager.get_knowledge_base(kb_id)
            
            if not result["success"]:
                logger.error(f"获取知识库失败: {result['error']}")
                return None
            
            return result["data"]
            
        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return None
    
    async def create_knowledge_base(
        self, 
        kb_data: Union[KnowledgeBaseCreate, Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建新知识库
        
        Args:
            kb_data: 知识库创建数据
            user_id: 创建者ID
            
        Returns:
            Optional[Dict[str, Any]]: 创建的知识库信息
        """
        try:
            # 转换输入数据
            if isinstance(kb_data, KnowledgeBaseCreate):
                data = {
                    "name": kb_data.name,
                    "description": kb_data.description or "",
                    "embedding_model": getattr(kb_data, 'embedding_model', 'text-embedding-ada-002'),
                    "settings": getattr(kb_data, 'settings', {})
                }
            else:
                data = kb_data
            
            # 使用核心业务逻辑层创建知识库
            result = await self.kb_manager.create_knowledge_base(
                name=data["name"],
                description=data.get("description", ""),
                embedding_model=data.get("embedding_model", "text-embedding-ada-002"),
                settings=data.get("settings", {}),
                user_id=user_id
            )
            
            if not result["success"]:
                logger.error(f"创建知识库失败: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            logger.info(f"知识库创建成功: {result['data']['id']}")
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建知识库失败: {str(e)}"
            )
    
    async def update_knowledge_base(
        self, 
        kb_id: str, 
        kb_data: Union[KnowledgeBaseUpdate, Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新知识库
        
        Args:
            kb_id: 知识库ID
            kb_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的知识库信息
        """
        try:
            # 验证访问权限
            if user_id:
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权访问该知识库"
                    )
            
            # 转换输入数据
            if isinstance(kb_data, KnowledgeBaseUpdate):
                data = {}
                if kb_data.name is not None:
                    data["name"] = kb_data.name
                if kb_data.description is not None:
                    data["description"] = kb_data.description
                if hasattr(kb_data, 'embedding_model') and kb_data.embedding_model is not None:
                    data["embedding_model"] = kb_data.embedding_model
                if hasattr(kb_data, 'settings') and kb_data.settings is not None:
                    data["settings"] = kb_data.settings
                if hasattr(kb_data, 'is_active') and kb_data.is_active is not None:
                    data["is_active"] = kb_data.is_active
            else:
                data = kb_data
            
            # 使用核心业务逻辑层更新知识库
            result = await self.kb_manager.update_knowledge_base(kb_id, **data)
            
            if not result["success"]:
                logger.error(f"更新知识库失败: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            logger.info(f"知识库更新成功: {kb_id}")
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新知识库失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新知识库失败: {str(e)}"
            )
    
    async def delete_knowledge_base(
        self, 
        kb_id: str, 
        force: bool = False,
        user_id: Optional[str] = None
    ) -> bool:
        """
        删除知识库
        
        Args:
            kb_id: 知识库ID
            force: 是否强制删除
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 验证访问权限
            if user_id:
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权访问该知识库"
                    )
            
            # 使用核心业务逻辑层删除知识库
            result = await self.kb_manager.delete_knowledge_base(kb_id, force)
            
            if not result["success"]:
                logger.error(f"删除知识库失败: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            logger.info(f"知识库删除成功: {kb_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除知识库失败: {str(e)}"
            )
    
    # ========== 文档管理方法 ==========
    
    async def get_documents(
        self, 
        kb_id: str, 
        skip: int = 0, 
        limit: int = 100,
        status_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取知识库中的文档列表
        
        Args:
            kb_id: 知识库ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            status_filter: 状态过滤
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 文档列表
        """
        try:
            # 验证访问权限
            if user_id:
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    logger.warning(f"用户 {user_id} 无权访问知识库 {kb_id}")
                    return []
            
            # 使用核心业务逻辑层获取文档列表
            result = await self.doc_processor.list_documents(
                kb_id=kb_id,
                status=status_filter,
                skip=skip,
                limit=limit
            )
            
            if not result["success"]:
                logger.error(f"获取文档列表失败: {result['error']}")
                return []
            
            return result["data"]["documents"]
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {str(e)}")
            return []
    
    async def get_document(
        self, 
        doc_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个文档详情
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 文档详情
        """
        try:
            # 使用核心业务逻辑层获取文档
            result = await self.doc_processor.get_document(doc_id)
            
            if not result["success"]:
                logger.error(f"获取文档失败: {result['error']}")
                return None
            
            # 验证访问权限
            if user_id:
                kb_id = result["data"]["kb_id"]
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    logger.warning(f"用户 {user_id} 无权访问文档 {doc_id}")
                    return None
            
            return result["data"]
            
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None
    
    async def create_document(
        self, 
        kb_id: str,
        doc_data: Union[DocumentCreate, Dict[str, Any]],
        file: Optional[UploadFile] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建文档
        
        Args:
            kb_id: 知识库ID
            doc_data: 文档数据
            file: 上传的文件
            user_id: 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 创建的文档信息
        """
        try:
            # 验证访问权限
            if user_id:
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权访问该知识库"
                    )
            
            # 处理文件上传
            file_path = None
            content = None
            mime_type = "text/plain"
            
            if file:
                # 上传文件到对象存储
                file_path = await upload_file(file)
                mime_type = file.content_type or "application/octet-stream"
            elif isinstance(doc_data, DocumentCreate):
                content = doc_data.content
                mime_type = getattr(doc_data, 'mime_type', 'text/plain')
            elif isinstance(doc_data, dict):
                content = doc_data.get("content")
                mime_type = doc_data.get("mime_type", "text/plain")
            
            # 转换输入数据
            if isinstance(doc_data, DocumentCreate):
                name = doc_data.name
                metadata = getattr(doc_data, 'metadata', {})
            else:
                name = doc_data["name"]
                metadata = doc_data.get("metadata", {})
            
            # 使用核心业务逻辑层创建文档
            result = await self.doc_processor.create_document(
                kb_id=kb_id,
                name=name,
                content=content,
                file_path=file_path,
                mime_type=mime_type,
                metadata=metadata,
                user_id=user_id
            )
            
            if not result["success"]:
                logger.error(f"创建文档失败: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            logger.info(f"文档创建成功: {result['data']['id']}")
            return result["data"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"创建文档失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建文档失败: {str(e)}"
            )
    
    async def process_document(
        self, 
        doc_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        user_id: Optional[str] = None
    ) -> bool:
        """
        处理文档（分块和向量化）
        
        Args:
            doc_id: 文档ID
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            user_id: 用户ID
            
        Returns:
            bool: 是否处理成功
        """
        try:
            # 获取文档信息以验证权限
            doc_result = await self.doc_processor.get_document(doc_id)
            if not doc_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="文档不存在"
                )
            
            # 验证访问权限
            if user_id:
                kb_id = doc_result["data"]["kb_id"]
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权访问该文档"
                    )
            
            # 使用核心业务逻辑层处理文档
            result = await self.doc_processor.process_document(
                doc_id=doc_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if not result["success"]:
                logger.error(f"处理文档失败: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            logger.info(f"文档处理成功: {doc_id}, 生成 {result['data']['chunks_created']} 个分块")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"处理文档失败: {str(e)}"
            )
    
    async def delete_document(
        self, 
        doc_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        删除文档
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取文档信息以验证权限
            doc_result = await self.doc_processor.get_document(doc_id)
            if not doc_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="文档不存在"
                )
            
            # 验证访问权限
            if user_id:
                kb_id = doc_result["data"]["kb_id"]
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="无权访问该文档"
                    )
            
            # 使用核心业务逻辑层删除文档
            result = await self.doc_processor.delete_document(doc_id)
            
            if not result["success"]:
                logger.error(f"删除文档失败: {result['error']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            
            logger.info(f"文档删除成功: {doc_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文档失败: {str(e)}"
            )
    
    # ========== 搜索方法 ==========
    
    async def search(
        self,
        query: str,
        kb_id: str,
        search_type: str = "hybrid",
        top_k: int = 10,
        threshold: float = 0.7,
        user_id: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        在知识库中搜索
        
        Args:
            query: 查询文本
            kb_id: 知识库ID
            search_type: 搜索类型 (semantic, keyword, hybrid)
            top_k: 返回结果数量
            threshold: 相似度阈值
            user_id: 用户ID
            **kwargs: 其他搜索参数
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        try:
            # 验证访问权限
            if user_id:
                has_access = await self.kb_manager.validate_knowledge_base_access(kb_id, user_id)
                if not has_access:
                    logger.warning(f"用户 {user_id} 无权访问知识库 {kb_id}")
                    return []
            
            # 根据搜索类型调用相应方法
            if search_type == "semantic":
                result = await self.retrieval_manager.semantic_search(
                    query=query,
                    kb_id=kb_id,
                    top_k=top_k,
                    threshold=threshold,
                    **kwargs
                )
            elif search_type == "keyword":
                result = await self.retrieval_manager.keyword_search(
                    query=query,
                    kb_id=kb_id,
                    top_k=top_k,
                    **kwargs
                )
            elif search_type == "hybrid":
                result = await self.retrieval_manager.hybrid_search(
                    query=query,
                    kb_id=kb_id,
                    top_k=top_k,
                    threshold=threshold,
                    **kwargs
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的搜索类型: {search_type}"
                )
            
            if not result["success"]:
                logger.error(f"搜索失败: {result['error']}")
                return []
            
            return result["data"]["results"]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []
    
    # ========== 兼容性方法 ==========
    
    async def _get_knowledge_base_stats_from_db(self, kb_id: str) -> Dict[str, Any]:
        """
        从数据库获取知识库统计信息（兼容性方法）
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 使用核心业务逻辑层获取统计信息
            result = await self.kb_manager._get_knowledge_base_stats(kb_id)
            return result
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "document_count": 0,
                "chunk_count": 0,
                "last_document_updated": None
            }

# ========== 兼容性适配器 ==========

class LegacyKnowledgeServiceAdapter:
    """
    遗留代码兼容适配器
    提供与原有KnowledgeService相同的接口，底层使用UnifiedKnowledgeService
    """
    
    def __init__(self, db: Session):
        self.unified_service = UnifiedKnowledgeService(db)
    
    # 转发所有方法到统一服务
    async def get_knowledge_bases(self, *args, **kwargs):
        return await self.unified_service.get_knowledge_bases(*args, **kwargs)
    
    async def get_knowledge_base(self, *args, **kwargs):
        return await self.unified_service.get_knowledge_base(*args, **kwargs)
    
    async def create_knowledge_base(self, *args, **kwargs):
        return await self.unified_service.create_knowledge_base(*args, **kwargs)
    
    async def update_knowledge_base(self, *args, **kwargs):
        return await self.unified_service.update_knowledge_base(*args, **kwargs)
    
    async def delete_knowledge_base(self, *args, **kwargs):
        return await self.unified_service.delete_knowledge_base(*args, **kwargs)
    
    async def search(self, *args, **kwargs):
        return await self.unified_service.search(*args, **kwargs)
    
    # 添加其他需要的方法...

# ========== 全局服务实例 ==========

def get_unified_knowledge_service(db: Session) -> UnifiedKnowledgeService:
    """获取统一知识库服务实例"""
    return UnifiedKnowledgeService(db)

def get_legacy_adapter(db: Session) -> LegacyKnowledgeServiceAdapter:
    """获取遗留适配器实例"""
    return LegacyKnowledgeServiceAdapter(db) 