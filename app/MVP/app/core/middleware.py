"""
自定义中间件
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging
import uuid
from datetime import datetime

from app.config import get_settings
from app.core.assistants.exceptions import BaseAssistantError

logger = logging.getLogger(__name__)
settings = get_settings()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求开始
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"[ID: {request_id}]"
        )

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # 记录请求完成
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"[ID: {request_id}] "
            f"Status: {response.status_code} "
            f"Time: {process_time:.3f}s"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = {}  # 简单的内存存储，生产环境应使用Redis

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取客户端标识（这里使用IP，实际可能需要用户ID）
        client_id = request.client.host if request.client else "unknown"

        # 获取当前时间窗口
        current_minute = datetime.now().strftime("%Y-%m-%d-%H-%M")
        key = f"{client_id}:{current_minute}"

        # 检查限流
        if key not in self.rate_limits:
            self.rate_limits[key] = 0

        self.rate_limits[key] += 1

        if self.rate_limits[key] > settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "请求过于频繁，请稍后再试",
                    "error": "RATE_LIMIT_EXCEEDED"
                }
            )

        # 清理过期的限流记录（简单实现）
        if len(self.rate_limits) > 10000:
            self.rate_limits.clear()

        response = await call_next(request)
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except BaseAssistantError as e:
            # 处理自定义异常
            logger.error(f"Business error: {e.code} - {e.message}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": e.message,
                    "error": e.code,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            # 处理未预期的异常
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"Unexpected error [ID: {request_id}]: {str(e)}",
                exc_info=True
            )

            # 生产环境不应暴露详细错误信息
            if settings.DEBUG:
                error_detail = str(e)
            else:
                error_detail = "内部服务器错误"

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "服务器处理请求时发生错误",
                    "error": error_detail,
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )