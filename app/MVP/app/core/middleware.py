"""
自定义中间件
"""
import asyncio
from fastapi import Request, Response, Header, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from typing import Callable
import time
import logging
import uuid
import contextlib
from datetime import UTC, datetime

from app.config import get_settings
from app.core.assistants.exceptions import BaseAssistantError

logger = logging.getLogger(__name__)
settings = get_settings()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取或生成请求ID (支持从Header传入)
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.state.request_id = request_id

        # 结构化日志
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get('user-agent')
        }

        # 使用上下文管理器确保异常时也能记录
        with self._log_request_context(log_data):
            # 添加高精度计时器
            with self._measure_time() as timer:
                response = await call_next(request)
                process_time = timer()

            # 添加响应头
            response.headers.update({
                "X-Request-ID": request_id,
                "X-Process-Time": f"{process_time:.4f}",
                "X-Server-Timestamp": datetime.now(UTC).isoformat()
            })

            return response

    @contextlib.contextmanager
    def _log_request_context(self, log_data: dict):
        """请求日志上下文"""
        logger.info("Request started", extra={"data": log_data})
        try:
            yield
        except Exception as e:
            log_data.update({"error": str(e), "status": "failed"})
            logger.error("Request failed", extra={"data": log_data})
            raise
        else:
            log_data["status"] = "completed"
            logger.info("Request completed", extra={"data": log_data})

    @contextlib.contextmanager
    def _measure_time(self):
        """高精度计时器"""
        start = time.perf_counter()
        yield lambda: time.perf_counter() - start


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 可配置的客户端标识
        client_id = self._get_client_id(request)
        window_key = self._get_window_key()

        async with self._lock:  # 防止竞态条件
            # 定期清理（非每次请求都检查）
            if time.monotonic() - self._last_cleanup > 300:  # 5分钟清理一次
                self._cleanup_expired()
                self._last_cleanup = time.monotonic()

            # 计数
            current = self.rate_limits[window_key].get(client_id, 0) + 1
            self.rate_limits[window_key][client_id] = current

            # 检查限流
            if current > settings.RATE_LIMIT_PER_MINUTE:
                return self._rate_limit_response(request)

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """可扩展的客户端标识"""
        if settings.RATE_LIMIT_BY_API_KEY:
            return request.headers.get('X-API-Key', 'unknown')
        return request.client.host if request.client else 'unknown'

    def _get_window_key(self) -> int:
        """时间窗口键（每分钟一个窗口）"""
        return int(time.time() // 60)

    def _cleanup_expired(self):
        """清理过期窗口（保留最近5个窗口）"""
        current_window = self._get_window_key()
        expired = [k for k in self.rate_limits if k < current_window - 5]
        for k in expired:
            self.rate_limits.pop(k, None)

    def _rate_limit_response(self, request: Request) -> JSONResponse:
        """标准化的限流响应"""
        retry_after = 60 - (time.time() % 60)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "message": "请求过于频繁",
                "code": "rate_limit_exceeded",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(int(retry_after))}
        )
    
    
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        
        except RequestValidationError as e:
            return self._handle_validation_error(e, request)
            
        except BaseAssistantError as e:
            return self._handle_business_error(e, request)
            
        except Exception as e:
            return self._handle_unexpected_error(e, request)

    def _handle_validation_error(self, e: RequestValidationError, request: Request) -> JSONResponse:
        """处理请求验证错误"""
        logger.warning(
            "Validation error",
            extra={
                "error": str(e),
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path
            }
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "请求参数无效",
                "errors": e.errors(),
                "code": "validation_error"
            }
        )

    def _handle_business_error(self, e: BaseAssistantError, request: Request) -> JSONResponse:
        """处理业务异常"""
        logger.error(
            f"Business error: {e.code}",
            extra={
                "error": e.message,
                "code": e.code,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
        return JSONResponse(
            status_code=e.status_code or 400,
            content=e.to_dict()
        )

    def _handle_unexpected_error(self, e: Exception, request: Request) -> JSONResponse:
        """处理未预期异常"""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.critical(
            f"Unexpected error [{request_id}]: {str(e)}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "内部服务器错误",
                "request_id": request_id,
                "code": "internal_error"
            }
        )