"""
基础数据模型
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict, List
from datetime import datetime, UTC


class BaseRequest(BaseModel):
    """基础请求模型"""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class BaseResponse(BaseModel):
    """基础响应模型"""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class PaginatedResponse(BaseResponse):
    """分页响应基类"""
    items: List[Any]
    total: int = Field(ge=0)
    skip: int = Field(ge=0, default=0)
    limit: int = Field(ge=1, le=100, default=20)


class APIResponse(BaseResponse):
    """统一API响应格式"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))