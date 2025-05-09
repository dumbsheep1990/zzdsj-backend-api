"""
API中间件
提供统一的异常处理和请求响应格式化
"""

import time
import logging
import traceback
from typing import Dict, Any, Callable
from fastapi import Request, Response, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.dependencies import ResponseFormatter

logger = logging.getLogger(__name__)


class APIMiddleware(BaseHTTPMiddleware):
    """API中间件，处理请求前后的通用逻辑"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 记录请求开始时间
        start_time = time.time()
        request.state.start_time = start_time
        
        # 生成请求ID
        request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")
        request.state.request_id = request_id
        
        try:
            # 调用下一个中间件或路由处理器
            response = await call_next(request)
            
            # 添加请求处理时间和请求ID到响应头
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as exc:
            # 处理未捕获的异常
            logger.error(f"未处理的异常: {str(exc)}")
            logger.error(traceback.format_exc())
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ResponseFormatter.format_error(
                    message="服务器内部错误",
                    code="internal_server_error"
                )
            )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理HTTP异常"""
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseFormatter.format_error(
            message=exc.detail,
            code=f"http_{exc.status_code}",
            status_code=exc.status_code
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求验证异常"""
    errors = exc.errors()
    error_details = []
    
    for error in errors:
        error_details.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"请求验证错误: {error_details}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseFormatter.format_error(
            message="请求数据验证失败",
            code="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    )


def setup_middlewares(app: FastAPI) -> None:
    """设置中间件"""
    # 添加全局中间件
    app.add_middleware(APIMiddleware)
    
    # 注册异常处理器
    app.exception_handler(HTTPException)(http_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
