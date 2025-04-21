"""
模型提供商和模型信息API
用于管理和配置不同AI服务提供商及其模型
"""
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import time
import logging

from app.utils.database import get_db
from app.models.model_provider import ModelProvider, ModelInfo, ProviderType
from app.schemas.model_provider import (
    ModelProviderCreate, ModelProviderUpdate, ModelProvider as ModelProviderSchema,
    ModelInfoCreate, ModelInfoUpdate, ModelInfo as ModelInfoSchema,
    ModelTestRequest, ModelTestResponse, ModelProviderList
)
from app.core.model_manager import test_model_connection, get_model_client

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/providers", response_model=ModelProviderList)
def get_model_providers(db: Session = Depends(get_db)):
    """获取所有模型提供商"""
    providers = db.query(ModelProvider).all()
    return {"providers": providers}


@router.get("/providers/{provider_id}", response_model=ModelProviderSchema)
def get_model_provider(provider_id: int, db: Session = Depends(get_db)):
    """获取特定模型提供商的详细信息"""
    provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    return provider


@router.post("/providers", response_model=ModelProviderSchema)
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


@router.put("/providers/{provider_id}", response_model=ModelProviderSchema)
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


@router.delete("/providers/{provider_id}")
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


# 模型信息API
@router.get("/providers/{provider_id}/models", response_model=List[ModelInfoSchema])
def get_provider_models(provider_id: int, db: Session = Depends(get_db)):
    """获取指定提供商的所有模型"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    
    return db_provider.models


@router.post("/providers/{provider_id}/models", response_model=ModelInfoSchema)
def create_model(
    provider_id: int,
    model: ModelInfoCreate,
    db: Session = Depends(get_db)
):
    """为指定提供商创建新模型"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    
    # 检查模型ID是否已存在
    existing_model = db.query(ModelInfo).filter(
        ModelInfo.provider_id == provider_id,
        ModelInfo.model_id == model.model_id
    ).first()
    
    if existing_model:
        raise HTTPException(status_code=400, detail=f"模型 {model.model_id} 已存在")
    
    # 如果设置为默认，更新该提供商的其他默认模型
    if model.is_default:
        existing_defaults = db.query(ModelInfo).filter(
            ModelInfo.provider_id == provider_id,
            ModelInfo.is_default == True
        ).all()
        for default_model in existing_defaults:
            default_model.is_default = False
    
    # 创建新模型
    db_model = ModelInfo(
        provider_id=provider_id,
        model_id=model.model_id,
        display_name=model.display_name or model.model_id,
        capabilities=model.capabilities,
        is_default=model.is_default,
        config=model.config or {}
    )
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model


@router.put("/providers/{provider_id}/models/{model_id}", response_model=ModelInfoSchema)
def update_model(
    provider_id: int,
    model_id: int,
    model_update: ModelInfoUpdate,
    db: Session = Depends(get_db)
):
    """更新模型信息"""
    db_model = db.query(ModelInfo).filter(
        ModelInfo.id == model_id,
        ModelInfo.provider_id == provider_id
    ).first()
    
    if not db_model:
        raise HTTPException(status_code=404, detail="模型未找到")
    
    # 更新字段
    update_data = model_update.dict(exclude_unset=True)
    
    # 如果设置为默认，更新该提供商的其他默认模型
    if update_data.get("is_default"):
        existing_defaults = db.query(ModelInfo).filter(
            ModelInfo.provider_id == provider_id,
            ModelInfo.is_default == True,
            ModelInfo.id != model_id
        ).all()
        for default_model in existing_defaults:
            default_model.is_default = False
    
    for key, value in update_data.items():
        setattr(db_model, key, value)
    
    db.commit()
    db.refresh(db_model)
    
    return db_model


@router.delete("/providers/{provider_id}/models/{model_id}")
def delete_model(provider_id: int, model_id: int, db: Session = Depends(get_db)):
    """删除模型"""
    db_model = db.query(ModelInfo).filter(
        ModelInfo.id == model_id,
        ModelInfo.provider_id == provider_id
    ).first()
    
    if not db_model:
        raise HTTPException(status_code=404, detail="模型未找到")
    
    # 如果是默认，需要检查是否还有其他模型
    if db_model.is_default:
        other_models = db.query(ModelInfo).filter(
            ModelInfo.provider_id == provider_id,
            ModelInfo.id != model_id
        ).first()
        
        if other_models:
            # 将第一个找到的模型设为默认
            other_models.is_default = True
    
    db.delete(db_model)
    db.commit()
    
    return {"message": "模型已删除"}


@router.post("/test-connection", response_model=ModelTestResponse)
async def test_connection(
    test_request: ModelTestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """测试与模型提供商的连接"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == test_request.provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    
    # 如果指定了model_id，查找对应的模型
    model_id = test_request.model_id
    if not model_id:
        # 找默认模型
        default_model = db.query(ModelInfo).filter(
            ModelInfo.provider_id == test_request.provider_id,
            ModelInfo.is_default == True
        ).first()
        
        if default_model:
            model_id = default_model.model_id
        else:
            # 找第一个可用模型
            first_model = db.query(ModelInfo).filter(
                ModelInfo.provider_id == test_request.provider_id
            ).first()
            
            if first_model:
                model_id = first_model.model_id
            else:
                raise HTTPException(status_code=400, detail="未找到可用的模型")
    
    # 测试连接
    start_time = time.time()
    try:
        response = await test_model_connection(
            provider_type=db_provider.provider_type,
            model_id=model_id,
            prompt=test_request.prompt,
            api_key=db_provider.api_key,
            api_base=db_provider.api_base,
            api_version=db_provider.api_version,
            config=db_provider.config
        )
        latency = int((time.time() - start_time) * 1000)  # 毫秒
        
        return {
            "success": True,
            "response": response,
            "latency_ms": latency
        }
    
    except Exception as e:
        logger.error(f"测试模型连接失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "latency_ms": int((time.time() - start_time) * 1000)
        }


@router.get("/default-provider", response_model=ModelProviderSchema)
def get_default_provider(db: Session = Depends(get_db)):
    """获取默认模型提供商"""
    default_provider = db.query(ModelProvider).filter(ModelProvider.is_default == True).first()
    if not default_provider:
        raise HTTPException(status_code=404, detail="未找到默认模型提供商")
    
    return default_provider
