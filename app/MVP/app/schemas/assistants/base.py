"""
基础数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime


class BaseRequest(BaseModel):
    """基础请求模型"""
    class Config:
        orm_mode = True
        use_enum_values = True


class BaseResponse(BaseModel):
    """基础响应模型"""
    class Config:
        orm_mode = True
        use_enum_values = True


class PaginatedResponse(BaseResponse):
    """分页响应基类"""
    items: List[Any]
    total: int
    skip: int
    limit: int


class APIResponse(BaseResponse):
    """统一API响应格式"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)