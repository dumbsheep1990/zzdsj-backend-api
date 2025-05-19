"""
LlamaIndex集成API模块
提供LlamaIndex框架集成的RESTful API端点
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.llamaindex_integration import LlamaIndexIntegration
from app.schemas.llamaindex_integration import (
    LlamaIndexIntegrationCreate,
    LlamaIndexIntegrationUpdate,
    LlamaIndexIntegrationResponse,
    IndexSettingsUpdate,
    StorageContextUpdate
)
from app.services.llamaindex_integration_service import LlamaIndexIntegrationService
from app.api.deps import get_current_user

router = APIRouter(prefix="/llamaindex", tags=["LlamaIndex集成"])

@router.post("/", response_model=LlamaIndexIntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_llamaindex_integration(
    integration: LlamaIndexIntegrationCreate,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    创建新的LlamaIndex集成配置
    
    - **index_name**: 索引名称（必须唯一）
    - **index_type**: 索引类型
    - **knowledge_base_id**: 关联的知识库ID（可选）
    - **index_settings**: 索引设置（可选）
    - **storage_context**: 存储上下文配置（可选）
    - **embedding_model**: 嵌入模型（可选）
    - **chunk_size**: 分块大小（默认:1024）
    - **chunk_overlap**: 分块重叠（默认:200）
    - **metadata**: 元数据（可选）
    
    需要认证和适当的权限
    """
    return await service.create_integration(integration.dict(), current_user.id)

@router.get("/{integration_id}", response_model=LlamaIndexIntegrationResponse)
async def get_llamaindex_integration(
    integration_id: str,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    获取LlamaIndex集成配置详情
    
    需要认证和适当的权限
    """
    integration = await service.get_integration(integration_id, current_user.id)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LlamaIndex集成配置不存在"
        )
    return integration

@router.get("/by-name/{index_name}", response_model=LlamaIndexIntegrationResponse)
async def get_llamaindex_integration_by_name(
    index_name: str,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    通过索引名称获取LlamaIndex集成配置
    
    需要认证和适当的权限
    """
    integration = await service.get_by_index_name(index_name, current_user.id)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"索引名称为 '{index_name}' 的LlamaIndex集成配置不存在"
        )
    return integration

@router.get("/", response_model=List[LlamaIndexIntegrationResponse])
async def list_llamaindex_integrations(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    获取LlamaIndex集成配置列表
    
    需要认证，根据用户权限返回可访问的配置
    """
    return await service.list_integrations(current_user.id, skip, limit)

@router.get("/knowledge-base/{knowledge_base_id}", response_model=List[LlamaIndexIntegrationResponse])
async def list_llamaindex_integrations_by_knowledge_base(
    knowledge_base_id: str,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    获取与指定知识库关联的LlamaIndex集成配置列表
    
    需要认证和知识库的访问权限
    """
    return await service.list_by_knowledge_base(knowledge_base_id, current_user.id)

@router.put("/{integration_id}", response_model=LlamaIndexIntegrationResponse)
async def update_llamaindex_integration(
    integration_id: str,
    integration: LlamaIndexIntegrationUpdate,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    更新LlamaIndex集成配置
    
    需要认证和适当的权限
    """
    updated = await service.update_integration(integration_id, integration.dict(exclude_unset=True), current_user.id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LlamaIndex集成配置不存在"
        )
    return updated

@router.patch("/{integration_id}/index-settings", response_model=LlamaIndexIntegrationResponse)
async def update_index_settings(
    integration_id: str,
    settings: IndexSettingsUpdate,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    更新索引设置
    
    需要认证和适当的权限
    """
    updated = await service.update_index_settings(integration_id, settings.index_settings, current_user.id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LlamaIndex集成配置不存在"
        )
    return updated

@router.patch("/{integration_id}/storage-context", response_model=LlamaIndexIntegrationResponse)
async def update_storage_context(
    integration_id: str,
    context: StorageContextUpdate,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    更新存储上下文配置
    
    需要认证和适当的权限
    """
    updated = await service.update_storage_context(integration_id, context.storage_context, current_user.id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LlamaIndex集成配置不存在"
        )
    return updated

@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llamaindex_integration(
    integration_id: str,
    current_user = Depends(get_current_user),
    service: LlamaIndexIntegrationService = Depends()
):
    """
    删除LlamaIndex集成配置
    
    需要认证和适当的权限
    """
    deleted = await service.delete_integration(integration_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LlamaIndex集成配置不存在"
        )
    return {"detail": "LlamaIndex集成配置已成功删除"}
