"""
助手相关数据模型
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import Field, validator
from app.schemas.assistants.base import BaseRequest, BaseResponse, PaginatedResponse


class AssistantCreateRequest(BaseRequest):
    """创建助手请求"""
    name: str = Field(..., min_length=1, max_length=100, description="助手名称")
    description: Optional[str] = Field(None, max_length=500, description="助手描述")
    model: str = Field(..., description="使用的AI模型")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="系统提示词")
    capabilities: Optional[List[str]] = Field(default=[], description="助手能力")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    tags: Optional[List[str]] = Field(default=[], description="标签")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    is_public: bool = Field(False, description="是否公开")
    config: Optional[Dict[str, Any]] = Field(default={}, description="配置信息")


class AssistantUpdateRequest(BaseRequest):
    """更新助手请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = None
    system_prompt: Optional[str] = Field(None, max_length=2000)
    capabilities: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    avatar_url: Optional[str] = None
    is_public: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class AssistantResponse(BaseResponse):
    """助手响应"""
    id: int
    name: str
    description: Optional[str]
    model: str
    system_prompt: Optional[str]
    capabilities: List[str]
    category: Optional[str]
    tags: List[str]
    avatar_url: Optional[str]
    is_public: bool
    config: Dict[str, Any]
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # 额外字段
    knowledge_base_ids: Optional[List[int]] = None
    stats: Optional[Dict[str, Any]] = None


class AssistantListResponse(PaginatedResponse):
    """助手列表响应"""
    items: List[AssistantResponse]


class AssistantSearchRequest(BaseRequest):
    """搜索助手请求"""
    query: Optional[str] = Field(None, description="搜索关键词")
    category: Optional[str] = Field(None, description="分类筛选")
    capabilities: Optional[List[str]] = Field(None, description="能力筛选")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    is_public: Optional[bool] = Field(None, description="公开性筛选")
    skip: int = Field(0, ge=0, description="跳过条数")
    limit: int = Field(20, ge=1, le=100, description="返回条数")