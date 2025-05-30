"""
统一知识库服务
整合原有的两个KnowledgeService类，提供统一的知识库管理接口
遵循分层架构：API层 -> 服务层 -> 数据访问层 -> 数据库
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
            # 使用统一管理器获取知识库
            all_kbs = await self.unified_manager.list_knowledge_bases(user_id)
            
            # 应用过滤条件
            filtered_kbs = []
            for kb in all_kbs:
                # 状态过滤
                if is_active is not None and kb.get("is_active") != is_active:
                    continue
                
                # 搜索过滤
                if search and search.lower() not in kb.get("name", "").lower():
                    continue
                
                filtered_kbs.append(kb)
            
            # 分页
            start = skip
            end = skip + limit
            paginated_kbs = filtered_kbs[start:end]
            
            # 转换为标准格式并添加统计信息
            result = []
            for kb in paginated_kbs:
                # 从数据库获取详细统计信息
                kb_id = kb["kb_id"]
                stats = await self._get_knowledge_base_stats_from_db(kb_id)
                
                kb_dict = {
                    "id": kb_id,
                    "name": kb["name"],
                    "description": kb["description"],
                    "is_active": kb.get("is_active", True),
                    "created_at": kb.get("created_at"),
                    "updated_at": kb.get("last_updated"),
                    "embedding_model": kb.get("embedding_model", "text-embedding-ada-002"),
                    "stats": stats
                }
                result.append(kb_dict)
            
            return result
            
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
            # 使用统一管理器获取知识库
            kb_info = await self.unified_manager.get_knowledge_base(kb_id)
            
            if not kb_info:
                return None
            
            # 获取详细统计信息
            stats = await self._get_knowledge_base_stats_from_db(kb_id)
            
            # 转换为标准格式
            return {
                "id": kb_info["kb_id"],
                "name": kb_info["name"],
                "description": kb_info["description"],
                "is_active": kb_info.get("is_active", True),
                "created_at": kb_info.get("created_at"),
                "updated_at": kb_info.get("last_updated"),
                "embedding_model": kb_info.get("embedding_model", "text-embedding-ada-002"),
                "settings": kb_info.get("settings", {}),
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"获取知识库失败: {str(e)}")
            return None
    
    async def create_knowledge_base(
        self, 
        kb_data: Union[KnowledgeBaseCreate, Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> KnowledgeBase:
        """
        创建新知识库
        
        Args:
            kb_data: 知识库创建数据
            user_id: 创建者ID
            
        Returns:
            KnowledgeBase: 创建的知识库对象
            
        Raises:
            HTTPException: 如果创建过程中出错
        """
        try:
            # 转换数据格式
            if isinstance(kb_data, KnowledgeBaseCreate):
                data_dict = kb_data.dict()
            else:
                data_dict = kb_data
            
            # 使用统一管理器创建
            config = KnowledgeBaseConfig(
                name=data_dict["name"],
                description=data_dict.get("description", ""),
                embedding_model=data_dict.get("embedding_model", "text-embedding-ada-002"),
                is_active=data_dict.get("is_active", True),
                chunking_strategy=data_dict.get("chunking_strategy", "sentence"),
                chunk_size=data_dict.get("chunk_size", 1000),
                chunk_overlap=data_dict.get("chunk_overlap", 200)
            )
            
            result = await self.unified_manager.create_knowledge_base(config, user_id)
            
            if result.get("status") == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"创建知识库失败: {result.get('error', '未知错误')}"
                )
            
            # 从数据库获取创建的知识库对象
            db_kb = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == result["kb_id"]
            ).first()
            
            if not db_kb:
                # 如果数据库中没有，创建数据库记录
                db_kb = KnowledgeBase(
                    id=result["kb_id"],
                    name=result["name"],
                    description=result["description"],
                    is_active=True,
                    embedding_model=config.embedding_model,
                    settings=config.to_dict()
                )
                self.db.add(db_kb)
                self.db.commit()
                self.db.refresh(db_kb)
            
            return db_kb
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建知识库失败: {str(e)}"
            )
    
    async def update_knowledge_base(
        self, 
        kb_id: str, 
        update_data: Union[KnowledgeBaseUpdate, Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> KnowledgeBase:
        """
        更新知识库信息
        
        Args:
            kb_id: 知识库ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            KnowledgeBase: 更新后的知识库对象
            
        Raises:
            HTTPException: 如果知识库不存在或更新失败
        """
        try:
            # 转换数据格式
            if isinstance(update_data, KnowledgeBaseUpdate):
                updates = update_data.dict(exclude_unset=True)
            else:
                updates = update_data
            
            # 使用统一管理器更新
            result = await self.unified_manager.update_knowledge_base(kb_id, updates)
            
            if result["status"] != "success":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "更新失败")
                )
            
            # 获取更新后的数据库记录
            db_kb = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == kb_id
            ).first()
            
            if not db_kb:
                raise HTTPException(status_code=404, detail="知识库未找到")
            
            # 同步更新数据库记录
            for field, value in updates.items():
                if hasattr(db_kb, field):
                    setattr(db_kb, field, value)
            
            db_kb.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(db_kb)
            
            return db_kb
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新知识库失败: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新知识库失败: {str(e)}"
            )
    
    async def delete_knowledge_base(
        self, 
        kb_id: str, 
        permanent: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        删除知识库
        
        Args:
            kb_id: 知识库ID
            permanent: 是否物理删除
            user_id: 用户ID
            
        Returns:
            Dict[str, str]: 删除结果消息
            
        Raises:
            HTTPException: 如果知识库不存在或删除失败
        """
        try:
            # 检查知识库是否存在
            db_kb = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == kb_id
            ).first()
            
            if not db_kb:
                raise HTTPException(status_code=404, detail="知识库未找到")
            
            if permanent:
                # 物理删除：删除所有相关数据
                
                # 1. 删除统一管理器中的数据
                result = await self.unified_manager.delete_knowledge_base(kb_id)
                
                # 2. 删除数据库中的相关记录
                # 删除文档块
                chunks = self.db.query(DocumentChunk).join(
                    Document, Document.id == DocumentChunk.document_id
                ).filter(
                    Document.knowledge_base_id == kb_id
                ).all()
                
                for chunk in chunks:
                    self.db.delete(chunk)
                
                # 删除文档
                documents = self.db.query(Document).filter(
                    Document.knowledge_base_id == kb_id
                ).all()
                
                for doc in documents:
                    self.db.delete(doc)
                
                # 删除知识库
                self.db.delete(db_kb)
                self.db.commit()
                
                return {"message": "知识库已永久删除"}
            else:
                # 逻辑删除：标记为非活跃
                db_kb.is_active = False
                db_kb.updated_at = datetime.now()
                self.db.commit()
                
                return {"message": "知识库已停用"}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            self.db.rollback()
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
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Document]:
        """
        获取知识库中的文档列表
        
        Args:
            kb_id: 知识库ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            status: 文档状态过滤
            search: 搜索关键词
            
        Returns:
            List[Document]: 文档列表
            
        Raises:
            HTTPException: 如果知识库不存在
        """
        # 检查知识库是否存在
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="知识库未找到")
        
        # 构建查询
        query = self.db.query(Document).filter(Document.knowledge_base_id == kb_id)
        
        # 应用过滤条件
        if status:
            query = query.filter(Document.status == status)
        
        if search:
            query = query.filter(or_(
                Document.title.ilike(f"%{search}%"),
                Document.content.ilike(f"%{search}%")
            ))
        
        # 分页
        documents = query.offset(skip).limit(limit).all()
        
        return documents
    
    async def get_document_by_id(self, doc_id: str, kb_id: Optional[str] = None) -> Optional[Document]:
        """
        通过ID获取文档详情
        
        Args:
            doc_id: 文档ID
            kb_id: 知识库ID（可选，用于额外验证）
            
        Returns:
            Optional[Document]: 文档详情或None
        """
        query = self.db.query(Document).filter(Document.id == doc_id)
        
        if kb_id:
            query = query.filter(Document.knowledge_base_id == kb_id)
        
        return query.first()
    
    async def create_document(
        self,
        kb_id: str,
        document_data: Union[DocumentCreate, Dict[str, Any]],
        file: Optional[UploadFile] = None,
        user_id: Optional[str] = None
    ) -> Document:
        """
        创建新文档
        
        Args:
            kb_id: 知识库ID
            document_data: 文档创建数据
            file: 可选的上传文件
            user_id: 用户ID
            
        Returns:
            Document: 创建的文档对象
            
        Raises:
            HTTPException: 如果知识库不存在或创建失败
        """
        try:
            # 检查知识库是否存在
            kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                raise HTTPException(status_code=404, detail="知识库未找到")
            
            # 转换数据格式
            if isinstance(document_data, DocumentCreate):
                data_dict = document_data.dict()
            else:
                data_dict = document_data
            
            # 处理文件上传（如果有）
            file_url = None
            if file:
                try:
                    filename = f"{kb_id}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                    file_url = await upload_file(file, filename)
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"文件上传失败: {str(e)}"
                    )
            
            # 准备文档数据
            document = {
                "title": data_dict.get("title", "Untitled"),
                "content": data_dict.get("content", ""),
                "metadata": {
                    **data_dict.get("metadata", {}),
                    "file_url": file_url or data_dict.get("file_url"),
                    "uploaded_by": user_id,
                    "uploaded_at": datetime.now().isoformat()
                }
            }
            
            # 使用统一管理器添加文档
            result = await self.unified_manager.add_document(kb_id, document)
            
            if result["status"] != "success":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"添加文档失败: {result.get('error', '未知错误')}"
                )
            
            # 创建数据库记录
            db_document = Document(
                id=result["document_id"],
                knowledge_base_id=kb_id,
                title=document["title"],
                content=document["content"],
                file_url=file_url or data_dict.get("file_url"),
                metadata=document["metadata"],
                language=data_dict.get("language", "zh"),
                doc_type=data_dict.get("doc_type", "text"),
                status="indexed"  # 统一管理器已处理完成
            )
            
            self.db.add(db_document)
            self.db.commit()
            self.db.refresh(db_document)
            
            return db_document
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"创建文档失败: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建文档失败: {str(e)}"
            )
    
    async def update_document(
        self,
        doc_id: str,
        document_data: Union[DocumentUpdate, Dict[str, Any]]
    ) -> Document:
        """
        更新文档信息
        
        Args:
            doc_id: 文档ID
            document_data: 文档更新数据
            
        Returns:
            Document: 更新后的文档对象
            
        Raises:
            HTTPException: 如果文档不存在或更新失败
        """
        try:
            db_document = await self.get_document_by_id(doc_id)
            if not db_document:
                raise HTTPException(status_code=404, detail="文档未找到")
            
            # 转换数据格式
            if isinstance(document_data, DocumentUpdate):
                update_data = document_data.dict(exclude_unset=True)
            else:
                update_data = document_data
            
            # 更新提供的字段
            for field, value in update_data.items():
                if hasattr(db_document, field):
                    setattr(db_document, field, value)
            
            db_document.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(db_document)
            
            return db_document
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新文档失败: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新文档失败: {str(e)}"
            )
    
    async def delete_document(self, doc_id: str, kb_id: Optional[str] = None) -> bool:
        """
        删除文档
        
        Args:
            doc_id: 文档ID
            kb_id: 知识库ID（可选）
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            HTTPException: 如果文档不存在或删除失败
        """
        try:
            db_document = await self.get_document_by_id(doc_id, kb_id)
            if not db_document:
                raise HTTPException(status_code=404, detail="文档未找到")
            
            # 从统一管理器中删除
            if kb_id:
                await self.unified_manager.remove_document(kb_id, doc_id)
            
            # 删除数据库中的文档块
            self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id
            ).delete()
            
            # 删除文档
            self.db.delete(db_document)
            self.db.commit()
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文档失败: {str(e)}"
            )
    
    # ========== 搜索方法 ==========
    
    async def search(self, kb_id: str, query: str, top_k: int = 5, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            kb_id: 知识库ID
            query: 搜索查询
            top_k: 返回结果数量
            filter_criteria: 过滤条件
        
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
        """
        try:
            # 验证知识库是否存在
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 使用统一管理器搜索
            results = await self.unified_manager.search_documents(
                kb_id, query, filter_criteria, top_k
            )
            
            return results
            
        except Exception as e:
            logger.error(f"搜索知识库时出错: {str(e)}")
            raise
    
    # ========== 统计信息方法 ==========
    
    async def get_knowledge_base_stats(self, kb_id: str) -> Dict[str, Any]:
        """
        获取知识库的统计信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        return await self._get_knowledge_base_stats_from_db(kb_id)
    
    async def _get_knowledge_base_stats_from_db(self, kb_id: str) -> Dict[str, Any]:
        """
        从数据库获取知识库的统计信息
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 获取文档数量
            doc_count = self.db.query(func.count(Document.id)).filter(
                Document.knowledge_base_id == kb_id
            ).scalar() or 0
            
            # 获取文档块数量
            chunk_count = self.db.query(func.count(DocumentChunk.id)).join(
                Document, Document.id == DocumentChunk.document_id
            ).filter(
                Document.knowledge_base_id == kb_id
            ).scalar() or 0
            
            # 获取语言分布
            languages = self.db.query(
                Document.language, func.count(Document.id).label('count')
            ).filter(
                Document.knowledge_base_id == kb_id
            ).group_by(Document.language).all()
            
            lang_distribution = {lang: count for lang, count in languages} if languages else {}
            
            # 计算字符总量
            total_characters = self.db.query(func.sum(DocumentChunk.token_count)).join(
                Document, Document.id == DocumentChunk.document_id
            ).filter(
                Document.knowledge_base_id == kb_id
            ).scalar() or 0
            
            return {
                "document_count": doc_count,
                "chunk_count": chunk_count,
                "language_distribution": lang_distribution,
                "total_characters": total_characters
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "document_count": 0,
                "chunk_count": 0,
                "language_distribution": {},
                "total_characters": 0
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