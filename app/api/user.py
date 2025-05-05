"""
用户管理路由模块: 提供用户、角色和权限管理功能
"""

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
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserSchema)
def get_user(
    user_id: str = Path(..., description="用户ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
) -> Any:
    """
    获取指定用户信息
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.put("/me", response_model=UserSchema)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户信息
    """
    if user_in.email and user_in.email != current_user.email:
        # 检查邮箱是否已被使用
        user_by_email = db.query(User).filter(User.email == user_in.email).first()
        if user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用",
            )
    
    # 更新用户信息
    for field, value in user_in.model_dump(exclude_unset=True).items():
        if field != "disabled" and field != "is_superuser":  # 普通用户无法修改这些字段
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user_in.email and user_in.email != user.email:
        # 检查邮箱是否已被使用
        user_by_email = db.query(User).filter(User.email == user_in.email).first()
        if user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用",
            )
    
    # 更新用户信息
    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", response_model=UserSchema)
def delete_user(
    user_id: str = Path(..., description="用户ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete"))
) -> Any:
    """
    删除指定用户（管理员权限）
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 不真正删除用户，而是禁用账户
    user.disabled = True
    db.commit()
    return user

@router.put("/me/password", response_model=UserSchema)
def update_password_me(
    password_in: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户密码
    """
    # 验证当前密码
    if not verify_password(password_in.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码不正确",
        )
    
    # 更新密码
    current_user.hashed_password = get_password_hash(password_in.new_password)
    db.commit()
    return current_user

@router.put("/me/settings", response_model=UserSchema)
def update_settings_me(
    settings_in: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    更新当前用户设置
    """
    # 获取用户设置
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        # 如果没有设置记录，创建一个
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    # 更新设置
    for field, value in settings_in.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

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
    roles = db.query(Role).offset(skip).limit(limit).all()
    return roles

@router.post("/roles", response_model=RoleSchema)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:create"))
) -> Any:
    """
    创建新角色
    """
    # 检查角色名是否已存在
    role = db.query(Role).filter(Role.name == role_in.name).first()
    if role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色名已存在",
        )
    
    # 如果设置为默认角色，需要取消其他默认角色
    if role_in.is_default:
        db.query(Role).filter(Role.is_default == True).update({"is_default": False})
    
    # 创建新角色
    db_role = Role(
        name=role_in.name,
        description=role_in.description,
        is_default=role_in.is_default,
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

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
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 如果更新角色名，检查是否已存在
    if role_in.name and role_in.name != role.name:
        existing_role = db.query(Role).filter(Role.name == role_in.name).first()
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色名已存在",
            )
    
    # 如果设置为默认角色，需要取消其他默认角色
    if role_in.is_default is not None and role_in.is_default and not role.is_default:
        db.query(Role).filter(Role.is_default == True).update({"is_default": False})
    
    # 更新角色信息
    for field, value in role_in.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    
    db.commit()
    db.refresh(role)
    return role

@router.delete("/roles/{role_id}", response_model=RoleSchema)
def delete_role(
    role_id: str = Path(..., description="角色ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:delete"))
) -> Any:
    """
    删除角色
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 检查角色是否有关联用户
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该角色有关联用户，无法删除",
        )
    
    # 删除角色
    db.delete(role)
    db.commit()
    return role

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
    permissions = db.query(Permission).offset(skip).limit(limit).all()
    return permissions

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
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 清除现有权限
    role.permissions = []
    
    # 如果提供了权限ID列表，添加权限
    if permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        for permission in permissions:
            role.permissions.append(permission)
    
    db.commit()
    db.refresh(role)
    return role

@router.put("/users/{user_id}/roles", response_model=UserSchema)
def assign_roles_to_user(
    user_id: str = Path(..., description="用户ID"),
    role_ids: List[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update"))
) -> Any:
    """
    分配角色给用户
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 清除现有角色
    user.roles = []
    
    # 如果提供了角色ID列表，添加角色
    if role_ids:
        roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
        for role in roles:
            user.roles.append(role)
    
    db.commit()
    db.refresh(user)
    return user
