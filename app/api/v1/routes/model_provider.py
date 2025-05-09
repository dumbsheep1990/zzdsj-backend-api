"""
模型提供商API路由
提供统一的模型提供商管理接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.models.database import get_db
from app.models.model_provider import ModelProvider, Model
from app.schemas.model_provider import (
    ModelProvider as ModelProviderSchema,
    ModelProviderCreate,
    ModelProviderUpdate,
    Model as ModelSchema,
    ModelCreate,
    ModelUpdate
)
from app.api.v1.dependencies import ResponseFormatter, get_request_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/providers", response_model=List[ModelProviderSchema])
async def get_model_providers(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有模型提供商
    """
    query = db.query(ModelProvider)
    
    if is_active is not None:
        query = query.filter(ModelProvider.is_active == is_active)
    
    providers = query.order_by(ModelProvider.created_at.desc()).offset(skip).limit(limit).all()
    return ResponseFormatter.format_success(providers)


@router.post("/providers", response_model=ModelProviderSchema)
async def create_model_provider(
    provider: ModelProviderCreate,
    db: Session = Depends(get_db)
):
    """
    创建新模型提供商
    """
    # 检查提供商是否已存在
    existing = db.query(ModelProvider).filter(ModelProvider.name == provider.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="提供商名称已存在")
    
    # 创建提供商记录
    db_provider = ModelProvider(
        name=provider.name,
        display_name=provider.display_name,
        api_type=provider.api_type,
        base_url=provider.base_url,
        api_key=provider.api_key,
        is_active=provider.is_active,
        config=provider.config or {},
        metadata=provider.metadata or {}
    )
    
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    
    return ResponseFormatter.format_success(db_provider)


@router.get("/providers/{provider_id}", response_model=ModelProviderSchema)
async def get_model_provider(
    provider_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取模型提供商
    """
    provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型提供商不存在")
    
    return ResponseFormatter.format_success(provider)


@router.put("/providers/{provider_id}", response_model=ModelProviderSchema)
async def update_model_provider(
    provider_id: int,
    provider_update: ModelProviderUpdate,
    db: Session = Depends(get_db)
):
    """
    更新模型提供商
    """
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型提供商不存在")
    
    # 检查名称唯一性
    if provider_update.name is not None and provider_update.name != db_provider.name:
        existing = db.query(ModelProvider).filter(ModelProvider.name == provider_update.name).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="提供商名称已存在")
        db_provider.name = provider_update.name
    
    # 更新其他字段
    if provider_update.display_name is not None:
        db_provider.display_name = provider_update.display_name
    
    if provider_update.api_type is not None:
        db_provider.api_type = provider_update.api_type
    
    if provider_update.base_url is not None:
        db_provider.base_url = provider_update.base_url
    
    if provider_update.api_key is not None:
        db_provider.api_key = provider_update.api_key
    
    if provider_update.is_active is not None:
        db_provider.is_active = provider_update.is_active
    
    if provider_update.config is not None:
        db_provider.config = provider_update.config
    
    if provider_update.metadata is not None:
        # 合并元数据，保留现有字段
        db_provider.metadata.update(provider_update.metadata)
    
    db_provider.updated_at = datetime.now()
    db.commit()
    db.refresh(db_provider)
    
    return ResponseFormatter.format_success(db_provider)


@router.delete("/providers/{provider_id}")
async def delete_model_provider(
    provider_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除或停用模型提供商
    """
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型提供商不存在")
    
    if permanent:
        # 删除关联的模型
        db.query(Model).filter(Model.provider_id == provider_id).delete()
        
        # 删除提供商
        db.delete(db_provider)
    else:
        # 仅停用提供商
        db_provider.is_active = False
        db_provider.updated_at = datetime.now()
    
    db.commit()
    
    return ResponseFormatter.format_success(None, message=f"模型提供商已{'删除' if permanent else '停用'}")


@router.get("/models", response_model=List[ModelSchema])
async def get_models(
    provider_id: Optional[int] = None,
    model_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取所有模型，支持按提供商和类型过滤
    """
    query = db.query(Model)
    
    if provider_id:
        query = query.filter(Model.provider_id == provider_id)
    
    if model_type:
        query = query.filter(Model.model_type == model_type)
    
    if is_active is not None:
        query = query.filter(Model.is_active == is_active)
    
    models = query.order_by(Model.created_at.desc()).offset(skip).limit(limit).all()
    return ResponseFormatter.format_success(models)


@router.post("/models", response_model=ModelSchema)
async def create_model(
    model: ModelCreate,
    db: Session = Depends(get_db)
):
    """
    创建新模型
    """
    # 检查提供商是否存在
    provider = db.query(ModelProvider).filter(ModelProvider.id == model.provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型提供商不存在")
    
    # 创建模型记录
    db_model = Model(
        provider_id=model.provider_id,
        name=model.name,
        display_name=model.display_name,
        model_type=model.model_type,
        context_length=model.context_length,
        is_active=model.is_active,
        config=model.config or {},
        metadata=model.metadata or {}
    )
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return ResponseFormatter.format_success(db_model)


@router.get("/models/{model_id}", response_model=ModelSchema)
async def get_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取模型
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    
    return ResponseFormatter.format_success(model)


@router.put("/models/{model_id}", response_model=ModelSchema)
async def update_model(
    model_id: int,
    model_update: ModelUpdate,
    db: Session = Depends(get_db)
):
    """
    更新模型
    """
    db_model = db.query(Model).filter(Model.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    
    # 更新字段
    if model_update.provider_id is not None:
        # 检查提供商是否存在
        provider = db.query(ModelProvider).filter(ModelProvider.id == model_update.provider_id).first()
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型提供商不存在")
        db_model.provider_id = model_update.provider_id
    
    if model_update.name is not None:
        db_model.name = model_update.name
    
    if model_update.display_name is not None:
        db_model.display_name = model_update.display_name
    
    if model_update.model_type is not None:
        db_model.model_type = model_update.model_type
    
    if model_update.context_length is not None:
        db_model.context_length = model_update.context_length
    
    if model_update.is_active is not None:
        db_model.is_active = model_update.is_active
    
    if model_update.config is not None:
        db_model.config = model_update.config
    
    if model_update.metadata is not None:
        # 合并元数据，保留现有字段
        db_model.metadata.update(model_update.metadata)
    
    db_model.updated_at = datetime.now()
    db.commit()
    db.refresh(db_model)
    
    return ResponseFormatter.format_success(db_model)


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除或停用模型
    """
    db_model = db.query(Model).filter(Model.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    
    if permanent:
        # 删除模型
        db.delete(db_model)
    else:
        # 仅停用模型
        db_model.is_active = False
        db_model.updated_at = datetime.now()
    
    db.commit()
    
    return ResponseFormatter.format_success(None, message=f"模型已{'删除' if permanent else '停用'}")


@router.get("/models/{model_id}/config", response_model=Dict[str, Any])
async def get_model_config(
    model_id: int,
    db: Session = Depends(get_db)
):
    """
    获取模型配置
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    
    # 获取完整配置，包括提供商配置
    provider = db.query(ModelProvider).filter(ModelProvider.id == model.provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型提供商不存在")
    
    # 合并配置
    config = {
        "model": {
            "id": model.id,
            "name": model.name,
            "display_name": model.display_name,
            "type": model.model_type,
            "context_length": model.context_length,
            "config": model.config
        },
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "display_name": provider.display_name,
            "api_type": provider.api_type,
            "base_url": provider.base_url,
            "config": provider.config
        }
    }
    
    return ResponseFormatter.format_success(config)
