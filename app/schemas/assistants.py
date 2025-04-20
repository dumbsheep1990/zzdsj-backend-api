from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# Base Assistant Schema
class AssistantBase(BaseModel):
    name: str
    description: Optional[str] = None
    model_id: Optional[str] = "gpt-4"
    capabilities: Optional[Dict[str, bool]] = {
        "customer_support": True,
        "question_answering": True,
        "service_intro": True
    }

# Create Assistant Schema
class AssistantCreate(AssistantBase):
    pass

# Update Assistant Schema
class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_id: Optional[str] = None
    is_active: Optional[bool] = None
    capabilities: Optional[Dict[str, bool]] = None

# Assistant Schema (for responses)
class Assistant(AssistantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Assistant with Knowledge Bases
class AssistantWithKnowledgeBases(Assistant):
    knowledge_bases: List["KnowledgeBaseInfo"] = []

# Knowledge Base Info (for nested relationships)
class KnowledgeBaseInfo(BaseModel):
    id: int
    name: str
    
    class Config:
        orm_mode = True

# Update references to handle circular imports
AssistantWithKnowledgeBases.update_forward_refs()
