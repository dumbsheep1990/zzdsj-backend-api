"""
模型提供商API
提供AI模型服务提供商的管理和配置功能
"""
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import time
import logging

from app.utils.core.database import get_db
from app.models.model_provider import ModelProvider, ModelInfo, ProviderType
from app.schemas.model_provider import (
    ModelProviderCreate, ModelProviderUpdate, ModelProvider as ModelProviderSchema,
    ModelInfoCreate, ModelInfoUpdate, ModelInfo as ModelInfoSchema,
    ModelTestRequest, ModelTestResponse, ModelProviderList
)
from core.model_manager import test_model_connection, get_model_client

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/providers",
    tags=["模型提供商"],
    responses={404: {"description": "未找到"}}
)


@router.get("/", response_model=ModelProviderList)
def get_model_providers(db: Session = Depends(get_db)):
    """获取所有模型提供商"""
    providers = db.query(ModelProvider).all()
    return {"providers": providers}


@router.get("/{provider_id}", response_model=ModelProviderSchema)
def get_model_provider(provider_id: int, db: Session = Depends(get_db)):
    """获取特定模型提供商的详细信息"""
    provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    return provider


@router.post("/", response_model=ModelProviderSchema)
def create_model_provider(provider: ModelProviderCreate, db: Session = Depends(get_db)):
    """创建新的模型提供商"""
    # 检查提供商类型是否有效
    if provider.provider_type not in [p.value for p in ProviderType]:
        raise HTTPException(status_code=400, detail=f"无效的提供商类型: {provider.provider_type}")
    
    # 如果设置为默认，更新其他默认提供商
    if provider.is_default:
        existing_defaults = db.query(ModelProvider).filter(ModelProvider.is_default == True).all()
        for default_provider in existing_defaults:
            default_provider.is_default = False
    
    # 创建新的提供商
    db_provider = ModelProvider(
        name=provider.name,
        provider_type=provider.provider_type,
        api_key=provider.api_key,
        api_base=provider.api_base,
        api_version=provider.api_version,
        is_default=provider.is_default,
        is_active=provider.is_active,
        config=provider.config or {}
    )
    
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    
    return db_provider


@router.put("/{provider_id}", response_model=ModelProviderSchema)
def update_model_provider(
    provider_id: int, 
    provider_update: ModelProviderUpdate,
    db: Session = Depends(get_db)
):
    """更新模型提供商信息"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    
    # 更新字段
    update_data = provider_update.dict(exclude_unset=True)
    
    # 如果设置为默认，更新其他默认提供商
    if update_data.get("is_default"):
        existing_defaults = db.query(ModelProvider).filter(
            ModelProvider.is_default == True,
            ModelProvider.id != provider_id
        ).all()
        for default_provider in existing_defaults:
            default_provider.is_default = False
    
    for key, value in update_data.items():
        setattr(db_provider, key, value)
    
    db.commit()
    db.refresh(db_provider)
    
    return db_provider


@router.delete("/{provider_id}")
def delete_model_provider(provider_id: int, db: Session = Depends(get_db)):
    """删除模型提供商"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    
    # 如果是默认，需要将错误抛出
    if db_provider.is_default:
        raise HTTPException(status_code=400, detail="无法删除默认模型提供商，请先设置另一个提供商为默认")
    
    db.delete(db_provider)
    db.commit()
    
    return {"message": "模型提供商已删除"}


@router.get("/default", response_model=ModelProviderSchema)
def get_default_provider(db: Session = Depends(get_db)):
    """获取默认模型提供商"""
    default_provider = db.query(ModelProvider).filter(ModelProvider.is_default == True).first()
    if not default_provider:
        raise HTTPException(status_code=404, detail="未找到默认模型提供商")
    
    return default_provider 