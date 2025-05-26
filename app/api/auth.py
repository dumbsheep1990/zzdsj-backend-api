"""
认证路由模块: 提供登录、注册和令牌刷新等功能
(桥接文件 - 仅用于向后兼容，所有新代码都应该使用app.api.frontend.user.auth模块)
"""

import logging
from datetime import datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.utils.auth import (
    authenticate_user,
    authenticate_user_by_email,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    validate_refresh_token,
    get_password_hash,
    verify_password
)
from app.schemas.user import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
    Token,
    Login,
    RefreshToken,
    PasswordUpdate
)
from app.models.user import User, UserSettings

# 导入新的用户认证路由处理函数
from app.api.frontend.user.auth import (
    register_user as new_register_user,
    login_for_access_token as new_login_for_access_token,
    refresh_access_token as new_refresh_access_token,
    read_users_me as new_read_users_me,
    logout as new_logout
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["认证与授权"],
    responses={404: {"description": "未找到"}},
)

@router.post("/register", response_model=UserSchema)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    注册新用户
    """
    logger.warning(
        "使用已弃用的认证端点: /api/v1/auth/register，应使用新的端点: /api/frontend/user/auth/register"
    )
    return new_register_user(user_in=user_in, db=db)

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: Login, db: Session = Depends(get_db)) -> Any:
    """
    获取访问令牌
    """
    logger.warning(
        "使用已弃用的认证端点: /api/v1/auth/login，应使用新的端点: /api/frontend/user/auth/login"
    )
    return new_login_for_access_token(form_data=form_data, db=db)

@router.post("/refresh", response_model=Token)
def refresh_access_token(refresh_token_in: RefreshToken, db: Session = Depends(get_db)) -> Any:
    """
    使用刷新令牌获取新的访问令牌
    """
    logger.warning(
        "使用已弃用的认证端点: /api/v1/auth/refresh，应使用新的端点: /api/frontend/user/auth/refresh"
    )
    return new_refresh_access_token(refresh_token_in=refresh_token_in, db=db)

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    获取当前登录用户信息
    """
    logger.warning(
        "使用已弃用的认证端点: /api/v1/auth/me，应使用新的端点: /api/frontend/user/auth/me"
    )
    return new_read_users_me(current_user=current_user)

@router.post("/logout")
def logout() -> Any:
    """
    用户登出
    """
    logger.warning(
        "使用已弃用的认证端点: /api/v1/auth/logout，应使用新的端点: /api/frontend/user/auth/logout"
    )
    return new_logout()
