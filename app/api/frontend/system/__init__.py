"""
系统模块：提供系统设置、配置管理和系统状态监控等功能
"""

from fastapi import APIRouter

from app.api.frontend.system import settings

# 创建系统模块路由
router = APIRouter()

# 注册子路由
router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
