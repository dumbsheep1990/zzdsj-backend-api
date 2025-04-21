"""
问答助手模式
定义问答助手和问题卡片相关的API请求和响应模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AnswerModeEnum(str):
    """回答模式枚举"""
    DEFAULT = "default"       # 默认模式
    DOCS_ONLY = "docs_only"   # 仅从文档回答
    MODEL_ONLY = "model_only" # 仅使用模型回答
    HYBRID = "hybrid"         # 混合模式


# 助手模式
class AssistantBase(BaseModel):
    """助手基础模式"""
    name: str
    description: Optional[str] = None
    type: str
    icon: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AssistantCreate(AssistantBase):
    """创建助手请求"""
    knowledge_base_id: Optional[int] = None


class AssistantUpdate(BaseModel):
    """更新助手请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    knowledge_base_id: Optional[int] = None


class QuestionStats(BaseModel):
    """问题统计信息"""
    total_questions: int
    total_views: int


class AssistantResponse(AssistantBase):
    """助手响应"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    knowledge_base_id: Optional[int] = None
    stats: Optional[QuestionStats] = None

    class Config:
        from_attributes = True


class AssistantList(BaseModel):
    """助手列表响应"""
    items: List[AssistantResponse]
    total: int


# 问题模式
class QuestionBase(BaseModel):
    """问题基础模式"""
    question_text: str
    answer_text: Optional[str] = None
    answer_mode: Optional[str] = AnswerModeEnum.DEFAULT
    use_cache: Optional[bool] = True


class QuestionCreate(QuestionBase):
    """创建问题请求"""
    assistant_id: int


class QuestionUpdate(BaseModel):
    """更新问题请求"""
    question_text: Optional[str] = None
    answer_text: Optional[str] = None
    answer_mode: Optional[str] = None
    use_cache: Optional[bool] = None
    enabled: Optional[bool] = None


class DocumentSegmentBase(BaseModel):
    """文档分段基础模式"""
    document_id: int
    segment_id: int
    relevance_score: float = 0.0
    is_enabled: bool = True


class DocumentSegmentResponse(DocumentSegmentBase):
    """文档分段响应"""
    id: int
    document_title: Optional[str] = None
    segment_content: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[str] = None

    class Config:
        from_attributes = True


class QuestionResponse(QuestionBase):
    """问题响应"""
    id: int
    assistant_id: int
    created_at: datetime
    updated_at: datetime
    views_count: int
    enabled: bool
    document_segments: Optional[List[DocumentSegmentResponse]] = None

    class Config:
        from_attributes = True


class QuestionList(BaseModel):
    """问题列表响应"""
    items: List[QuestionResponse]
    total: int


# 设置相关模式
class AnswerSettingsUpdate(BaseModel):
    """回答设置更新请求"""
    answer_mode: str
    use_cache: bool


class DocumentSegmentSettingsUpdate(BaseModel):
    """文档分段设置更新请求"""
    segment_ids: List[int]  # 启用的文档分段ID列表
