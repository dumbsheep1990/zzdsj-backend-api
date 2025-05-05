"""
API密钥管理路由模块: 提供API密钥的创建、查询和管理功能
"""

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
    api_keys = db.query(ApiKeyModel).filter(
        ApiKeyModel.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return api_keys

@router.post("/", response_model=ApiKeyWithValue)
def create_user_api_key(
    api_key_in: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    为当前用户创建新的API密钥
    """
    # 设置过期时间（如果提供）
    expires_at = None
    if api_key_in.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=api_key_in.expires_days)
    
    # 创建API密钥
    api_key_value = create_api_key(db, current_user.id, api_key_in.name, api_key_in.description)
    
    # 获取创建的API密钥记录
    api_key = db.query(ApiKeyModel).filter(
        ApiKeyModel.key == api_key_value
    ).first()
    
    # 设置过期时间
    if expires_at:
        api_key.expires_at = expires_at
        db.commit()
        db.refresh(api_key)
    
    # 返回包含密钥值的响应
    return {
        "id": api_key.id,
        "name": api_key.name,
        "description": api_key.description,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at,
        "last_used_at": api_key.last_used_at,
        "created_at": api_key.created_at,
        "key": api_key_value  # 这是唯一一次返回密钥值
    }

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
    # 检查API密钥是否存在并属于当前用户
    api_key = db.query(ApiKeyModel).filter(
        ApiKeyModel.id == api_key_id,
        ApiKeyModel.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API密钥不存在或不属于当前用户")
    
    # 更新API密钥信息
    for field, value in api_key_in.model_dump(exclude_unset=True).items():
        setattr(api_key, field, value)
    
    db.commit()
    db.refresh(api_key)
    return api_key

@router.delete("/{api_key_id}", response_model=ApiKeySchema)
def delete_api_key(
    api_key_id: str = Path(..., description="API密钥ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    删除API密钥
    """
    # 检查API密钥是否存在并属于当前用户
    api_key = db.query(ApiKeyModel).filter(
        ApiKeyModel.id == api_key_id,
        ApiKeyModel.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API密钥不存在或不属于当前用户")
    
    # 删除API密钥
    db.delete(api_key)
    db.commit()
    return api_key
