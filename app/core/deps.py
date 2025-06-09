"""
核心依赖注入模块
提供API接口所需的通用依赖
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.user import User
from app.api.dependencies import get_current_user

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    可选的用户认证依赖
    
    如果提供了认证令牌，则验证用户身份
    如果没有提供令牌，则返回None（允许匿名访问）
    """
    if not credentials:
        return None
    
    try:
        # 尝试获取当前用户
        return get_current_user(credentials, db)
    except HTTPException:
        # 认证失败时返回None而不是抛出异常
        return None

def require_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    要求管理员权限的依赖
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

def get_user_id_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    从令牌中提取用户ID（如果存在）
    """
    if not credentials:
        return None
    
    try:
        # TODO: 实现JWT令牌解析逻辑
        # 这里应该解析JWT令牌并提取用户ID
        # 暂时返回None
        return None
    except Exception:
        return None 