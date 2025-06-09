"""
API依赖注入
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import logging

from app.config import get_settings
from app.config.database import get_async_db
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

# 安全方案
security = HTTPBearer()


class CurrentUser:
    """当前用户信息"""

    def __init__(self, id: int, email: str, username: str):
        self.id = id
        self.email = email
        self.username = username


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> CurrentUser:
    """获取当前登录用户"""
    token = credentials.credentials

    try:
        # 解码JWT令牌
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id_str = payload.get("sub")

        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 将字符串转换为整数
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的用户ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 查询用户信息
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(
            id=user.id,
            email=user.email,
            username=user.username
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_async_db)
) -> Optional[CurrentUser]:
    """获取可选的当前用户（用于公开接口）"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# 分页参数
class PaginationParams:
    """分页参数"""

    def __init__(
            self,
            skip: int = 0,
            limit: int = 20
    ):
        self.skip = skip
        self.limit = min(limit, 100)  # 限制最大返回数量


def get_pagination(
        skip: int = 0,
        limit: int = 20
) -> PaginationParams:
    """获取分页参数"""
    return PaginationParams(skip=skip, limit=limit)


# 数据库事务管理
from contextlib import asynccontextmanager


@asynccontextmanager
async def async_transaction(db: AsyncSession):
    """异步数据库事务上下文管理器"""
    try:
        yield db
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        await db.close()