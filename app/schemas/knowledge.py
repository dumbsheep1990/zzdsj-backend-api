from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# 基础知识库模式
class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = {}
    type: Optional[str] = "default"
    embedding_model: Optional[str] = "text-embedding-ada-002"

# 创建知识库模式
class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

# 更新知识库模式
class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    type: Optional[str] = None
    embedding_model: Optional[str] = None

# 知识库模式（用于响应）
class KnowledgeBase(KnowledgeBaseBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_documents: int
    total_tokens: int
    agno_kb_id: Optional[str] = None
    
    class Config:
        orm_mode = True

# 带统计数据的知识库
class KnowledgeBaseWithStats(KnowledgeBase):
    document_count: int
    total_tokens: int
    file_types: Dict[str, int] = {}
    
    class Config:
        orm_mode = True

# 文档基础模式
class DocumentBase(BaseModel):
    title: str
    content: Optional[str] = None
    mime_type: Optional[str] = "text/plain"
    metadata: Optional[Dict[str, Any]] = {}
    file_path: Optional[str] = None

# 创建文档模式
class DocumentCreate(DocumentBase):
    knowledge_base_id: int

# 更新文档模式
class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

# 文档模式（用于响应）
class Document(DocumentBase):
    id: int
    knowledge_base_id: int
    created_at: datetime
    updated_at: datetime
    file_size: int
    status: str
    error_message: Optional[str] = None
    
    class Config:
        orm_mode = True

# 文档块模式
class DocumentChunk(BaseModel):
    id: int
    document_id: int
    content: str
    metadata: Dict[str, Any]
    embedding_id: str
    token_count: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# 知识库统计数据模式
class KnowledgeBaseStats(BaseModel):
    document_count: int
    total_tokens: int
    processed_count: int
    pending_count: int
    error_count: int
    file_types: Dict[str, int] = {}

# 文档列表响应
class DocumentListResponse(BaseModel):
    items: List[Document]
    total: int
    page: int
    page_size: int
