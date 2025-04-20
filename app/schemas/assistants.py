from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# 基础助手模式
class AssistantBase(BaseModel):
    name: str
    description: Optional[str] = None
    model_id: Optional[str] = "gpt-4"
    capabilities: Optional[Dict[str, bool]] = {
        "customer_support": True,
        "question_answering": True,
        "service_intro": True
    }

# 创建助手模式
class AssistantCreate(AssistantBase):
    pass

# 更新助手模式
class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_id: Optional[str] = None
    is_active: Optional[bool] = None
    capabilities: Optional[Dict[str, bool]] = None

# 助手模式（用于响应）
class Assistant(AssistantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# 带知识库的助手
class AssistantWithKnowledgeBases(Assistant):
    knowledge_bases: List["KnowledgeBaseInfo"] = []

# 知识库信息（用于嵌套关系）
class KnowledgeBaseInfo(BaseModel):
    id: int
    name: str
    
    class Config:
        orm_mode = True

# 更新引用以处理循环导入
AssistantWithKnowledgeBases.update_forward_refs()
