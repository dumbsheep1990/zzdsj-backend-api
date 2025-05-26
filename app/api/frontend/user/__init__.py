"""
用户模块：提供用户认证、资料管理、设置、偏好和API密钥等功能
"""

from fastapi import APIRouter

from app.api.frontend.user import auth, profile, settings, preferences, api_key, manage

# 创建用户模块路由
router = APIRouter()

# 注册子路由
router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
router.include_router(profile.router, prefix="/profile", tags=["用户资料"])
router.include_router(settings.router, prefix="/settings", tags=["用户设置"])
router.include_router(preferences.router, prefix="/preferences", tags=["个性化偏好"])
router.include_router(api_key.router, prefix="/api-keys", tags=["API密钥管理"])
router.include_router(manage.router, prefix="", tags=["用户管理"]) # 使用空前缀，保持原始路径 