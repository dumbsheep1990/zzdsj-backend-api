"""
资源权限管理路由模块: 提供用户与各类资源之间权限关系的管理功能
"""

from typing import Any, List, Optional

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
    ModelConfigAccess, 
    MCPConfigAccess,
    UserResourceQuota,
    ResourceType,
    AccessLevel
)
from app.schemas.resource_permission import (
    ResourcePermissionCreate,
    ResourcePermissionResponse,
    ResourcePermissionUpdate,
    KnowledgeBaseAccessCreate,
    KnowledgeBaseAccessResponse,
    KnowledgeBaseAccessUpdate,
    AssistantAccessCreate,
    AssistantAccessResponse,
    AssistantAccessUpdate,
    ModelConfigAccessCreate,
    ModelConfigAccessResponse,
    ModelConfigAccessUpdate,
    MCPConfigAccessCreate,
    MCPConfigAccessResponse,
    MCPConfigAccessUpdate,
    UserResourceQuotaResponse,
    UserResourceQuotaUpdate
)

router = APIRouter(
    prefix="/api/v1/resource-permissions",
    tags=["资源权限管理"],
    responses={404: {"description": "未找到"}},
)

# 通用资源权限管理
@router.get("/", response_model=List[ResourcePermissionResponse])
def get_resource_permissions(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    resource_type: Optional[ResourceType] = Query(None, description="资源类型过滤"),
    resource_id: Optional[str] = Query(None, description="资源ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:read"))
) -> Any:
    """
    获取资源权限列表（管理员权限）
    """
    query = db.query(ResourcePermission)
    
    # 应用过滤条件
    if user_id:
        query = query.filter(ResourcePermission.user_id == user_id)
    if resource_type:
        query = query.filter(ResourcePermission.resource_type == resource_type)
    if resource_id:
        query = query.filter(ResourcePermission.resource_id == resource_id)
        
    permissions = query.all()
    return permissions

@router.post("/", response_model=ResourcePermissionResponse)
def create_resource_permission(
    permission_in: ResourcePermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:create"))
) -> Any:
    """
    创建资源权限（管理员权限）
    """
    # 检查用户是否存在
    user = db.query(User).filter(User.id == permission_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已存在相同的权限记录
    existing = db.query(ResourcePermission).filter(
        ResourcePermission.user_id == permission_in.user_id,
        ResourcePermission.resource_type == permission_in.resource_type,
        ResourcePermission.resource_id == permission_in.resource_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此用户对该资源已有权限记录，请使用更新接口"
        )
    
    # 创建权限记录
    db_permission = ResourcePermission(
        user_id=permission_in.user_id,
        resource_type=permission_in.resource_type,
        resource_id=permission_in.resource_id,
        access_level=permission_in.access_level
    )
    
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    
    return db_permission

@router.put("/{permission_id}", response_model=ResourcePermissionResponse)
def update_resource_permission(
    permission_id: str = Path(..., description="权限记录ID"),
    permission_in: ResourcePermissionUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:update"))
) -> Any:
    """
    更新资源权限（管理员权限）
    """
    db_permission = db.query(ResourcePermission).filter(
        ResourcePermission.id == permission_id
    ).first()
    
    if not db_permission:
        raise HTTPException(status_code=404, detail="权限记录不存在")
    
    # 更新访问级别
    if permission_in.access_level:
        db_permission.access_level = permission_in.access_level
    
    db.commit()
    db.refresh(db_permission)
    
    return db_permission

@router.delete("/{permission_id}", response_model=ResourcePermissionResponse)
def delete_resource_permission(
    permission_id: str = Path(..., description="权限记录ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:delete"))
) -> Any:
    """
    删除资源权限（管理员权限）
    """
    db_permission = db.query(ResourcePermission).filter(
        ResourcePermission.id == permission_id
    ).first()
    
    if not db_permission:
        raise HTTPException(status_code=404, detail="权限记录不存在")
    
    db.delete(db_permission)
    db.commit()
    
    return db_permission

# 知识库访问权限管理
@router.get("/knowledge-base-access", response_model=List[KnowledgeBaseAccessResponse])
def get_knowledge_base_access(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    knowledge_base_id: Optional[str] = Query(None, description="知识库ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:read"))
) -> Any:
    """
    获取知识库访问权限列表（管理员权限）
    """
    query = db.query(KnowledgeBaseAccess)
    
    # 应用过滤条件
    if user_id:
        query = query.filter(KnowledgeBaseAccess.user_id == user_id)
    if knowledge_base_id:
        query = query.filter(KnowledgeBaseAccess.knowledge_base_id == knowledge_base_id)
        
    access_list = query.all()
    return access_list

@router.post("/knowledge-base-access", response_model=KnowledgeBaseAccessResponse)
def create_knowledge_base_access(
    access_in: KnowledgeBaseAccessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:create"))
) -> Any:
    """
    创建知识库访问权限（管理员权限）
    """
    # 检查用户是否存在
    user = db.query(User).filter(User.id == access_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已存在相同的访问权限记录
    existing = db.query(KnowledgeBaseAccess).filter(
        KnowledgeBaseAccess.user_id == access_in.user_id,
        KnowledgeBaseAccess.knowledge_base_id == access_in.knowledge_base_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此用户对该知识库已有访问权限记录，请使用更新接口"
        )
    
    # 创建访问权限记录
    db_access = KnowledgeBaseAccess(
        user_id=access_in.user_id,
        knowledge_base_id=access_in.knowledge_base_id,
        can_read=access_in.can_read,
        can_write=access_in.can_write,
        can_delete=access_in.can_delete,
        can_share=access_in.can_share,
        can_manage=access_in.can_manage
    )
    
    db.add(db_access)
    db.commit()
    db.refresh(db_access)
    
    return db_access

@router.put("/knowledge-base-access/{access_id}", response_model=KnowledgeBaseAccessResponse)
def update_knowledge_base_access(
    access_id: str = Path(..., description="访问权限记录ID"),
    access_in: KnowledgeBaseAccessUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:update"))
) -> Any:
    """
    更新知识库访问权限（管理员权限）
    """
    db_access = db.query(KnowledgeBaseAccess).filter(
        KnowledgeBaseAccess.id == access_id
    ).first()
    
    if not db_access:
        raise HTTPException(status_code=404, detail="访问权限记录不存在")
    
    # 更新权限字段
    for field, value in access_in.model_dump(exclude_unset=True).items():
        setattr(db_access, field, value)
    
    db.commit()
    db.refresh(db_access)
    
    return db_access

@router.delete("/knowledge-base-access/{access_id}", response_model=KnowledgeBaseAccessResponse)
def delete_knowledge_base_access(
    access_id: str = Path(..., description="访问权限记录ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:delete"))
) -> Any:
    """
    删除知识库访问权限（管理员权限）
    """
    db_access = db.query(KnowledgeBaseAccess).filter(
        KnowledgeBaseAccess.id == access_id
    ).first()
    
    if not db_access:
        raise HTTPException(status_code=404, detail="访问权限记录不存在")
    
    db.delete(db_access)
    db.commit()
    
    return db_access

# 助手访问权限管理
@router.get("/assistant-access", response_model=List[AssistantAccessResponse])
def get_assistant_access(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    assistant_id: Optional[str] = Query(None, description="助手ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:read"))
) -> Any:
    """
    获取助手访问权限列表（管理员权限）
    """
    query = db.query(AssistantAccess)
    
    # 应用过滤条件
    if user_id:
        query = query.filter(AssistantAccess.user_id == user_id)
    if assistant_id:
        query = query.filter(AssistantAccess.assistant_id == assistant_id)
        
    access_list = query.all()
    return access_list

@router.post("/assistant-access", response_model=AssistantAccessResponse)
def create_assistant_access(
    access_in: AssistantAccessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_permission:create"))
) -> Any:
    """
    创建助手访问权限（管理员权限）
    """
    # 检查用户是否存在
    user = db.query(User).filter(User.id == access_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已存在相同的访问权限记录
    existing = db.query(AssistantAccess).filter(
        AssistantAccess.user_id == access_in.user_id,
        AssistantAccess.assistant_id == access_in.assistant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此用户对该助手已有访问权限记录，请使用更新接口"
        )
    
    # 创建访问权限记录
    db_access = AssistantAccess(
        user_id=access_in.user_id,
        assistant_id=access_in.assistant_id,
        can_use=access_in.can_use,
        can_edit=access_in.can_edit,
        can_delete=access_in.can_delete,
        can_share=access_in.can_share,
        can_manage=access_in.can_manage
    )
    
    db.add(db_access)
    db.commit()
    db.refresh(db_access)
    
    return db_access

# 用户资源配额管理
@router.get("/quotas", response_model=List[UserResourceQuotaResponse])
def get_resource_quotas(
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_quota:read"))
) -> Any:
    """
    获取用户资源配额列表（管理员权限）
    """
    query = db.query(UserResourceQuota)
    
    # 应用过滤条件
    if user_id:
        query = query.filter(UserResourceQuota.user_id == user_id)
        
    quotas = query.all()
    return quotas

@router.get("/quotas/me", response_model=UserResourceQuotaResponse)
def get_my_resource_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    获取当前用户的资源配额
    """
    quota = db.query(UserResourceQuota).filter(
        UserResourceQuota.user_id == current_user.id
    ).first()
    
    if not quota:
        raise HTTPException(status_code=404, detail="资源配额未设置")
    
    return quota

@router.put("/quotas/{user_id}", response_model=UserResourceQuotaResponse)
def update_resource_quota(
    user_id: str = Path(..., description="用户ID"),
    quota_in: UserResourceQuotaUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resource_quota:update"))
) -> Any:
    """
    更新用户资源配额（管理员权限）
    """
    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    quota = db.query(UserResourceQuota).filter(
        UserResourceQuota.user_id == user_id
    ).first()
    
    if not quota:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 的资源配额未设置")
    
    # 更新配额设置
    for field, value in quota_in.model_dump(exclude_unset=True).items():
        setattr(quota, field, value)
    
    db.commit()
    db.refresh(quota)
    
    return quota
