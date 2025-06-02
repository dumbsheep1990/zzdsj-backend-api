"""
知识库服务模块: 提供知识库相关的业务逻辑处理
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.repositories.knowledge import KnowledgeBaseRepository, DocumentRepository, DocumentChunkRepository
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.utils.storage.vector_storage import get_vector_store
from app.config import settings

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识库服务类"""
    
    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
    
    async def create_knowledge_base(self, name: str, description: Optional[str] = None, 
                                   embedding_model: Optional[str] = None) -> KnowledgeBase:
        """
        创建新知识库
        
        参数:
            name: 知识库名称
            description: 知识库描述
            embedding_model: 嵌入模型
        
        返回:
            新建的知识库
        """
        try:
            # 使用默认嵌入模型（如果未指定）
            if not embedding_model:
                embedding_model = settings.EMBEDDING_MODEL
            
            kb_data = {
                "id": str(uuid.uuid4()),
                "name": name,
                "description": description,
                "embedding_model": embedding_model,
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 创建知识库
            kb = self.kb_repo.create(kb_data)
            logger.info(f"已创建知识库: {kb.name} (ID: {kb.id})")
            
            # 初始化向量存储
            vector_store = get_vector_store()
            await vector_store.create_collection(kb.id)
            
            return kb
            
        except Exception as e:
            logger.error(f"创建知识库时出错: {str(e)}")
            raise
    
    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库"""
        return self.kb_repo.get_by_id(kb_id)
    
    async def get_knowledge_base_with_documents(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库及其所有文档"""
        return self.kb_repo.get_with_documents(kb_id)
    
    async def update_knowledge_base(self, kb_id: str, 
                                  data: Dict[str, Any]) -> Optional[KnowledgeBase]:
        """更新知识库信息"""
        return self.kb_repo.update(kb_id, data)
    
    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """
        删除知识库
        
        参数:
            kb_id: 知识库ID
        
        返回:
            操作是否成功
        """
        try:
            # 先删除向量存储中的集合
            vector_store = get_vector_store()
            await vector_store.delete_collection(kb_id)
            
            # 然后删除数据库中的记录
            return self.kb_repo.delete(kb_id)
            
        except Exception as e:
            logger.error(f"删除知识库时出错: {str(e)}")
            raise
    
    async def add_document(self, kb_id: str, file_name: str, file_path: str, 
                         content_type: str, file_size: int, 
                         metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        添加文档到知识库
        
        参数:
            kb_id: 知识库ID
            file_name: 文件名
            file_path: 文件路径
            content_type: 内容类型
            file_size: 文件大小
            metadata: 元数据
        
        返回:
            创建的文档
        """
        try:
            # 验证知识库是否存在
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 创建文档记录
            doc_data = {
                "id": str(uuid.uuid4()),
                "knowledge_base_id": kb_id,
                "file_name": file_name,
                "file_path": file_path,
                "content_type": content_type,
                "file_size": file_size,
                "status": "pending",  # 文档初始状态为待处理
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            document = self.doc_repo.create(doc_data)
            logger.info(f"已将文档添加到知识库: {file_name} (ID: {document.id})")
            
            return document
            
        except Exception as e:
            logger.error(f"添加文档时出错: {str(e)}")
            raise
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档"""
        return self.doc_repo.get_by_id(doc_id)
    
    async def update_document_status(self, doc_id: str, status: str) -> Optional[Document]:
        """更新文档状态"""
        return self.doc_repo.update_status(doc_id, status)
    
    async def add_document_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """
        添加文档分块
        
        参数:
            doc_id: 文档ID
            chunks: 分块内容列表，每个元素包含内容和元数据
        
        返回:
            创建的分块列表
        """
        try:
            # 验证文档是否存在
            document = await self.get_document(doc_id)
            if not document:
                raise ValueError(f"文档不存在: {doc_id}")
            
            # 准备分块数据
            chunk_data_list = []
            for i, chunk in enumerate(chunks):
                chunk_data = {
                    "id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "content": chunk["content"],
                    "chunk_index": i,
                    "metadata": chunk.get("metadata", {}),
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                chunk_data_list.append(chunk_data)
            
            # 批量创建分块
            created_chunks = self.chunk_repo.bulk_create(chunk_data_list)
            logger.info(f"已为文档 {doc_id} 添加 {len(created_chunks)} 个分块")
            
            return created_chunks
            
        except Exception as e:
            logger.error(f"添加文档分块时出错: {str(e)}")
            raise
    
    async def index_document_chunks(self, kb_id: str, chunks: List[DocumentChunk]) -> bool:
        """
        将文档分块索引到向量存储
        
        参数:
            kb_id: 知识库ID
            chunks: 文档分块列表
        
        返回:
            操作是否成功
        """
        try:
            if not chunks:
                return True
                
            # 获取知识库
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 获取向量存储
            vector_store = get_vector_store()
            
            # 准备向量存储的文档
            texts = [chunk.content for chunk in chunks]
            metadatas = [{"chunk_id": chunk.id, "document_id": chunk.document_id, **chunk.metadata} for chunk in chunks]
            
            # 获取嵌入模型
            embedding_model = kb.embedding_model or settings.EMBEDDING_MODEL
            
            # 添加到向量存储
            ids = await vector_store.add_texts(collection_name=kb_id, 
                                              texts=texts, 
                                              metadatas=metadatas,
                                              embedding_model=embedding_model)
            
            # 更新分块的向量ID
            for i, chunk in enumerate(chunks):
                await self.chunk_repo.update_vector_id(chunk.id, ids[i])
            
            logger.info(f"已将 {len(chunks)} 个分块索引到向量存储 (知识库: {kb_id})")
            return True
            
        except Exception as e:
            logger.error(f"索引文档分块时出错: {str(e)}")
            raise
    
    async def search(self, kb_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        参数:
            kb_id: 知识库ID
            query: 搜索查询
            top_k: 返回结果数量
        
        返回:
            搜索结果列表
        """
        try:
            # 验证知识库是否存在
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 获取向量存储
            vector_store = get_vector_store()
            
            # 获取嵌入模型
            embedding_model = kb.embedding_model or settings.EMBEDDING_MODEL
            
            # 执行搜索
            results = await vector_store.similarity_search(
                collection_name=kb_id,
                query=query,
                k=top_k,
                embedding_model=embedding_model
            )
            
            # 格式化结果
            formatted_results = []
            for result in results:
                # 获取分块详细信息
                chunk = self.chunk_repo.get_by_id(result["metadata"]["chunk_id"])
                if chunk:
                    # 获取文档信息
                    document = self.doc_repo.get_by_id(chunk.document_id)
                    
                    formatted_result = {
                        "id": chunk.id,
                        "content": chunk.content,
                        "score": result["score"],
                        "document": {
                            "id": document.id if document else None,
                            "file_name": document.file_name if document else None,
                            "content_type": document.content_type if document else None
                        },
                        "metadata": chunk.metadata
                    }
                    formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索知识库时出错: {str(e)}")
            raise
