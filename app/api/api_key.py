"""
API密钥管理路由模块: 提供API密钥的创建、查询和管理功能
(桥接文件 - 仅用于向后兼容，所有新代码都应该使用app.api.frontend.user.api_key模块)
"""

import logging
from typing import Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.utils.auth import (
    get_current_active_user,
    create_api_key
)
from app.schemas.user import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKey as ApiKeySchema,
    ApiKeyWithValue
)
from app.models.user import User, ApiKey as ApiKeyModel

# 导入新的API密钥路由处理函数
from app.api.frontend.user.api_key import (
    get_api_keys as new_get_api_keys,
    create_user_api_key as new_create_user_api_key,
    update_api_key as new_update_api_key,
    delete_api_key as new_delete_api_key
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/api-keys",
    tags=["API密钥管理"],
    responses={404: {"description": "未找到"}},
)

@router.get("/", response_model=List[ApiKeySchema])
def get_api_keys(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    获取当前用户的所有API密钥
    """
    logger.warning(
        "使用已弃用的API密钥端点: /api/v1/api-keys/，应使用新的端点: /api/frontend/user/api-keys/"
    )
    return new_get_api_keys(db=db, skip=skip, limit=limit, current_user=current_user)

@router.post("/", response_model=ApiKeyWithValue)
def create_user_api_key(
    api_key_in: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    为当前用户创建新的API密钥
    """
    logger.warning(
        "使用已弃用的API密钥端点: /api/v1/api-keys/，应使用新的端点: /api/frontend/user/api-keys/"
    )
    return new_create_user_api_key(api_key_in=api_key_in, db=db, current_user=current_user)

@router.put("/{api_key_id}", response_model=ApiKeySchema)
def update_api_key(
    api_key_id: str = Path(..., description="API密钥ID"),
    api_key_in: ApiKeyUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新API密钥信息
    """
    logger.warning(
        "使用已弃用的API密钥端点: /api/v1/api-keys/{api_key_id}，应使用新的端点: /api/frontend/user/api-keys/{api_key_id}"
    )
    return new_update_api_key(
        api_key_id=api_key_id,
        api_key_in=api_key_in,
        db=db,
        current_user=current_user
    )

@router.delete("/{api_key_id}", response_model=ApiKeySchema)
def delete_api_key(
    api_key_id: str = Path(..., description="API密钥ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    删除API密钥
    """
    logger.warning(
        "使用已弃用的API密钥端点: /api/v1/api-keys/{api_key_id}，应使用新的端点: /api/frontend/user/api-keys/{api_key_id}"
    )
    return new_delete_api_key(
        api_key_id=api_key_id,
        db=db,
        current_user=current_user
    )
