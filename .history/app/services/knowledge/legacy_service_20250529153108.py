"""
知识库服务模块
提供知识库、文档和文档块的业务逻辑和数据访问封装
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status, UploadFile
import os
import json
from datetime import datetime

from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    DocumentCreate,
    DocumentUpdate,
    KnowledgeBaseStats
)
from app.utils.object_storage import upload_file, get_file_url
from app.frameworks.agno import KnowledgeBaseProcessor

@register_service(service_type="knowledge", priority="high", description="知识库管理服务")
class KnowledgeService:
    """
    知识库服务类，提供对KnowledgeBase、Document和DocumentChunk模型的业务逻辑和数据访问操作
    """
    
    def __init__(self, db: Session):
        """
        初始化知识库服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def get_knowledge_bases(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取知识库列表，支持过滤和搜索
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            is_active: 可选的活跃状态过滤
            search: 可选的搜索关键词
            
        Returns:
            List[Dict[str, Any]]: 知识库列表及其统计信息
        """
        query = self.db.query(KnowledgeBase)
        
        # 应用过滤条件
        if is_active is not None:
            query = query.filter(KnowledgeBase.is_active == is_active)
        
        if search:
            query = query.filter(or_(
                KnowledgeBase.name.ilike(f"%{search}%"),
                KnowledgeBase.description.ilike(f"%{search}%")
            ))
        
        # 获取基本知识库数据
        knowledge_bases = query.offset(skip).limit(limit).all()
        
        # 为每个知识库添加统计信息
        result = []
        for kb in knowledge_bases:
            # 获取文档数量
            doc_count = self.db.query(func.count(Document.id)).filter(
                Document.knowledge_base_id == kb.id
            ).scalar() or 0
            
            # 获取文档块数量
            chunk_count = self.db.query(func.count(DocumentChunk.id)).join(
                Document, Document.id == DocumentChunk.document_id
            ).filter(
                Document.knowledge_base_id == kb.id
            ).scalar() or 0
            
            # 获取语言分布
            languages = self.db.query(
                Document.language, func.count(Document.id).label('count')
            ).filter(
                Document.knowledge_base_id == kb.id
            ).group_by(Document.language).all()
            
            lang_distribution = {lang: count for lang, count in languages} if languages else {}
            
            # 计算字符总量
            total_characters = self.db.query(func.sum(DocumentChunk.token_count)).join(
                Document, Document.id == DocumentChunk.document_id
            ).filter(
                Document.knowledge_base_id == kb.id
            ).scalar() or 0
            
            # 构建结果
            kb_dict = {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "is_active": kb.is_active,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at,
                "embedding_model": kb.embedding_model,
                "stats": {
                    "document_count": doc_count,
                    "chunk_count": chunk_count,
                    "language_distribution": lang_distribution,
                    "total_characters": total_characters
                }
            }
            result.append(kb_dict)
        
        return result
    
    async def get_knowledge_base_by_id(self, knowledge_base_id: int) -> Optional[Dict[str, Any]]:
        """
        通过ID获取知识库详情，包含统计信息
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            Optional[Dict[str, Any]]: 知识库详情及统计信息
        """
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
        if not kb:
            return None
            
        # 获取知识库统计信息
        stats = await self._get_knowledge_base_stats(knowledge_base_id)
        
        # 构建结果
        result = {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "is_active": kb.is_active,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
            "embedding_model": kb.embedding_model,
            "stats": stats
        }
        
        return result
    
    async def create_knowledge_base(self, knowledge_base_data: KnowledgeBaseCreate) -> KnowledgeBase:
        """
        创建新知识库
        
        Args:
            knowledge_base_data: 知识库创建数据
            
        Returns:
            KnowledgeBase: 创建的知识库对象
            
        Raises:
            HTTPException: 如果创建过程中出错
        """
        # 创建知识库记录
        db_knowledge_base = KnowledgeBase(
            name=knowledge_base_data.name,
            description=knowledge_base_data.description,
            is_active=knowledge_base_data.is_active,
            embedding_model=knowledge_base_data.embedding_model
        )
        
        try:
            self.db.add(db_knowledge_base)
            self.db.commit()
            self.db.refresh(db_knowledge_base)
            return db_knowledge_base
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建知识库失败: {str(e)}"
            )
    
    async def update_knowledge_base(
        self, 
        knowledge_base_id: int, 
        knowledge_base_data: KnowledgeBaseUpdate
    ) -> KnowledgeBase:
        """
        更新知识库信息
        
        Args:
            knowledge_base_id: 知识库ID
            knowledge_base_data: 知识库更新数据
            
        Returns:
            KnowledgeBase: 更新后的知识库对象
            
        Raises:
            HTTPException: 如果知识库不存在或更新失败
        """
        db_knowledge_base = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id == knowledge_base_id
        ).first()
        
        if not db_knowledge_base:
            raise HTTPException(status_code=404, detail="知识库未找到")
        
        # 更新提供的字段
        update_data = knowledge_base_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_knowledge_base, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(db_knowledge_base)
            return db_knowledge_base
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新知识库失败: {str(e)}"
            )
    
    async def delete_knowledge_base(self, knowledge_base_id: int) -> bool:
        """
        删除知识库
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            HTTPException: 如果知识库不存在或删除失败
        """
        db_knowledge_base = self.db.query(KnowledgeBase).filter(
            KnowledgeBase.id == knowledge_base_id
        ).first()
        
        if not db_knowledge_base:
            raise HTTPException(status_code=404, detail="知识库未找到")
        
        try:
            # 删除知识库中的所有文档块
            chunks = self.db.query(DocumentChunk).join(
                Document, Document.id == DocumentChunk.document_id
            ).filter(
                Document.knowledge_base_id == knowledge_base_id
            ).all()
            
            for chunk in chunks:
                self.db.delete(chunk)
            
            # 删除知识库中的所有文档
            documents = self.db.query(Document).filter(
                Document.knowledge_base_id == knowledge_base_id
            ).all()
            
            for doc in documents:
                self.db.delete(doc)
            
            # 删除知识库
            self.db.delete(db_knowledge_base)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除知识库失败: {str(e)}"
            )
    
    # 文档相关方法
    async def get_documents(
        self,
        knowledge_base_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """
        获取知识库中的文档列表
        
        Args:
            knowledge_base_id: 知识库ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Document]: 文档列表
            
        Raises:
            HTTPException: 如果知识库不存在
        """
        # 检查知识库是否存在
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="知识库未找到")
        
        # 获取文档列表
        documents = self.db.query(Document).filter(
            Document.knowledge_base_id == knowledge_base_id
        ).offset(skip).limit(limit).all()
        
        return documents
    
    async def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """
        通过ID获取文档详情
        
        Args:
            document_id: 文档ID
            
        Returns:
            Optional[Document]: 文档详情或None
        """
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    async def create_document(
        self,
        knowledge_base_id: int,
        document_data: DocumentCreate,
        file: Optional[UploadFile] = None
    ) -> Document:
        """
        创建新文档
        
        Args:
            knowledge_base_id: 知识库ID
            document_data: 文档创建数据
            file: 可选的上传文件
            
        Returns:
            Document: 创建的文档对象
            
        Raises:
            HTTPException: 如果知识库不存在或创建失败
        """
        # 检查知识库是否存在
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
        if not kb:
            raise HTTPException(status_code=404, detail="知识库未找到")
        
        # 处理文件上传（如果有）
        file_url = None
        if file:
            try:
                filename = f"{knowledge_base_id}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                file_url = await upload_file(file, filename)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"文件上传失败: {str(e)}"
                )
        
        # 创建文档记录
        db_document = Document(
            knowledge_base_id=knowledge_base_id,
            title=document_data.title,
            content=document_data.content,
            file_url=file_url or document_data.file_url,
            metadata=document_data.metadata,
            language=document_data.language,
            doc_type=document_data.doc_type,
            status="pending"  # 初始状态为待处理
        )
        
        try:
            self.db.add(db_document)
            self.db.commit()
            self.db.refresh(db_document)
            
            # 处理文档（在后台进行）
            processor = KnowledgeBaseProcessor()
            processor.process_document_async(db_document.id)
            
            return db_document
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建文档失败: {str(e)}"
            )
    
    async def update_document(
        self,
        document_id: int,
        document_data: DocumentUpdate
    ) -> Document:
        """
        更新文档信息
        
        Args:
            document_id: 文档ID
            document_data: 文档更新数据
            
        Returns:
            Document: 更新后的文档对象
            
        Raises:
            HTTPException: 如果文档不存在或更新失败
        """
        db_document = await self.get_document_by_id(document_id)
        if not db_document:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        # 更新提供的字段
        update_data = document_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_document, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(db_document)
            return db_document
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新文档失败: {str(e)}"
            )
    
    async def delete_document(self, document_id: int) -> bool:
        """
        删除文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            bool: 是否删除成功
            
        Raises:
            HTTPException: 如果文档不存在或删除失败
        """
        db_document = await self.get_document_by_id(document_id)
        if not db_document:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        try:
            # 删除文档块
            self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            # 删除文档
            self.db.delete(db_document)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文档失败: {str(e)}"
            )
    
    # 辅助方法
    async def _get_knowledge_base_stats(self, knowledge_base_id: int) -> Dict[str, Any]:
        """
        获取知识库的统计信息
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 获取文档数量
        doc_count = self.db.query(func.count(Document.id)).filter(
            Document.knowledge_base_id == knowledge_base_id
        ).scalar() or 0
        
        # 获取文档块数量
        chunk_count = self.db.query(func.count(DocumentChunk.id)).join(
            Document, Document.id == DocumentChunk.document_id
        ).filter(
            Document.knowledge_base_id == knowledge_base_id
        ).scalar() or 0
        
        # 获取语言分布
        languages = self.db.query(
            Document.language, func.count(Document.id).label('count')
        ).filter(
            Document.knowledge_base_id == knowledge_base_id
        ).group_by(Document.language).all()
        
        lang_distribution = {lang: count for lang, count in languages} if languages else {}
        
        # 计算字符总量
        total_characters = self.db.query(func.sum(DocumentChunk.token_count)).join(
            Document, Document.id == DocumentChunk.document_id
        ).filter(
            Document.knowledge_base_id == knowledge_base_id
        ).scalar() or 0
        
        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "language_distribution": lang_distribution,
            "total_characters": total_characters
        }
