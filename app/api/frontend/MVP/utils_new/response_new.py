"""
统一响应格式
"""

from app.schemas.knowledge_base import BaseResponse
from datetime import datetime

def success_response(data=None, message="操作成功") -> BaseResponse:
    """成功响应"""
    return BaseResponse(
        success=True,
        message=message,
        data=data,
        error=None,
        timestamp=datetime.now()
    )

def error_response(error: str, message="操作失败") -> BaseResponse:
    """错误响应"""
    return BaseResponse(
        success=False,
        message=message,
        data=None,
        error=error,
        timestamp=datetime.now()
    )