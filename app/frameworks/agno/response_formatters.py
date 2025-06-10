"""
ZZDSJ Agno响应格式化器

统一API响应格式，支持：
- 标准JSON响应格式
- 错误响应格式
- 流式响应格式
- 分页响应格式
- 监控和指标响应格式

Phase 3: API层适配的响应格式组件
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import uuid

from fastapi import status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorType(Enum):
    """错误类型枚举"""
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
    AGNO_ERROR = "agno_error"
    LEGACY_FALLBACK = "legacy_fallback"


@dataclass
class ResponseMetadata:
    """响应元数据"""
    timestamp: str
    request_id: str
    processing_time_ms: Optional[float] = None
    agno_enabled: bool = True
    fallback_used: bool = False
    cache_hit: bool = False
    rate_limit_remaining: Optional[int] = None


@dataclass
class PaginationInfo:
    """分页信息"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class StandardResponse(BaseModel):
    """标准响应格式"""
    status: ResponseStatus
    message: str
    data: Any = None
    metadata: ResponseMetadata
    error: Optional[Dict[str, Any]] = None
    pagination: Optional[PaginationInfo] = None


class ErrorDetail(BaseModel):
    """错误详情"""
    type: ErrorType
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class ZZDSJResponseFormatter:
    """ZZDSJ响应格式化器"""
    
    def __init__(self):
        """初始化响应格式化器"""
        self.default_headers = {
            "X-Powered-By": "ZZDSJ-Agno",
            "X-API-Version": "v1.0.0"
        }
        
        logger.info("ZZDSJ响应格式化器已初始化")
    
    def create_success_response(self,
                              data: Any = None,
                              message: str = "操作成功",
                              request_id: str = None,
                              processing_time_ms: float = None,
                              agno_enabled: bool = True,
                              fallback_used: bool = False,
                              cache_hit: bool = False,
                              pagination: PaginationInfo = None,
                              additional_headers: Dict[str, str] = None) -> JSONResponse:
        """创建成功响应"""
        
        metadata = ResponseMetadata(
            timestamp=datetime.now().isoformat(),
            request_id=request_id or str(uuid.uuid4()),
            processing_time_ms=processing_time_ms,
            agno_enabled=agno_enabled,
            fallback_used=fallback_used,
            cache_hit=cache_hit
        )
        
        response_data = {
            "status": ResponseStatus.SUCCESS.value,
            "message": message,
            "data": data,
            "metadata": {
                "timestamp": metadata.timestamp,
                "request_id": metadata.request_id,
                "processing_time_ms": metadata.processing_time_ms,
                "agno_enabled": metadata.agno_enabled,
                "fallback_used": metadata.fallback_used,
                "cache_hit": metadata.cache_hit
            }
        }
        
        if pagination:
            response_data["pagination"] = {
                "page": pagination.page,
                "page_size": pagination.page_size,
                "total_items": pagination.total_items,
                "total_pages": pagination.total_pages,
                "has_next": pagination.has_next,
                "has_previous": pagination.has_previous
            }
        
        headers = {**self.default_headers}
        if additional_headers:
            headers.update(additional_headers)
        
        headers["X-Request-ID"] = metadata.request_id
        if processing_time_ms:
            headers["X-Processing-Time-MS"] = str(processing_time_ms)
        if agno_enabled:
            headers["X-Agno-Enabled"] = "true"
        if fallback_used:
            headers["X-Fallback-Used"] = "true"
        if cache_hit:
            headers["X-Cache-Hit"] = "true"
        
        return JSONResponse(
            content=response_data,
            status_code=status.HTTP_200_OK,
            headers=headers
        )
    
    def create_error_response(self,
                            error_type: ErrorType,
                            error_code: str,
                            message: str,
                            details: Dict[str, Any] = None,
                            stack_trace: str = None,
                            request_id: str = None,
                            processing_time_ms: float = None,
                            agno_enabled: bool = True,
                            fallback_used: bool = False,
                            additional_headers: Dict[str, str] = None) -> JSONResponse:
        """创建错误响应"""
        
        metadata = ResponseMetadata(
            timestamp=datetime.now().isoformat(),
            request_id=request_id or str(uuid.uuid4()),
            processing_time_ms=processing_time_ms,
            agno_enabled=agno_enabled,
            fallback_used=fallback_used
        )
        
        error_detail = {
            "type": error_type.value,
            "code": error_code,
            "message": message,
            "details": details,
            "stack_trace": stack_trace
        }
        
        response_data = {
            "status": ResponseStatus.ERROR.value,
            "message": message,
            "metadata": {
                "timestamp": metadata.timestamp,
                "request_id": metadata.request_id,
                "processing_time_ms": metadata.processing_time_ms,
                "agno_enabled": metadata.agno_enabled,
                "fallback_used": metadata.fallback_used
            },
            "error": error_detail
        }
        
        # 根据错误类型确定HTTP状态码
        http_status = self._get_http_status_for_error(error_type)
        
        headers = {**self.default_headers}
        if additional_headers:
            headers.update(additional_headers)
        
        headers["X-Request-ID"] = metadata.request_id
        if processing_time_ms:
            headers["X-Processing-Time-MS"] = str(processing_time_ms)
        headers["X-Error-Type"] = error_type.value
        headers["X-Error-Code"] = error_code
        
        return JSONResponse(
            content=response_data,
            status_code=http_status,
            headers=headers
        )
    
    def create_streaming_response(self,
                                content_generator: AsyncGenerator[str, None],
                                media_type: str = "text/plain",
                                request_id: str = None,
                                agno_enabled: bool = True,
                                additional_headers: Dict[str, str] = None) -> StreamingResponse:
        """创建流式响应"""
        
        headers = {**self.default_headers}
        if additional_headers:
            headers.update(additional_headers)
        
        headers.update({
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id or str(uuid.uuid4()),
            "X-Stream-Enabled": "true"
        })
        
        if agno_enabled:
            headers["X-Agno-Enabled"] = "true"
        
        return StreamingResponse(
            content_generator,
            media_type=media_type,
            headers=headers
        )
    
    def _get_http_status_for_error(self, error_type: ErrorType) -> int:
        """根据错误类型获取HTTP状态码"""
        status_map = {
            ErrorType.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorType.AUTHENTICATION_ERROR: status.HTTP_401_UNAUTHORIZED,
            ErrorType.AUTHORIZATION_ERROR: status.HTTP_403_FORBIDDEN,
            ErrorType.NOT_FOUND_ERROR: status.HTTP_404_NOT_FOUND,
            ErrorType.RATE_LIMIT_ERROR: status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorType.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorType.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorType.AGNO_ERROR: status.HTTP_502_BAD_GATEWAY,
            ErrorType.LEGACY_FALLBACK: status.HTTP_200_OK  # 回退成功但有警告
        }
        
        return status_map.get(error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    async def format_agno_response(self,
                                 agno_response: Any,
                                 request_start_time: datetime,
                                 request_id: str = None,
                                 fallback_used: bool = False) -> JSONResponse:
        """格式化Agno响应"""
        
        processing_time = (datetime.now() - request_start_time).total_seconds() * 1000
        
        # 检查响应是否有success属性
        if hasattr(agno_response, 'success'):
            if agno_response.success:
                return self.create_success_response(
                    data=agno_response.data,
                    message=agno_response.message or "Agno处理成功",
                    request_id=request_id or agno_response.request_id,
                    processing_time_ms=processing_time,
                    agno_enabled=True,
                    fallback_used=fallback_used
                )
            else:
                return self.create_error_response(
                    error_type=ErrorType.AGNO_ERROR,
                    error_code=agno_response.error_code or "AGNO_PROCESSING_ERROR",
                    message=agno_response.message or "Agno处理失败",
                    request_id=request_id or agno_response.request_id,
                    processing_time_ms=processing_time,
                    agno_enabled=True,
                    fallback_used=fallback_used
                )
        else:
            # 直接响应数据
            return self.create_success_response(
                data=agno_response,
                message="处理成功",
                request_id=request_id,
                processing_time_ms=processing_time,
                agno_enabled=True,
                fallback_used=fallback_used
            )


# 全局响应格式化器实例
_response_formatter = None

def get_response_formatter() -> ZZDSJResponseFormatter:
    """获取全局响应格式化器实例"""
    global _response_formatter
    if _response_formatter is None:
        _response_formatter = ZZDSJResponseFormatter()
    return _response_formatter


# 便捷函数
def success_response(data: Any = None, message: str = "操作成功", **kwargs) -> JSONResponse:
    """创建成功响应（便捷函数）"""
    formatter = get_response_formatter()
    return formatter.create_success_response(data=data, message=message, **kwargs)


def error_response(error_type: ErrorType, 
                  error_code: str, 
                  message: str, 
                  **kwargs) -> JSONResponse:
    """创建错误响应（便捷函数）"""
    formatter = get_response_formatter()
    return formatter.create_error_response(
        error_type=error_type,
        error_code=error_code,
        message=message,
        **kwargs
    )


def streaming_response(content_generator: AsyncGenerator[str, None], 
                      **kwargs) -> StreamingResponse:
    """创建流式响应（便捷函数）"""
    formatter = get_response_formatter()
    return formatter.create_streaming_response(
        content_generator=content_generator,
        **kwargs
    )


# 响应格式示例
def example_responses():
    """响应格式示例"""
    formatter = get_response_formatter()
    
    # 成功响应示例
    success_resp = formatter.create_success_response(
        data={"result": "Hello from Agno!"},
        message="聊天响应生成成功"
    )
    
    # 错误响应示例
    error_resp = formatter.create_error_response(
        error_type=ErrorType.AGNO_ERROR,
        error_code="AGENT_CREATION_FAILED",
        message="代理创建失败"
    )
    
    logger.info("✅ 响应格式示例创建完成")
    
    return {
        "success": success_resp,
        "error": error_resp
    }


if __name__ == "__main__":
    # 运行示例
    examples = example_responses()
    logger.info("✅ ZZDSJ响应格式化器测试完成") 