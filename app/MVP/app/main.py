"""
应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings, logger
from app.api.v1.assistants.routes import register_assistant_routes
from app.core.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlerMiddleware
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 启动时的初始化操作
    # TODO: 初始化数据库连接池、缓存等

    yield

    # 关闭时的清理操作
    logger.info("Shutting down application")
    # TODO: 关闭数据库连接、清理资源等


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 注册路由
app.include_router(
    register_assistant_routes(),
    prefix=settings.API_V1_PREFIX
)


# 健康检查端点
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )