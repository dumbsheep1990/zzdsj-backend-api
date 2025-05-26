"""
API共享响应格式化系统
提供双层API架构的统一响应格式和差异化处理
"""

from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from fastapi.responses import JSONResponse
from fastapi import status
from pydantic import BaseModel, Field
from datetime import datetime
import traceback
import logging

logger = logging.getLogger(__name__)


class BaseResponseModel(BaseModel):
    """基础响应模型"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="响应时间戳")
    request_id: Optional[str] = Field(None, description="请求ID")


class BaseResponseFormatter(ABC):
    """
    基础响应格式化器抽象类
    定义响应格式化的基本接口
    """
    
    @staticmethod
    @abstractmethod
    def success(
        data: Any = None,
        message: str = "success",
        **kwargs
    ) -> JSONResponse:
        """创建成功响应"""
        pass
    
    @staticmethod
    @abstractmethod
    def error(
        message: str,
        code: str = "error",
        **kwargs
    ) -> JSONResponse:
        """创建错误响应"""
        pass
    
    @staticmethod
    @abstractmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        **kwargs
    ) -> JSONResponse:
        """创建分页响应"""
        pass


class ExternalResponseFormatter(BaseResponseFormatter):
    """
    对外API响应格式化器
    简化的、用户友好的响应格式
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "success",
        request_id: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        **kwargs
    ) -> JSONResponse:
        """
        创建对外API成功响应
        
        格式：
        {
            "status": "success",
            "data": {...},
            "message": "success",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        response_data = {
            "status": "success",
            "data": data,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if request_id:
            response_data["request_id"] = request_id
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    @staticmethod
    def error(
        message: str,
        code: str = "error",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs
    ) -> JSONResponse:
        """
        创建对外API错误响应
        
        格式：
        {
            "status": "error",
            "message": "错误描述",
            "code": "error_code",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        response_data = {
            "status": "error",
            "message": message,
            "code": code,
            "timestamp": datetime.now().isoformat()
        }
        
        # 对外API不暴露详细错误信息，只在必要时包含基本details
        if details and isinstance(details, dict):
            # 过滤敏感信息
            safe_details = {
                k: v for k, v in details.items() 
                if k in ["field", "validation_errors", "invalid_value"]
            }
            if safe_details:
                response_data["details"] = safe_details
        
        if request_id:
            response_data["request_id"] = request_id
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    @staticmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "success",
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """
        创建对外API分页响应
        
        格式：
        {
            "status": "success",
            "data": [...],
            "pagination": {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "has_next": true,
                "has_prev": false
            },
            "message": "success",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        
        response_data = {
            "status": "success",
            "data": data,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if request_id:
            response_data["request_id"] = request_id
        
        return JSONResponse(
            content=response_data,
            status_code=status.HTTP_200_OK
        )
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "创建成功",
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """创建资源成功响应"""
        return ExternalResponseFormatter.success(
            data=data,
            message=message,
            request_id=request_id,
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def not_found(
        message: str = "资源不存在",
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """资源不存在响应"""
        return ExternalResponseFormatter.error(
            message=message,
            code="not_found",
            request_id=request_id,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def unauthorized(
        message: str = "认证失败",
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """认证失败响应"""
        return ExternalResponseFormatter.error(
            message=message,
            code="unauthorized",
            request_id=request_id,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(
        message: str = "权限不足",
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """权限不足响应"""
        return ExternalResponseFormatter.error(
            message=message,
            code="forbidden",
            request_id=request_id,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def rate_limited(
        message: str = "请求过于频繁",
        retry_after: Optional[int] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """限流响应"""
        response = ExternalResponseFormatter.error(
            message=message,
            code="rate_limited",
            request_id=request_id,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
        
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        
        return response


class InternalResponseFormatter(BaseResponseFormatter):
    """
    内部API响应格式化器
    详细的、管理员友好的响应格式
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        include_server_info: bool = True,
        **kwargs
    ) -> JSONResponse:
        """
        创建内部API成功响应
        
        格式：
        {
            "success": true,
            "data": {...},
            "message": "操作成功",
            "metadata": {...},
            "timestamp": "2024-01-01T00:00:00Z",
            "request_id": "uuid",
            "server_info": {
                "version": "1.0.0",
                "environment": "production"
            }
        }
        """
        response_data = {
            "success": True,
            "data": data,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response_data["metadata"] = metadata
        
        if request_id:
            response_data["request_id"] = request_id
        
        if include_server_info:
            try:
                from app.config import settings
                response_data["server_info"] = {
                    "version": getattr(settings, "VERSION", "1.0.0"),
                    "environment": getattr(settings, "ENVIRONMENT", "unknown")
                }
            except Exception:
                pass
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    @staticmethod
    def error(
        message: str,
        code: str = "error",
        details: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        request_id: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        include_debug_info: bool = True,
        **kwargs
    ) -> JSONResponse:
        """
        创建内部API错误响应
        
        格式：
        {
            "success": false,
            "error": {
                "message": "错误描述",
                "code": "error_code",
                "details": {...},
                "stack_trace": "..." // 仅在debug模式
            },
            "timestamp": "2024-01-01T00:00:00Z",
            "request_id": "uuid"
        }
        """
        error_data = {
            "message": message,
            "code": code
        }
        
        if details:
            error_data["details"] = details
        
        # 内部API可以包含详细错误信息
        if stack_trace and include_debug_info:
            try:
                from app.config import settings
                if getattr(settings, "DEBUG", False):
                    error_data["stack_trace"] = stack_trace
            except Exception:
                pass
        
        response_data = {
            "success": False,
            "error": error_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if request_id:
            response_data["request_id"] = request_id
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    @staticmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功",
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """
        创建内部API分页响应
        
        格式：
        {
            "success": true,
            "data": [...],
            "pagination": {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "has_next": true,
                "has_prev": false,
                "start_index": 1,
                "end_index": 20
            },
            "message": "查询成功",
            "metadata": {...},
            "timestamp": "2024-01-01T00:00:00Z",
            "request_id": "uuid"
        }
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        start_index = (page - 1) * page_size + 1 if total > 0 else 0
        end_index = min(page * page_size, total)
        
        pagination_info = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "start_index": start_index,
            "end_index": end_index
        }
        
        response_metadata = {"pagination": pagination_info}
        if metadata:
            response_metadata.update(metadata)
        
        return InternalResponseFormatter.success(
            data=data,
            message=message,
            metadata=response_metadata,
            request_id=request_id
        )
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "创建成功",
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """创建资源成功响应"""
        return InternalResponseFormatter.success(
            data=data,
            message=message,
            metadata=metadata,
            request_id=request_id,
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def updated(
        data: Any = None,
        message: str = "更新成功",
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """更新资源成功响应"""
        return InternalResponseFormatter.success(
            data=data,
            message=message,
            metadata=metadata,
            request_id=request_id,
            status_code=status.HTTP_200_OK
        )
    
    @staticmethod
    def deleted(
        message: str = "删除成功",
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> JSONResponse:
        """删除资源成功响应"""
        return InternalResponseFormatter.success(
            data=None,
            message=message,
            metadata=metadata,
            request_id=request_id,
            status_code=status.HTTP_200_OK
        )


class StreamingResponseFormatter:
    """
    流式响应格式化器
    用于处理流式数据响应
    """
    
    @staticmethod
    def format_stream_chunk(
        data: Any,
        chunk_type: str = "data",
        request_id: Optional[str] = None,
        api_type: str = "external"
    ) -> str:
        """
        格式化流式响应块 (SSE格式)
        
        Args:
            data: 数据块
            chunk_type: 块类型 (data, error, end)
            request_id: 请求ID
            api_type: API类型 (external/internal)
            
        Returns:
            str: 格式化的SSE数据
        """
        import json
        
        if api_type == "external":
            # 对外API - 简化格式
            chunk_data = {
                "type": chunk_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 内部API - 详细格式
            chunk_data = {
                "type": chunk_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "chunk_id": f"chunk_{int(datetime.now().timestamp() * 1000)}"
                }
            }
        
        if request_id:
            chunk_data["request_id"] = request_id
        
        return f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
    
    @staticmethod
    def format_error_chunk(
        message: str,
        code: str = "stream_error",
        request_id: Optional[str] = None,
        api_type: str = "external"
    ) -> str:
        """格式化流式错误块"""
        error_data = {
            "message": message,
            "code": code
        }
        
        return StreamingResponseFormatter.format_stream_chunk(
            data=error_data,
            chunk_type="error",
            request_id=request_id,
            api_type=api_type
        )
    
    @staticmethod
    def format_end_chunk(
        request_id: Optional[str] = None,
        api_type: str = "external"
    ) -> str:
        """格式化流式结束块"""
        return StreamingResponseFormatter.format_stream_chunk(
            data=None,
            chunk_type="end",
            request_id=request_id,
            api_type=api_type
        )


# 异常响应处理

def handle_exception_response(
    exception: Exception,
    request_id: Optional[str] = None,
    api_type: str = "external",
    include_debug: bool = False
) -> JSONResponse:
    """
    统一异常响应处理
    
    Args:
        exception: 异常对象
        request_id: 请求ID
        api_type: API类型 (external/internal)
        include_debug: 是否包含调试信息
    
    Returns:
        JSONResponse: 格式化的异常响应
    """
    # 确定错误信息
    error_message = str(exception)
    error_code = type(exception).__name__.lower()
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # 根据异常类型确定状态码
    if hasattr(exception, 'status_code'):
        status_code = exception.status_code
    elif 'not found' in error_message.lower():
        status_code = status.HTTP_404_NOT_FOUND
        error_code = "not_found"
    elif 'unauthorized' in error_message.lower():
        status_code = status.HTTP_401_UNAUTHORIZED
        error_code = "unauthorized"
    elif 'forbidden' in error_message.lower():
        status_code = status.HTTP_403_FORBIDDEN
        error_code = "forbidden"
    
    # 记录异常日志
    logger.error(
        f"API异常 [{api_type}]: {error_code} - {error_message}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    # 根据API类型选择响应格式
    if api_type == "external":
        return ExternalResponseFormatter.error(
            message=error_message,
            code=error_code,
            request_id=request_id,
            status_code=status_code
        )
    else:
        details = {
            "exception_type": type(exception).__name__,
            "module": getattr(exception, '__module__', 'unknown')
        }
        
        stack_trace = None
        if include_debug:
            stack_trace = traceback.format_exc()
        
        return InternalResponseFormatter.error(
            message=error_message,
            code=error_code,
            details=details,
            stack_trace=stack_trace,
            request_id=request_id,
            status_code=status_code
        )


# 工厂函数

def get_response_formatter(api_type: str) -> Union[ExternalResponseFormatter, InternalResponseFormatter]:
    """
    根据API类型获取对应的响应格式化器
    
    Args:
        api_type: API类型 ("external" or "internal")
    
    Returns:
        对应的响应格式化器类
    """
    if api_type == "external":
        return ExternalResponseFormatter
    elif api_type == "internal":
        return InternalResponseFormatter
    else:
        # 默认使用对外API格式化器
        return ExternalResponseFormatter


# 响应装饰器

def format_api_response(api_type: str = "external"):
    """
    API响应格式化装饰器
    
    Args:
        api_type: API类型
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # 如果结果已经是JSONResponse，直接返回
                if isinstance(result, JSONResponse):
                    return result
                
                # 获取请求ID（如果在kwargs中）
                request_id = kwargs.get('request_id')
                
                # 格式化为成功响应
                formatter = get_response_formatter(api_type)
                return formatter.success(
                    data=result,
                    request_id=request_id
                )
            except Exception as e:
                # 获取请求ID
                request_id = kwargs.get('request_id')
                
                # 格式化异常响应
                return handle_exception_response(
                    exception=e,
                    request_id=request_id,
                    api_type=api_type,
                    include_debug=(api_type == "internal")
                )
        
        return wrapper
    return decorator 