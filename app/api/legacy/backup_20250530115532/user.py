"""
用户管理路由模块: 提供用户、角色和权限管理功能
(桥接文件 - 仅用于向后兼容，所有新代码都应该使用app.api.frontend.user.manage模块)
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.utils.auth import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    get_password_hash,
    verify_password,
    require_permission
)
from app.schemas.user import (
    User as UserSchema,
    UserUpdate,
    PasswordUpdate,
    Role as RoleSchema,
    RoleCreate,
    RoleUpdate,
    Permission as PermissionSchema,
    PermissionCreate,
    PermissionUpdate,
    UserSettingsUpdate
)
from app.models.user import User, Role, Permission, UserSettings

# 导入新的用户管理路由处理函数
from app.api.frontend.user.manage import (
    get_users as new_get_users,
    get_user as new_get_user,
    update_user_me as new_update_user_me,
    update_user as new_update_user,
    delete_user as new_delete_user,
    update_password_me as new_update_password_me,
    update_settings_me as new_update_settings_me,
    get_roles as new_get_roles,
    create_role as new_create_role,
    update_role as new_update_role,
    delete_role as new_delete_role,
    get_permissions as new_get_permissions,
    assign_permissions_to_role as new_assign_permissions_to_role,
    assign_roles_to_user as new_assign_roles_to_user
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users",
    tags=["用户管理"],
    responses={404: {"description": "未找到"}},
)

# 用户管理接口
@router.get("/", response_model=List[UserSchema])
def get_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(require_permission("user:read"))
) -> Any:
    """
    获取所有用户列表
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/，应使用新的端点: /api/frontend/user/"
    )
    return new_get_users(db=db, skip=skip, limit=limit, current_user=current_user)

@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: str = Path(..., description="用户ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
) -> Any:
    """
    获取指定用户信息
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/{user_id}，应使用新的端点: /api/frontend/user/{user_id}"
    )
    return new_get_user(user_id=user_id, db=db, current_user=current_user)

@router.put("/me", response_model=UserSchema)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户信息
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/me，应使用新的端点: /api/frontend/user/me"
    )
    return new_update_user_me(user_in=user_in, db=db, current_user=current_user)

@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: str = Path(..., description="用户ID"),
    user_in: UserUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update"))
) -> Any:
    """
    更新指定用户信息（管理员权限）
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/{user_id}，应使用新的端点: /api/frontend/user/{user_id}"
    )
    return new_update_user(user_id=user_id, user_in=user_in, db=db, current_user=current_user)

@router.delete("/{user_id}", response_model=UserSchema)
def delete_user(
    user_id: str = Path(..., description="用户ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete"))
) -> Any:
    """
    删除指定用户（管理员权限）
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/{user_id}，应使用新的端点: /api/frontend/user/{user_id}"
    )
    return new_delete_user(user_id=user_id, db=db, current_user=current_user)

@router.put("/me/password", response_model=UserSchema)
def update_password_me(
    password_in: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户密码
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/me/password，应使用新的端点: /api/frontend/user/me/password"
    )
    return new_update_password_me(password_in=password_in, db=db, current_user=current_user)

@router.put("/me/settings", response_model=UserSchema)
def update_settings_me(
    settings_in: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户设置
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/me/settings，应使用新的端点: /api/frontend/user/me/settings"
    )
    return new_update_settings_me(settings_in=settings_in, db=db, current_user=current_user)

# 角色管理接口
@router.get("/roles", response_model=List[RoleSchema])
def get_roles(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(require_permission("role:read"))
) -> Any:
    """
    获取所有角色列表
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/roles，应使用新的端点: /api/frontend/user/roles"
    )
    return new_get_roles(db=db, skip=skip, limit=limit, current_user=current_user)

@router.post("/roles", response_model=RoleSchema)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:create"))
) -> Any:
    """
    创建新角色
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/roles，应使用新的端点: /api/frontend/user/roles"
    )
    return new_create_role(role_in=role_in, db=db, current_user=current_user)

@router.put("/roles/{role_id}", response_model=RoleSchema)
def update_role(
    role_id: str = Path(..., description="角色ID"),
    role_in: RoleUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
) -> Any:
    """
    更新角色信息
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/roles/{role_id}，应使用新的端点: /api/frontend/user/roles/{role_id}"
    )
    return new_update_role(role_id=role_id, role_in=role_in, db=db, current_user=current_user)

@router.delete("/roles/{role_id}", response_model=RoleSchema)
def delete_role(
    role_id: str = Path(..., description="角色ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:delete"))
) -> Any:
    """
    删除角色
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/roles/{role_id}，应使用新的端点: /api/frontend/user/roles/{role_id}"
    )
    return new_delete_role(role_id=role_id, db=db, current_user=current_user)

# 权限管理接口
@router.get("/permissions", response_model=List[PermissionSchema])
def get_permissions(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(require_permission("permission:read"))
) -> Any:
    """
    获取所有权限列表
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/permissions，应使用新的端点: /api/frontend/user/permissions"
    )
    return new_get_permissions(db=db, skip=skip, limit=limit, current_user=current_user)

@router.put("/roles/{role_id}/permissions", response_model=RoleSchema)
def assign_permissions_to_role(
    role_id: str = Path(..., description="角色ID"),
    permission_ids: List[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
) -> Any:
    """
    分配权限给角色
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/roles/{role_id}/permissions，应使用新的端点: /api/frontend/user/roles/{role_id}/permissions"
    )
    return new_assign_permissions_to_role(role_id=role_id, permission_ids=permission_ids, db=db, current_user=current_user)

@router.put("/{user_id}/roles", response_model=UserSchema)
def assign_roles_to_user(
    user_id: str = Path(..., description="用户ID"),
    role_ids: List[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update"))
) -> Any:
    """
    分配角色给用户
    """
    logger.warning(
        "使用已弃用的用户管理端点: /api/v1/users/{user_id}/roles，应使用新的端点: /api/frontend/user/{user_id}/roles"
    )
    return new_assign_roles_to_user(user_id=user_id, role_ids=role_ids, db=db, current_user=current_user)
