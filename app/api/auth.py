"""
认证路由模块: 提供登录、注册和令牌刷新等功能
"""

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
    verify_password,
    create_api_key
)
from app.schemas.user import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
    Token,
    Login,
    RefreshToken,
    PasswordUpdate,
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKey,
    ApiKeyWithValue
)
from app.models.user import User, UserSettings, ApiKey as ApiKeyModel

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
    # 检查用户名是否已存在
    db_user_by_username = db.query(User).filter(User.username == user_in.username).first()
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用",
        )
    
    # 检查邮箱是否已存在
    db_user_by_email = db.query(User).filter(User.email == user_in.email).first()
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
    )
    
    # 添加默认角色
    from app.models.user import Role
    default_role = db.query(Role).filter(Role.is_default == True).first()
    if default_role:
        db_user.roles.append(default_role)
    
    db.add(db_user)
    db.commit()
    
    # 创建用户设置
    db_settings = UserSettings(
        user_id=db_user.id,
    )
    db.add(db_settings)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: Login, db: Session = Depends(get_db)) -> Any:
    """
    获取访问令牌
    """
    # 首先尝试用用户名登录
    user = authenticate_user(db, form_data.username, form_data.password)
    
    # 如果失败，尝试用邮箱登录
    if not user:
        user = authenticate_user_by_email(db, form_data.username, form_data.password)
    
    # 如果两种方式都失败
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名/邮箱或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 如果用户被禁用
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用",
        )
    
    # 生成访问令牌和刷新令牌
    access_token_expires = timedelta(minutes=30)
    refresh_token_expires = timedelta(days=7)
    
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id}, expires_delta=refresh_token_expires
    )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds(),
    }

@router.post("/refresh", response_model=Token)
def refresh_access_token(refresh_token_in: RefreshToken, db: Session = Depends(get_db)) -> Any:
    """
    使用刷新令牌获取新的访问令牌
    """
    # 验证刷新令牌
    token_data = validate_refresh_token(db, refresh_token_in.refresh_token)
    user = token_data["user"]
    
    # 生成新的访问令牌和刷新令牌
    access_token_expires = timedelta(minutes=30)
    refresh_token_expires = timedelta(days=7)
    
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id}, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds(),
    }

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    获取当前登录用户信息
    """
    return current_user
