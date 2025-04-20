"""
知识库仓库模块: 提供知识库、文档及文档分块的数据访问
"""

from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.repositories.base import BaseRepository

class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """知识库仓库"""
    
    def __init__(self, db: Session):
        super().__init__(KnowledgeBase, db)
    
    def get_with_documents(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库及其所有文档"""
        return self.db.query(KnowledgeBase).options(
            joinedload(KnowledgeBase.documents)
        ).filter(KnowledgeBase.id == kb_id).first()
    
    def get_active_knowledge_bases(self) -> List[KnowledgeBase]:
        """获取所有活跃的知识库"""
        return self.db.query(KnowledgeBase).filter(KnowledgeBase.status == "active").all()
    
    def search_knowledge_bases(self, query: str, skip: int = 0, limit: int = 20) -> List[KnowledgeBase]:
        """搜索知识库"""
        search = f"%{query}%"
        return self.db.query(KnowledgeBase).filter(
            or_(
                KnowledgeBase.name.ilike(search),
                KnowledgeBase.description.ilike(search)
            )
        ).offset(skip).limit(limit).all()
    
    def update_status(self, kb_id: str, status: str) -> Optional[KnowledgeBase]:
        """更新知识库状态"""
        return self.update(kb_id, {"status": status})


class DocumentRepository(BaseRepository[Document]):
    """文档仓库"""
    
    def __init__(self, db: Session):
        super().__init__(Document, db)
    
    def get_by_knowledge_base(self, kb_id: str, status: Optional[str] = None) -> List[Document]:
        """获取知识库的所有文档，可按状态过滤"""
        query = self.db.query(Document).filter(Document.knowledge_base_id == kb_id)
        
        if status:
            query = query.filter(Document.status == status)
            
        return query.all()
    
    def get_with_chunks(self, doc_id: str) -> Optional[Document]:
        """获取文档及其所有分块"""
        return self.db.query(Document).options(
            joinedload(Document.chunks)
        ).filter(Document.id == doc_id).first()
        
    def update_status(self, doc_id: str, status: str) -> Optional[Document]:
        """更新文档状态"""
        return self.update(doc_id, {"status": status})
    
    def count_by_knowledge_base(self, kb_id: str, status: Optional[str] = None) -> int:
        """计算知识库文档数量，可按状态过滤"""
        query = self.db.query(Document).filter(Document.knowledge_base_id == kb_id)
        
        if status:
            query = query.filter(Document.status == status)
            
        return query.count()


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """文档分块仓库"""
    
    def __init__(self, db: Session):
        super().__init__(DocumentChunk, db)
    
    def get_by_document(self, doc_id: str) -> List[DocumentChunk]:
        """获取文档的所有分块"""
        return self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    
    def get_by_vector_id(self, vector_id: str) -> Optional[DocumentChunk]:
        """通过向量ID获取分块"""
        return self.db.query(DocumentChunk).filter(DocumentChunk.vector_id == vector_id).first()
    
    def bulk_create(self, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """批量创建分块"""
        try:
            db_chunks = [DocumentChunk(**chunk) for chunk in chunks]
            self.db.add_all(db_chunks)
            self.db.commit()
            
            # 刷新对象以获取生成的ID
            for chunk in db_chunks:
                self.db.refresh(chunk)
                
            return db_chunks
        except Exception as e:
            self.db.rollback()
            raise
    
    def update_vector_id(self, chunk_id: str, vector_id: str) -> Optional[DocumentChunk]:
        """更新分块的向量ID"""
        return self.update(chunk_id, {"vector_id": vector_id})
    
    def find_by_content(self, content_query: str, limit: int = 10) -> List[DocumentChunk]:
        """通过内容搜索分块"""
        search = f"%{content_query}%"
        return self.db.query(DocumentChunk).filter(
            DocumentChunk.content.ilike(search)
        ).limit(limit).all()
