from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# Base Knowledge Base Schema
class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = {}
    type: Optional[str] = "default"
    embedding_model: Optional[str] = "text-embedding-ada-002"

# Create Knowledge Base Schema
class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

# Update Knowledge Base Schema
class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    type: Optional[str] = None
    embedding_model: Optional[str] = None

# Knowledge Base Schema (for responses)
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

# Knowledge Base with Stats
class KnowledgeBaseWithStats(KnowledgeBase):
    document_count: int
    total_tokens: int
    file_types: Dict[str, int] = {}
    
    class Config:
        orm_mode = True

# Document Base Schema
class DocumentBase(BaseModel):
    title: str
    content: Optional[str] = None
    mime_type: Optional[str] = "text/plain"
    metadata: Optional[Dict[str, Any]] = {}
    file_path: Optional[str] = None

# Create Document Schema
class DocumentCreate(DocumentBase):
    knowledge_base_id: int

# Update Document Schema
class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

# Document Schema (for responses)
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

# Document Chunk Schema
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

# Knowledge Base Stats Schema
class KnowledgeBaseStats(BaseModel):
    document_count: int
    total_tokens: int
    processed_count: int
    pending_count: int
    error_count: int
    file_types: Dict[str, int] = {}

# Document List Response
class DocumentListResponse(BaseModel):
    items: List[Document]
    total: int
    page: int
    page_size: int
