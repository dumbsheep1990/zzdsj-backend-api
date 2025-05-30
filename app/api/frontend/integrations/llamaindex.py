"""
Frontend API - LlamaIndex集成服务接口
提供LlamaIndex框架集成的RESTful API端点，支持索引管理和查询操作
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory
from app.models.llamaindex_integration import LlamaIndexIntegration
from app.schemas.llamaindex_integration import (
    LlamaIndexIntegrationCreate,
    LlamaIndexIntegrationUpdate,
    LlamaIndexIntegrationResponse,
    IndexSettingsUpdate,
    StorageContextUpdate
)
from app.services.llamaindex_integration_service import LlamaIndexIntegrationService

# 创建响应格式化器和路由
formatter = InternalResponseFormatter()
router = APIRouter(
    prefix="/integrations/llamaindex",
    tags=["LlamaIndex集成"],
    responses={401: {"description": "未授权"}, 404: {"description": "未找到资源"}}
)
validator = ValidatorFactory.create("llamaindex")

# ====================================
# 索引管理接口
# ====================================

@router.get("/", response_model=List[LlamaIndexIntegrationResponse])
async def list_llamaindex_integrations(
    name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取LlamaIndex集成列表
    
    支持按名称过滤和分页
    """
    service = container.get_service(LlamaIndexIntegrationService)
    integrations = await service.list_integrations(
        user_id=context.user.id,
        name=name,
        limit=limit,
        offset=offset
    )
    return formatter.success(integrations)

@router.post("/", response_model=LlamaIndexIntegrationResponse)
async def create_llamaindex_integration(
    integration: LlamaIndexIntegrationCreate,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建新的LlamaIndex集成
    
    支持设置索引类型、存储上下文和配置选项
    """
    # 验证请求数据
    validator.validate_create(integration)
    
    # 创建集成
    service = container.get_service(LlamaIndexIntegrationService)
    new_integration = await service.create_integration(
        user_id=context.user.id,
        name=integration.name,
        description=integration.description,
        index_type=integration.index_type,
        settings=integration.settings,
        storage_context=integration.storage_context
    )
    
    return formatter.success(
        new_integration,
        message="成功创建LlamaIndex集成",
        status_code=status.HTTP_201_CREATED
    )

@router.get("/{integration_id}", response_model=LlamaIndexIntegrationResponse)
async def get_llamaindex_integration(
    integration_id: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取LlamaIndex集成详情
    
    返回集成的详细信息，包括索引设置和存储上下文
    """
    service = container.get_service(LlamaIndexIntegrationService)
    integration = await service.get_integration(
        integration_id=integration_id,
        user_id=context.user.id
    )
    
    if not integration:
        return formatter.error(
            message="找不到指定的LlamaIndex集成",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return formatter.success(integration)

@router.put("/{integration_id}", response_model=LlamaIndexIntegrationResponse)
async def update_llamaindex_integration(
    integration_id: str,
    update_data: LlamaIndexIntegrationUpdate,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新LlamaIndex集成
    
    支持更新名称、描述和索引设置
    """
    # 验证请求数据
    validator.validate_update(update_data)
    
    # 更新集成
    service = container.get_service(LlamaIndexIntegrationService)
    updated_integration = await service.update_integration(
        integration_id=integration_id,
        user_id=context.user.id,
        update_data=update_data
    )
    
    if not updated_integration:
        return formatter.error(
            message="找不到指定的LlamaIndex集成或无权更新",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return formatter.success(
        updated_integration,
        message="成功更新LlamaIndex集成"
    )

@router.delete("/{integration_id}")
async def delete_llamaindex_integration(
    integration_id: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除LlamaIndex集成
    
    将删除集成及其关联的索引数据
    """
    service = container.get_service(LlamaIndexIntegrationService)
    success = await service.delete_integration(
        integration_id=integration_id,
        user_id=context.user.id
    )
    
    if not success:
        return formatter.error(
            message="找不到指定的LlamaIndex集成或无权删除",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    return formatter.success(
        data=None,
        message="成功删除LlamaIndex集成"
    )

# ====================================
# 索引操作接口
# ====================================

@router.post("/{integration_id}/update-settings")
async def update_index_settings(
    integration_id: str,
    settings_update: IndexSettingsUpdate,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新索引设置
    
    支持更新索引类型和配置选项
    """
    service = container.get_service(LlamaIndexIntegrationService)
    updated = await service.update_index_settings(
        integration_id=integration_id,
        user_id=context.user.id,
        settings_update=settings_update
    )
    
    if not updated:
        return formatter.error(
            message="无法更新索引设置",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    return formatter.success(
        data=updated,
        message="成功更新索引设置"
    )

@router.post("/{integration_id}/update-storage")
async def update_storage_context(
    integration_id: str,
    storage_update: StorageContextUpdate,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新存储上下文
    
    支持更新存储类型和存储配置
    """
    service = container.get_service(LlamaIndexIntegrationService)
    updated = await service.update_storage_context(
        integration_id=integration_id,
        user_id=context.user.id,
        storage_update=storage_update
    )
    
    if not updated:
        return formatter.error(
            message="无法更新存储上下文",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    return formatter.success(
        data=updated,
        message="成功更新存储上下文"
    )

@router.post("/{integration_id}/rebuild-index")
async def rebuild_index(
    integration_id: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    重建索引
    
    根据当前设置重新构建索引
    """
    service = container.get_service(LlamaIndexIntegrationService)
    result = await service.rebuild_index(
        integration_id=integration_id,
        user_id=context.user.id
    )
    
    if not result:
        return formatter.error(
            message="无法重建索引",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    return formatter.success(
        data={"task_id": result.get("task_id")},
        message="索引重建任务已启动"
    )

@router.get("/{integration_id}/status")
async def get_index_status(
    integration_id: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取索引状态
    
    返回索引的当前状态，包括文档数量、索引大小和上次更新时间
    """
    service = container.get_service(LlamaIndexIntegrationService)
    status = await service.get_index_status(
        integration_id=integration_id,
        user_id=context.user.id
    )
    
    if not status:
        return formatter.error(
            message="无法获取索引状态",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    return formatter.success(status)
