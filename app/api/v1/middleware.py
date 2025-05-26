"""
V1 API专用中间件
提供请求日志、响应格式化、错误处理等功能
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from datetime import datetime
from typing import Callable

from app.api.shared.responses import ExternalResponseFormatter
from app.api.shared.exceptions import APIBaseException

logger = logging.getLogger(__name__)


class V1RequestLoggingMiddleware(BaseHTTPMiddleware):
    """V1 API请求日志中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("v1_api")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()
        
        # 生成请求ID
        request_id = f"v1_{int(start_time * 1000)}"
        
        # 记录请求信息
        self.logger.info(
            f"V1 API请求开始: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            self.logger.info(
                f"V1 API请求完成: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s"
                }
            )
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"
            response.headers["X-API-Version"] = "v1"
            
            return response
            
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录错误
            self.logger.error(
                f"V1 API请求异常: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "process_time": f"{process_time:.3f}s"
                },
                exc_info=True
            )
            
            # 返回统一的错误响应
            if isinstance(e, APIBaseException):
                return JSONResponse(
                    content={
                        "status": "error",
                        "message": e.message,
                        "code": e.code,
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id
                    },
                    status_code=e.status_code,
                    headers={
                        "X-Request-ID": request_id,
                        "X-Process-Time": f"{process_time:.3f}s",
                        "X-API-Version": "v1"
                    }
                )
            else:
                return JSONResponse(
                    content={
                        "status": "error",
                        "message": "服务器内部错误",
                        "code": "internal_server_error",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id
                    },
                    status_code=500,
                    headers={
                        "X-Request-ID": request_id,
                        "X-Process-Time": f"{process_time:.3f}s",
                        "X-API-Version": "v1"
                    }
                )


class V1ResponseFormattingMiddleware(BaseHTTPMiddleware):
    """V1 API响应格式化中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 只处理JSON响应
        if (response.headers.get("content-type", "").startswith("application/json") and
            response.status_code == 200):
            
            # 确保响应包含V1 API的标准格式
            # 这里可以添加额外的格式化逻辑
            pass
        
        return response


class V1CORSMiddleware(BaseHTTPMiddleware):
    """V1 API跨域中间件"""
    
    def __init__(self, app: ASGIApp, allowed_origins: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 处理预检请求
        if request.method == "OPTIONS":
            return JSONResponse(
                content={},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With",
                    "Access-Control-Max-Age": "3600"
                }
            )
        
        response = await call_next(request)
        
        # 添加CORS头
        origin = request.headers.get("origin")
        if origin and (self.allowed_origins == ["*"] or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Process-Time, X-API-Version"
        
        return response


class V1SecurityMiddleware(BaseHTTPMiddleware):
    """V1 API安全中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 添加安全头
        response = await call_next(request)
        
        # 基本安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # API特定安全头
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response


class V1RateLimitMiddleware(BaseHTTPMiddleware):
    """V1 API限流中间件（配合依赖注入使用）"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("v1_rate_limit")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 限流逻辑主要在dependencies中实现
        # 这里可以添加额外的限流日志记录
        
        try:
            response = await call_next(request)
            
            # 如果是429状态码，记录限流日志
            if response.status_code == 429:
                self.logger.warning(
                    f"V1 API限流触发: {request.method} {request.url.path}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": request.client.host if request.client else "unknown",
                        "user_agent": request.headers.get("user-agent", "unknown")
                    }
                )
            
            return response
            
        except Exception as e:
            # 传递异常给上层中间件处理
            raise e


def setup_v1_middleware(app):
    """
    为FastAPI应用设置V1 API中间件
    
    Args:
        app: FastAPI应用实例
    """
    # 按照执行顺序添加中间件（后添加的先执行）
    
    # 1. 安全中间件（最外层）
    app.add_middleware(V1SecurityMiddleware)
    
    # 2. CORS中间件
    app.add_middleware(V1CORSMiddleware)
    
    # 3. 限流中间件
    app.add_middleware(V1RateLimitMiddleware)
    
    # 4. 响应格式化中间件
    app.add_middleware(V1ResponseFormattingMiddleware)
    
    # 5. 请求日志中间件（最内层）
    app.add_middleware(V1RequestLoggingMiddleware)
    
    logger.info("V1 API中间件设置完成")
