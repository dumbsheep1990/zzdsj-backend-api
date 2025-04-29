"""
LlamaIndex存储适配器: 提供自定义的PostgreSQL和Redis存储后端
"""

from typing import Dict, List, Optional, Any, Union, Sequence, Set
from llama_index.core.schema import Document, BaseNode, TextNode
from llama_index.core.storage.docstore import SimpleDocumentStore, BaseDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore, BaseIndexStore
from llama_index.core.storage.kvstore import SimpleKVStore, BaseKVStore
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import json
import logging

from app.utils.database import db_manager
from app.models.knowledge import DocumentChunk
from app.models.assistants import Assistant

logger = logging.getLogger(__name__)

class PostgresDocumentStore(BaseDocumentStore):
    """PostgreSQL文档存储适配器"""
    
    def __init__(self, namespace: Optional[str] = None):
        """
        初始化PostgreSQL文档存储
        
        Args:
            namespace: 命名空间，用于隔离不同的存储实例
        """
        self.namespace = namespace or "default"
        self._simple_docstore = SimpleDocumentStore()  # 用作备份和缓存
        logger.info(f"初始化PostgreSQL文档存储，命名空间: {self.namespace}")
    
    def add_documents(self, docs: List[Document], **kwargs: Any) -> None:
        """
        添加文档到存储
        
        Args:
            docs: 文档列表
            **kwargs: 附加参数
        """
        # 先添加到内存存储作为缓存
        self._simple_docstore.add_documents(docs, **kwargs)
        
        # 转换为数据库模型并存储
        def _add_to_db(db: Session) -> List[str]:
            doc_ids = []
            
            for doc in docs:
                content = doc.get_content()
                metadata = doc.metadata.copy() if doc.metadata else {}
                
                # 确保命名空间信息被保存
                metadata["namespace"] = self.namespace
                
                # 创建文档块实例
                doc_chunk = DocumentChunk(
                    doc_id=doc.doc_id,
                    content=content,
                    metadata=metadata,
                    namespace=self.namespace
                )
                
                db.add(doc_chunk)
                doc_ids.append(doc.doc_id)
            
            return doc_ids
        
        try:
            doc_ids = db_manager.execute_with_session(_add_to_db)
            logger.info(f"已将{len(doc_ids)}篇文档添加到PostgreSQL存储")
        except Exception as e:
            logger.error(f"向PostgreSQL添加文档时出错: {str(e)}")
            raise
    
    def get_document(self, doc_id: str, **kwargs: Any) -> Optional[Document]:
        """
        从存储中获取文档
        
        Args:
            doc_id: 文档ID
            **kwargs: 附加参数
            
        Returns:
            Document对象或None(如果未找到)
        """
        # 先尝试从内存缓存获取
        doc = self._simple_docstore.get_document(doc_id, **kwargs)
        if doc is not None:
            return doc
        
        # 从数据库获取
        def _get_from_db(db: Session) -> Optional[Document]:
            doc_chunk = db.query(DocumentChunk).filter(
                DocumentChunk.doc_id == doc_id,
                DocumentChunk.namespace == self.namespace
            ).first()
            
            if doc_chunk is None:
                return None
            
            # 转换为Document对象
            metadata = doc_chunk.metadata.copy() if doc_chunk.metadata else {}
            doc = Document(
                text=doc_chunk.content,
                metadata=metadata,
                doc_id=doc_chunk.doc_id
            )
            return doc
        
        try:
            doc = db_manager.execute_with_session(_get_from_db)
            if doc is not None:
                # 添加到内存缓存
                self._simple_docstore.add_documents([doc])
            return doc
        except Exception as e:
            logger.error(f"从PostgreSQL获取文档时出错: {str(e)}")
            return None
    
    def delete_document(self, doc_id: str, **kwargs: Any) -> None:
        """
        从存储中删除文档
        
        Args:
            doc_id: 文档ID
            **kwargs: 附加参数
        """
        # 从内存缓存中删除
        self._simple_docstore.delete_document(doc_id, **kwargs)
        
        # 从数据库中删除
        def _delete_from_db(db: Session) -> bool:
            result = db.query(DocumentChunk).filter(
                DocumentChunk.doc_id == doc_id,
                DocumentChunk.namespace == self.namespace
            ).delete()
            return result > 0
        
        try:
            deleted = db_manager.execute_with_session(_delete_from_db)
            if deleted:
                logger.info(f"已从PostgreSQL删除文档: {doc_id}")
            else:
                logger.warning(f"未找到要删除的文档: {doc_id}")
        except Exception as e:
            logger.error(f"从PostgreSQL删除文档时出错: {str(e)}")
            raise
    
    def documents_dict(self) -> Dict[str, Document]:
        """
        获取存储中的所有文档
        
        Returns:
            文档字典，键为doc_id，值为Document对象
        """
        def _get_all_from_db(db: Session) -> Dict[str, Document]:
            doc_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.namespace == self.namespace
            ).all()
            
            docs_dict = {}
            for doc_chunk in doc_chunks:
                metadata = doc_chunk.metadata.copy() if doc_chunk.metadata else {}
                doc = Document(
                    text=doc_chunk.content,
                    metadata=metadata,
                    doc_id=doc_chunk.doc_id
                )
                docs_dict[doc_chunk.doc_id] = doc
            
            return docs_dict
        
        try:
            docs_dict = db_manager.execute_with_session(_get_all_from_db)
            # 更新内存缓存
            self._simple_docstore = SimpleDocumentStore()
            self._simple_docstore.add_documents(list(docs_dict.values()))
            return docs_dict
        except Exception as e:
            logger.error(f"从PostgreSQL获取所有文档时出错: {str(e)}")
            # 返回内存缓存中的文档
            return self._simple_docstore.documents_dict()

class LlamaIndexStorageAdapter:
    """LlamaIndex存储适配器集成类"""
    
    def __init__(self, namespace: Optional[str] = None):
        """
        初始化存储适配器
        
        Args:
            namespace: 命名空间，用于隔离不同的存储实例
        """
        self.namespace = namespace or "default"
        self.docstore = PostgresDocumentStore(namespace=self.namespace)
        # 使用默认实现作为索引存储和KV存储，后续可以替换为自定义实现
        self.index_store = SimpleIndexStore()
        self.kvstore = SimpleKVStore()
    
    def get_storage_context(self):
        """
        获取LlamaIndex存储上下文
        
        Returns:
            StorageContext对象
        """
        from llama_index.core.storage import StorageContext
        
        return StorageContext.from_defaults(
            docstore=self.docstore,
            index_store=self.index_store,
            kvstore=self.kvstore
        )
