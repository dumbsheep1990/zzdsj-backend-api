"""
模型API
提供AI模型的管理和配置功能
"""
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import time
import logging

from app.utils.database import get_db
from app.models.model_provider import ModelProvider, ModelInfo
from app.schemas.model_provider import (
    ModelInfoCreate, ModelInfoUpdate, ModelInfo as ModelInfoSchema,
    ModelTestRequest, ModelTestResponse
)
from core.model_manager import test_model_connection

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/models",
    tags=["AI模型"],
    responses={404: {"description": "未找到"}}
)


@router.get("/provider/{provider_id}", response_model=List[ModelInfoSchema])
def get_provider_models(provider_id: int, db: Session = Depends(get_db)):
    """获取指定提供商的所有模型"""
    db_provider = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    if not db_provider:
        raise HTTPException(status_code=404, detail="模型提供商未找到")
    
    return db_provider.models


@router.post("/provider/{provider_id}", response_model=ModelInfoSchema)
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


@router.put("/{model_id}", response_model=ModelInfoSchema)
def update_model(
    model_id: int,
    model_update: ModelInfoUpdate,
    db: Session = Depends(get_db)
):
    """更新模型信息"""
    db_model = db.query(ModelInfo).filter(ModelInfo.id == model_id).first()
    
    if not db_model:
        raise HTTPException(status_code=404, detail="模型未找到")
    
    # 更新字段
    update_data = model_update.dict(exclude_unset=True)
    
    # 如果设置为默认，更新该提供商的其他默认模型
    if update_data.get("is_default"):
        existing_defaults = db.query(ModelInfo).filter(
            ModelInfo.provider_id == db_model.provider_id,
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


@router.delete("/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    """删除模型"""
    db_model = db.query(ModelInfo).filter(ModelInfo.id == model_id).first()
    
    if not db_model:
        raise HTTPException(status_code=404, detail="模型未找到")
    
    # 如果是默认，需要检查是否还有其他模型
    if db_model.is_default:
        other_models = db.query(ModelInfo).filter(
            ModelInfo.provider_id == db_model.provider_id,
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