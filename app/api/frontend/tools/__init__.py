"""
工具模块：提供统一的工具管理和执行功能
"""

from fastapi import APIRouter

from app.api.frontend.tools import base
from app.api.frontend.tools import history
from app.api.frontend.tools import manager
from app.api.frontend.tools import unified
from app.api.frontend.tools import owl

# 创建工具模块路由
router = APIRouter()

# 注册子路由
router.include_router(base.router, prefix="/base", tags=["基础工具"])
router.include_router(history.router, prefix="/history", tags=["工具历史"])
router.include_router(manager.router, prefix="", tags=["工具管理"])
router.include_router(unified.router, prefix="/unified", tags=["统一工具"])
router.include_router(owl.router, prefix="/owl", tags=["OWL工具"])
