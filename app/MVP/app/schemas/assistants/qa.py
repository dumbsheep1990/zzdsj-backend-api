"""
问答相关数据模型
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import Field
from app.schemas.assistants.base import BaseRequest, BaseResponse, PaginatedResponse


class QAAssistantCreateRequest(BaseRequest):
    """创建问答助手请求"""
    name: str = Field(..., min_length=1, max_length=100, description="助手名称")
    description: Optional[str] = Field(None, max_length=500, description="助手描述")
    type: str = Field("standard", description="助手类型")
    icon: Optional[str] = Field(None, description="图标")
    status: str = Field("active", description="状态")
    config: Optional[Dict[str, Any]] = Field(default={}, description="配置")
    knowledge_base_id: Optional[int] = Field(None, description="关联的知识库ID")


class QAAssistantUpdateRequest(BaseRequest):
    """更新问答助手请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class QAAssistantResponse(BaseResponse):
    """问答助手响应"""
    id: int
    name: str
    description: Optional[str]
    type: str
    icon: Optional[str]
    status: str
    config: Dict[str, Any]
    knowledge_base_id: Optional[int]
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    # 统计信息
    question_count: Optional[int] = None
    total_views: Optional[int] = None


class QuestionCreateRequest(BaseRequest):
    """创建问题请求"""
    assistant_id: int = Field(..., description="助手ID")
    question: str = Field(..., min_length=1, max_length=500, description="问题")
    answer: str = Field(..., min_length=1, max_length=5000, description="答案")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="元数据")


class QuestionUpdateRequest(BaseRequest):
    """更新问题请求"""
    question: Optional[str] = Field(None, min_length=1, max_length=500)
    answer: Optional[str] = Field(None, min_length=1, max_length=5000)
    category: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None


class QuestionResponse(BaseResponse):
    """问题响应"""
    id: int
    assistant_id: int
    question: str
    answer: str
    category: Optional[str]
    views_count: int
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]

    # 关联信息
    document_segments: Optional[List[Dict[str, Any]]] = None


class QuestionListResponse(PaginatedResponse):
    """问题列表响应"""
    items: List[QuestionResponse]


class AnswerSettingsRequest(BaseRequest):
    """答案设置请求"""
    answer_mode: Optional[str] = Field(None, description="回答模式")
    use_cache: Optional[bool] = Field(None, description="是否使用缓存")
    max_tokens: Optional[int] = Field(None, ge=1, le=10000, description="最大令牌数")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="温度参数")


class DocumentSegmentSettingsRequest(BaseRequest):
    """文档分段设置请求"""
    segment_ids: List[int] = Field(..., min_items=0, description="文档分段ID列表")


class QAStatisticsResponse(BaseResponse):
    """问答统计响应"""
    total_questions: int
    total_views: int
    categories: Dict[str, int]
    popular_questions: List[QuestionResponse]
    recent_questions: List[QuestionResponse]