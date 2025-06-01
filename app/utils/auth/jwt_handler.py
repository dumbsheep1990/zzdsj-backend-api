"""
认证工具模块: 提供用户认证和授权功能
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import uuid

from app.models.user import User, Role, Permission
from app.utils.core.database import get_db
from app.config import settings

# 密码上下文，用于密码哈希和验证
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2认证方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# JWT配置
SECRET_KEY = settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else "23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0"
ALGORITHM = settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES if hasattr(settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES') else 30
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS if hasattr(settings, 'JWT_REFRESH_TOKEN_EXPIRE_DAYS') else 7

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def get_user(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def authenticate_user_by_email(db: Session, email: str, password: str) -> Optional[User]:
    """通过邮箱验证用户"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise credentials_exception
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(status_code=400, detail="用户已禁用")
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="用户已禁用")
    return current_user

def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """获取当前超级管理员用户"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user

def validate_refresh_token(db: Session, token: str) -> Dict[str, Any]:
    """验证刷新令牌"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的刷新令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise credentials_exception
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(status_code=400, detail="用户已禁用")
    return {"user_id": user_id, "user": user}

def has_permission(user: User, permission_code: str) -> bool:
    """检查用户是否具有特定权限"""
    if user.is_superuser:
        return True
    
    for role in user.roles:
        for permission in role.permissions:
            if permission.code == permission_code:
                return True
    return False

def require_permission(permission_code: str):
    """权限要求依赖"""
    def dependency(current_user: User = Depends(get_current_user)):
        if not has_permission(current_user, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要 {permission_code} 权限"
            )
        return current_user
    return dependency

def create_api_key(db: Session, user_id: str, name: str = None, description: str = None) -> str:
    """为用户创建API密钥"""
    from app.models.user import ApiKey

    # 生成随机API密钥
    api_key = f"zz_{uuid.uuid4().hex}"
    
    # 创建API密钥记录
    db_api_key = ApiKey(
        user_id=user_id,
        key=api_key,
        name=name or "默认API密钥",
        description=description or "自动生成的API密钥",
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return api_key

def verify_api_key(db: Session, api_key: str) -> Optional[User]:
    """验证API密钥并返回关联用户"""
    from app.models.user import ApiKey
    
    db_api_key = db.query(ApiKey).filter(ApiKey.key == api_key, ApiKey.is_active == True).first()
    if not db_api_key:
        return None
    
    # 更新最后使用时间
    db_api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    # 检查过期时间
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        return None
    
    # 获取关联用户
    user = get_user_by_id(db, db_api_key.user_id)
    if not user or user.disabled:
        return None
    
    return user
