# MVP/main.py
"""
在应用初始化时注册错误处理器
"""
from fastapi import FastAPI
from app.api.frontend.error_handlers import (
    app_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.core.exceptions import BaseAppException

def setup_error_handlers(app: FastAPI):
    """设置错误处理器"""
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.settings import settings
from app.api.frontend.assistants import router as assistants_router
from app.db.base import Base, engine
from app.auth.dependencies import get_current_user  # 可选，根据需要引入

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="智能问答系统", version="1.0")

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(assistants_router, prefix="/api/assistants")

# 数据库初始化（启动时创建表，生产环境建议用Alembic）
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)