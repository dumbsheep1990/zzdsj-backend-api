"""
资源权限管理路由模块: 提供用户与各类资源之间权限关系的管理功能
"""

from typing import Any, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.utils.auth import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    require_permission
)
from app.models.user import User
from app.models.resource_permission import (
    ResourcePermission, 
    KnowledgeBaseAccess, 
    AssistantAccess, 
    UserResourceQuota
)

from app.schemas.resource_permission import (
    ResourceType,
    AccessLevel,
    ResourcePermissionCreate,
    ResourcePermissionUpdate,
    ResourcePermissionResponse,
    KnowledgeBaseAccessCreate,
    KnowledgeBaseAccessUpdate,
    KnowledgeBaseAccessResponse,
    AssistantAccessCreate,
    AssistantAccessUpdate,
    AssistantAccessResponse,
    UserResourceQuotaUpdate,
    UserResourceQuotaResponse
)
from app.repositories.resource_permission import (
    ResourcePermissionRepository,
    KnowledgeBaseAccessRepository,
    AssistantAccessRepository,
    UserResourceQuotaRepository
)
from app.api.frontend.dependencies import ResponseFormatter

router = APIRouter(prefix="/api/frontend/security/permissions", tags=["资源权限管理"])


@router.get("/resources", response_model=List[ResourcePermissionResponse])
async def get_resource_permissions(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    resource_type: Optional[ResourceType] = Query(None, description="资源类型过滤"),
    resource_id: Optional[str] = Query(None, description="资源ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:read"))
):
    """
    获取资源权限列表（管理员权限）
    
    - **user_id**: 可选的用户ID过滤
    - **resource_type**: 可选的资源类型过滤
    - **resource_id**: 可选的资源ID过滤
    
    需要资源权限读取权限
    """
    repo = ResourcePermissionRepository(db)
    
    # 构建过滤条件
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if resource_type:
        filters["resource_type"] = resource_type
    if resource_id:
        filters["resource_id"] = resource_id
    
    permissions = await repo.list_permissions(**filters)
    return ResponseFormatter.format_success(permissions)


@router.post("/resources", response_model=ResourcePermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_permission(
    permission_in: ResourcePermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:create"))
):
    """
    创建资源权限（管理员权限）
    
    - **user_id**: 用户ID
    - **resource_type**: 资源类型
    - **resource_id**: 资源ID
    - **access_level**: 访问级别
    - **expires_at**: 可选的过期时间
    
    需要资源权限创建权限
    """
    repo = ResourcePermissionRepository(db)
    
    # 检查权限是否已存在
    existing = await repo.get_permission_by_resource(
        permission_in.user_id,
        permission_in.resource_type,
        permission_in.resource_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户已有此资源的权限记录"
        )
    
    # 创建权限
    try:
        new_permission = await repo.create_permission(permission_in.dict())
        return ResponseFormatter.format_success(new_permission)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建权限失败: {str(e)}"
        )


@router.put("/resources/{permission_id}", response_model=ResourcePermissionResponse)
async def update_resource_permission(
    permission_id: str = Path(..., description="权限记录ID"),
    permission_in: ResourcePermissionUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:update"))
):
    """
    更新资源权限（管理员权限）
    
    - **permission_id**: 权限记录ID
    - **permission_in**: 更新数据
    
    需要资源权限更新权限
    """
    repo = ResourcePermissionRepository(db)
    
    # 检查权限是否存在
    existing = await repo.get_permission(permission_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"权限记录 {permission_id} 不存在"
        )
    
    # 更新权限
    try:
        updated = await repo.update_permission(permission_id, permission_in.dict(exclude_unset=True))
        return ResponseFormatter.format_success(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新权限失败: {str(e)}"
        )


@router.delete("/resources/{permission_id}")
async def delete_resource_permission(
    permission_id: str = Path(..., description="权限记录ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:delete"))
):
    """
    删除资源权限（管理员权限）
    
    - **permission_id**: 权限记录ID
    
    需要资源权限删除权限
    """
    repo = ResourcePermissionRepository(db)
    
    # 检查权限是否存在
    existing = await repo.get_permission(permission_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"权限记录 {permission_id} 不存在"
        )
    
    # 删除权限
    await repo.delete_permission(permission_id)
    return ResponseFormatter.format_success({"status": "success", "message": "权限记录已删除"})


# 知识库访问权限管理
@router.get("/knowledge-bases", response_model=List[KnowledgeBaseAccessResponse])
async def get_knowledge_base_access(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    knowledge_base_id: Optional[str] = Query(None, description="知识库ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:read"))
):
    """
    获取知识库访问权限列表（管理员权限）
    
    - **user_id**: 可选的用户ID过滤
    - **knowledge_base_id**: 可选的知识库ID过滤
    
    需要资源权限读取权限
    """
    repo = KnowledgeBaseAccessRepository(db)
    
    # 构建过滤条件
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if knowledge_base_id:
        filters["knowledge_base_id"] = knowledge_base_id
    
    access_list = await repo.list_access(**filters)
    return ResponseFormatter.format_success(access_list)


@router.post("/knowledge-bases", response_model=KnowledgeBaseAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base_access(
    access_in: KnowledgeBaseAccessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:create"))
):
    """
    创建知识库访问权限（管理员权限）
    
    - **user_id**: 用户ID
    - **knowledge_base_id**: 知识库ID
    - **can_read**: 是否可读
    - **can_write**: 是否可写
    - **can_share**: 是否可共享
    - **is_owner**: 是否为所有者
    - **expires_at**: 可选的过期时间
    
    需要资源权限创建权限
    """
    repo = KnowledgeBaseAccessRepository(db)
    
    # 检查权限是否已存在
    existing = await repo.get_access_by_knowledge_base(
        access_in.user_id,
        access_in.knowledge_base_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户已有此知识库的访问权限记录"
        )
    
    # 创建权限
    try:
        new_access = await repo.create_access(access_in.dict())
        return ResponseFormatter.format_success(new_access)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建知识库访问权限失败: {str(e)}"
        )


@router.put("/knowledge-bases/{access_id}", response_model=KnowledgeBaseAccessResponse)
async def update_knowledge_base_access(
    access_id: str = Path(..., description="访问权限记录ID"),
    access_in: KnowledgeBaseAccessUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:update"))
):
    """
    更新知识库访问权限（管理员权限）
    
    - **access_id**: 访问权限记录ID
    - **access_in**: 更新数据
    
    需要资源权限更新权限
    """
    repo = KnowledgeBaseAccessRepository(db)
    
    # 检查权限是否存在
    existing = await repo.get_access(access_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库访问权限记录 {access_id} 不存在"
        )
    
    # 更新权限
    try:
        updated = await repo.update_access(access_id, access_in.dict(exclude_unset=True))
        return ResponseFormatter.format_success(updated)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新知识库访问权限失败: {str(e)}"
        )


@router.delete("/knowledge-bases/{access_id}")
async def delete_knowledge_base_access(
    access_id: str = Path(..., description="访问权限记录ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:delete"))
):
    """
    删除知识库访问权限（管理员权限）
    
    - **access_id**: 访问权限记录ID
    
    需要资源权限删除权限
    """
    repo = KnowledgeBaseAccessRepository(db)
    
    # 检查权限是否存在
    existing = await repo.get_access(access_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库访问权限记录 {access_id} 不存在"
        )
    
    # 删除权限
    await repo.delete_access(access_id)
    return ResponseFormatter.format_success({"status": "success", "message": "知识库访问权限记录已删除"})


# 助手访问权限管理
@router.get("/assistants", response_model=List[AssistantAccessResponse])
async def get_assistant_access(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    assistant_id: Optional[str] = Query(None, description="助手ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:read"))
):
    """
    获取助手访问权限列表（管理员权限）
    
    - **user_id**: 可选的用户ID过滤
    - **assistant_id**: 可选的助手ID过滤
    
    需要资源权限读取权限
    """
    repo = AssistantAccessRepository(db)
    
    # 构建过滤条件
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if assistant_id:
        filters["assistant_id"] = assistant_id
    
    access_list = await repo.list_access(**filters)
    return ResponseFormatter.format_success(access_list)


@router.post("/assistants", response_model=AssistantAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant_access(
    access_in: AssistantAccessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:create"))
):
    """
    创建助手访问权限（管理员权限）
    
    - **user_id**: 用户ID
    - **assistant_id**: 助手ID
    - **can_use**: 是否可使用
    - **can_edit**: 是否可编辑
    - **can_share**: 是否可共享
    - **is_owner**: 是否为所有者
    - **expires_at**: 可选的过期时间
    
    需要资源权限创建权限
    """
    repo = AssistantAccessRepository(db)
    
    # 检查权限是否已存在
    existing = await repo.get_access_by_assistant(
        access_in.user_id,
        access_in.assistant_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户已有此助手的访问权限记录"
        )
    
    # 创建权限
    try:
        new_access = await repo.create_access(access_in.dict())
        return ResponseFormatter.format_success(new_access)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建助手访问权限失败: {str(e)}"
        )


# 用户资源配额管理
@router.get("/quotas", response_model=List[UserResourceQuotaResponse])
async def get_resource_quotas(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_quota:read"))
):
    """
    获取用户资源配额列表（管理员权限）
    
    - **user_id**: 可选的用户ID过滤
    
    需要资源配额读取权限
    """
    repo = UserResourceQuotaRepository(db)
    
    # 构建过滤条件
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    
    quotas = await repo.list_quotas(**filters)
    return ResponseFormatter.format_success(quotas)


@router.get("/quotas/me", response_model=UserResourceQuotaResponse)
async def get_my_resource_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的资源配额
    
    返回当前登录用户的资源配额信息
    """
    repo = UserResourceQuotaRepository(db)
    
    # 获取当前用户的配额
    quota = await repo.get_quota_by_user(current_user.id)
    
    if not quota:
        # 如果没有配额记录，返回默认配额
        quota = {
            "user_id": current_user.id,
            "max_knowledge_bases": 10,
            "max_assistants": 5,
            "max_tokens_per_month": 1000000,
            "max_storage_mb": 1000,
            "current_tokens_used": 0,
            "current_storage_used_mb": 0
        }
    
    return ResponseFormatter.format_success(quota)


@router.put("/quotas/{user_id}", response_model=UserResourceQuotaResponse)
async def update_resource_quota(
    user_id: str = Path(..., description="用户ID"),
    quota_in: UserResourceQuotaUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_quota:update"))
):
    """
    更新用户资源配额（管理员权限）
    
    - **user_id**: 用户ID
    - **quota_in**: 更新数据
    
    需要资源配额更新权限
    """
    repo = UserResourceQuotaRepository(db)
    
    # 检查用户的配额是否存在
    existing = await repo.get_quota_by_user(user_id)
    
    if not existing:
        # 如果不存在，创建新的配额记录
        try:
            quota_data = quota_in.dict(exclude_unset=True)
            quota_data["user_id"] = user_id
            
            new_quota = await repo.create_quota(quota_data)
            return ResponseFormatter.format_success(new_quota)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"创建用户资源配额失败: {str(e)}"
            )
    else:
        # 如果存在，更新配额记录
        try:
            updated = await repo.update_quota(existing["id"], quota_in.dict(exclude_unset=True))
            return ResponseFormatter.format_success(updated)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"更新用户资源配额失败: {str(e)}"
            )
