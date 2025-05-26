"""
[✅ 已迁移] 此文件已完成重构和迁移到 app/api/frontend/ai/models/provider.py 和 app/api/frontend/ai/models/model.py
模型提供商和模型信息API桥接文件
(已弃用) - 请使用 app.api.frontend.ai.models 模块
此文件仅用于向后兼容，所有新代码都应该使用新的模块
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

# 导入新的模型提供商和模型API路由处理函数
from app.api.frontend.ai.models.provider import (
    get_model_providers as new_get_model_providers,
    get_model_provider as new_get_model_provider,
    create_model_provider as new_create_model_provider,
    update_model_provider as new_update_model_provider,
    delete_model_provider as new_delete_model_provider,
    get_default_provider as new_get_default_provider
)

from app.api.frontend.ai.models.model import (
    get_provider_models as new_get_provider_models,
    create_model as new_create_model,
    update_model as new_update_model,
    delete_model as new_delete_model,
    test_connection as new_test_connection
)

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/providers", response_model=ModelProviderList)
def get_model_providers(db: Session = Depends(get_db)):
    """获取所有模型提供商"""
    logger.warning(
        "使用已弃用的模型提供商端点: /providers，应使用新的端点: /api/frontend/ai/models/providers"
    )
    return new_get_model_providers(db=db)


@router.get("/providers/{provider_id}", response_model=ModelProviderSchema)
def get_model_provider(provider_id: int, db: Session = Depends(get_db)):
    """获取特定模型提供商的详细信息"""
    logger.warning(
        f"使用已弃用的模型提供商端点: /providers/{provider_id}，应使用新的端点: /api/frontend/ai/models/providers/{provider_id}"
    )
    return new_get_model_provider(provider_id=provider_id, db=db)


@router.post("/providers", response_model=ModelProviderSchema)
def create_model_provider(provider: ModelProviderCreate, db: Session = Depends(get_db)):
    """创建新的模型提供商"""
    logger.warning(
        "使用已弃用的模型提供商端点: /providers，应使用新的端点: /api/frontend/ai/models/providers"
    )
    return new_create_model_provider(provider=provider, db=db)


@router.put("/providers/{provider_id}", response_model=ModelProviderSchema)
def update_model_provider(
    provider_id: int, 
    provider_update: ModelProviderUpdate,
    db: Session = Depends(get_db)
):
    """更新模型提供商信息"""
    logger.warning(
        f"使用已弃用的模型提供商端点: /providers/{provider_id}，应使用新的端点: /api/frontend/ai/models/providers/{provider_id}"
    )
    return new_update_model_provider(provider_id=provider_id, provider_update=provider_update, db=db)


@router.delete("/providers/{provider_id}")
def delete_model_provider(provider_id: int, db: Session = Depends(get_db)):
    """删除模型提供商"""
    logger.warning(
        f"使用已弃用的模型提供商端点: /providers/{provider_id}，应使用新的端点: /api/frontend/ai/models/providers/{provider_id}"
    )
    return new_delete_model_provider(provider_id=provider_id, db=db)


# 模型信息API
@router.get("/providers/{provider_id}/models", response_model=List[ModelInfoSchema])
def get_provider_models(provider_id: int, db: Session = Depends(get_db)):
    """获取指定提供商的所有模型"""
    logger.warning(
        f"使用已弃用的模型端点: /providers/{provider_id}/models，应使用新的端点: /api/frontend/ai/models/provider/{provider_id}"
    )
    return new_get_provider_models(provider_id=provider_id, db=db)


@router.post("/providers/{provider_id}/models", response_model=ModelInfoSchema)
def create_model(
    provider_id: int,
    model: ModelInfoCreate,
    db: Session = Depends(get_db)
):
    """为指定提供商创建新模型"""
    logger.warning(
        f"使用已弃用的模型端点: /providers/{provider_id}/models，应使用新的端点: /api/frontend/ai/models/provider/{provider_id}"
    )
    return new_create_model(provider_id=provider_id, model=model, db=db)


@router.put("/providers/{provider_id}/models/{model_id}", response_model=ModelInfoSchema)
def update_model(
    provider_id: int,
    model_id: int,
    model_update: ModelInfoUpdate,
    db: Session = Depends(get_db)
):
    """更新模型信息"""
    logger.warning(
        f"使用已弃用的模型端点: /providers/{provider_id}/models/{model_id}，应使用新的端点: /api/frontend/ai/models/{model_id}"
    )
    return new_update_model(model_id=model_id, model_update=model_update, db=db)


@router.delete("/providers/{provider_id}/models/{model_id}")
def delete_model(provider_id: int, model_id: int, db: Session = Depends(get_db)):
    """删除模型"""
    logger.warning(
        f"使用已弃用的模型端点: /providers/{provider_id}/models/{model_id}，应使用新的端点: /api/frontend/ai/models/{model_id}"
    )
    return new_delete_model(model_id=model_id, db=db)


@router.post("/test-connection", response_model=ModelTestResponse)
async def test_connection(
    test_request: ModelTestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """测试与模型提供商的连接"""
    logger.warning(
        "使用已弃用的模型端点: /test-connection，应使用新的端点: /api/frontend/ai/models/test-connection"
    )
    return await new_test_connection(test_request=test_request, background_tasks=background_tasks, db=db)


@router.get("/default-provider", response_model=ModelProviderSchema)
def get_default_provider(db: Session = Depends(get_db)):
    """获取默认模型提供商"""
    logger.warning(
        "使用已弃用的模型提供商端点: /default-provider，应使用新的端点: /api/frontend/ai/models/providers/default"
    )
    return new_get_default_provider(db=db)
