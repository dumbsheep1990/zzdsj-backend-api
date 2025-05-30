"""
权限管理器
提供权限控制的核心业务逻辑
"""

import logging
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.permission import Permission, Role, UserRole, RolePermission
from app.repositories.permission_repository import PermissionRepository

logger = logging.getLogger(__name__)


class PermissionManager:
    """权限管理器 - Core层业务逻辑"""
    
    def __init__(self, db: Session):
        """初始化权限管理器"""
        self.db = db
        self.repository = PermissionRepository(db)
    
    # ============ 权限管理 ============
    
    async def create_permission(self, name: str, description: str = None,
                              resource: str = None, action: str = None) -> Dict[str, Any]:
        """创建权限 - 业务逻辑层"""
        try:
            # 业务规则验证
            if await self.repository.get_permission_by_name(name):
                return {
                    "success": False,
                    "error": f"权限名称 '{name}' 已存在",
                    "error_code": "PERMISSION_EXISTS"
                }
            
            # 权限名称格式验证
            if not self._validate_permission_name(name):
                return {
                    "success": False,
                    "error": "权限名称格式无效",
                    "error_code": "INVALID_PERMISSION_NAME"
                }
            
            # 创建权限
            permission = await self.repository.create_permission(
                name=name,
                description=description,
                resource=resource,
                action=action
            )
            
            return {
                "success": True,
                "data": {
                    "id": permission.id,
                    "name": permission.name,
                    "description": permission.description,
                    "resource": permission.resource,
                    "action": permission.action
                }
            }
            
        except Exception as e:
            logger.error(f"创建权限失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建权限失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_permissions(self) -> Dict[str, Any]:
        """获取所有权限"""
        try:
            permissions = await self.repository.get_permissions()
            
            return {
                "success": True,
                "data": [
                    {
                        "id": perm.id,
                        "name": perm.name,
                        "description": perm.description,
                        "resource": perm.resource,
                        "action": perm.action,
                        "created_at": perm.created_at.isoformat()
                    }
                    for perm in permissions
                ]
            }
            
        except Exception as e:
            logger.error(f"获取权限列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取权限列表失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    # ============ 角色管理 ============
    
    async def create_role(self, name: str, description: str = None,
                         is_system: bool = False) -> Dict[str, Any]:
        """创建角色 - 业务逻辑层"""
        try:
            # 业务规则验证
            if await self.repository.get_role_by_name(name):
                return {
                    "success": False,
                    "error": f"角色名称 '{name}' 已存在",
                    "error_code": "ROLE_EXISTS"
                }
            
            # 角色名称格式验证
            if not self._validate_role_name(name):
                return {
                    "success": False,
                    "error": "角色名称格式无效",
                    "error_code": "INVALID_ROLE_NAME"
                }
            
            # 创建角色
            role = await self.repository.create_role(
                name=name,
                description=description,
                is_system=is_system
            )
            
            return {
                "success": True,
                "data": {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "is_system": role.is_system
                }
            }
            
        except Exception as e:
            logger.error(f"创建角色失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建角色失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def assign_permission_to_role(self, role_id: str, permission_id: str) -> Dict[str, Any]:
        """为角色分配权限 - 业务逻辑层"""
        try:
            # 验证角色和权限存在
            role = await self.repository.get_role_by_id(role_id)
            if not role:
                return {
                    "success": False,
                    "error": "角色不存在",
                    "error_code": "ROLE_NOT_FOUND"
                }
            
            permission = await self.repository.get_permission_by_id(permission_id)
            if not permission:
                return {
                    "success": False,
                    "error": "权限不存在",
                    "error_code": "PERMISSION_NOT_FOUND"
                }
            
            # 检查是否已经分配
            if await self.repository.has_role_permission(role_id, permission_id):
                return {
                    "success": False,
                    "error": "权限已分配给该角色",
                    "error_code": "PERMISSION_ALREADY_ASSIGNED"
                }
            
            # 分配权限
            await self.repository.assign_permission_to_role(role_id, permission_id)
            
            return {
                "success": True,
                "data": {
                    "message": f"权限 '{permission.name}' 已分配给角色 '{role.name}'",
                    "role_id": role_id,
                    "permission_id": permission_id
                }
            }
            
        except Exception as e:
            logger.error(f"分配权限失败: {str(e)}")
            return {
                "success": False,
                "error": f"分配权限失败: {str(e)}",
                "error_code": "ASSIGN_FAILED"
            }
    
    async def revoke_permission_from_role(self, role_id: str, permission_id: str) -> Dict[str, Any]:
        """从角色撤销权限 - 业务逻辑层"""
        try:
            # 验证角色和权限存在
            role = await self.repository.get_role_by_id(role_id)
            if not role:
                return {
                    "success": False,
                    "error": "角色不存在",
                    "error_code": "ROLE_NOT_FOUND"
                }
            
            permission = await self.repository.get_permission_by_id(permission_id)
            if not permission:
                return {
                    "success": False,
                    "error": "权限不存在",
                    "error_code": "PERMISSION_NOT_FOUND"
                }
            
            # 检查是否已分配
            if not await self.repository.has_role_permission(role_id, permission_id):
                return {
                    "success": False,
                    "error": "该角色没有此权限",
                    "error_code": "PERMISSION_NOT_ASSIGNED"
                }
            
            # 撤销权限
            await self.repository.revoke_permission_from_role(role_id, permission_id)
            
            return {
                "success": True,
                "data": {
                    "message": f"权限 '{permission.name}' 已从角色 '{role.name}' 撤销",
                    "role_id": role_id,
                    "permission_id": permission_id
                }
            }
            
        except Exception as e:
            logger.error(f"撤销权限失败: {str(e)}")
            return {
                "success": False,
                "error": f"撤销权限失败: {str(e)}",
                "error_code": "REVOKE_FAILED"
            }
    
    # ============ 用户角色管理 ============
    
    async def assign_role_to_user(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """为用户分配角色 - 业务逻辑层"""
        try:
            # 验证角色存在
            role = await self.repository.get_role_by_id(role_id)
            if not role:
                return {
                    "success": False,
                    "error": "角色不存在",
                    "error_code": "ROLE_NOT_FOUND"
                }
            
            # 检查是否已经分配
            if await self.repository.has_user_role(user_id, role_id):
                return {
                    "success": False,
                    "error": "用户已拥有该角色",
                    "error_code": "ROLE_ALREADY_ASSIGNED"
                }
            
            # 分配角色
            await self.repository.assign_role_to_user(user_id, role_id)
            
            return {
                "success": True,
                "data": {
                    "message": f"角色 '{role.name}' 已分配给用户",
                    "user_id": user_id,
                    "role_id": role_id
                }
            }
            
        except Exception as e:
            logger.error(f"分配角色失败: {str(e)}")
            return {
                "success": False,
                "error": f"分配角色失败: {str(e)}",
                "error_code": "ASSIGN_FAILED"
            }
    
    async def revoke_role_from_user(self, user_id: str, role_id: str) -> Dict[str, Any]:
        """从用户撤销角色 - 业务逻辑层"""
        try:
            # 验证角色存在
            role = await self.repository.get_role_by_id(role_id)
            if not role:
                return {
                    "success": False,
                    "error": "角色不存在",
                    "error_code": "ROLE_NOT_FOUND"
                }
            
            # 检查是否已分配
            if not await self.repository.has_user_role(user_id, role_id):
                return {
                    "success": False,
                    "error": "用户没有该角色",
                    "error_code": "ROLE_NOT_ASSIGNED"
                }
            
            # 撤销角色
            await self.repository.revoke_role_from_user(user_id, role_id)
            
            return {
                "success": True,
                "data": {
                    "message": f"角色 '{role.name}' 已从用户撤销",
                    "user_id": user_id,
                    "role_id": role_id
                }
            }
            
        except Exception as e:
            logger.error(f"撤销角色失败: {str(e)}")
            return {
                "success": False,
                "error": f"撤销角色失败: {str(e)}",
                "error_code": "REVOKE_FAILED"
            }
    
    # ============ 权限检查 ============
    
    async def check_user_permission(self, user_id: str, permission_name: str) -> bool:
        """检查用户是否有指定权限"""
        try:
            # 获取用户的所有权限
            user_permissions = await self.get_user_permissions(user_id)
            if not user_permissions["success"]:
                return False
            
            # 检查权限
            permission_names = {perm["name"] for perm in user_permissions["data"]}
            return permission_name in permission_names
            
        except Exception as e:
            logger.error(f"检查用户权限失败: {str(e)}")
            return False
    
    async def check_user_resource_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户是否有指定资源的操作权限"""
        try:
            # 获取用户的所有权限
            user_permissions = await self.get_user_permissions(user_id)
            if not user_permissions["success"]:
                return False
            
            # 检查资源权限
            for perm in user_permissions["data"]:
                if perm["resource"] == resource and perm["action"] == action:
                    return True
                # 检查通配符权限
                if perm["resource"] == "*" or perm["action"] == "*":
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查用户资源权限失败: {str(e)}")
            return False
    
    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有权限"""
        try:
            permissions = await self.repository.get_user_permissions(user_id)
            
            return {
                "success": True,
                "data": [
                    {
                        "id": perm.id,
                        "name": perm.name,
                        "description": perm.description,
                        "resource": perm.resource,
                        "action": perm.action
                    }
                    for perm in permissions
                ]
            }
            
        except Exception as e:
            logger.error(f"获取用户权限失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户权限失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def get_user_roles(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有角色"""
        try:
            roles = await self.repository.get_user_roles(user_id)
            
            return {
                "success": True,
                "data": [
                    {
                        "id": role.id,
                        "name": role.name,
                        "description": role.description,
                        "is_system": role.is_system
                    }
                    for role in roles
                ]
            }
            
        except Exception as e:
            logger.error(f"获取用户角色失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户角色失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def get_role_permissions(self, role_id: str) -> Dict[str, Any]:
        """获取角色的所有权限"""
        try:
            permissions = await self.repository.get_role_permissions(role_id)
            
            return {
                "success": True,
                "data": [
                    {
                        "id": perm.id,
                        "name": perm.name,
                        "description": perm.description,
                        "resource": perm.resource,
                        "action": perm.action
                    }
                    for perm in permissions
                ]
            }
            
        except Exception as e:
            logger.error(f"获取角色权限失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取角色权限失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    # ============ 私有辅助方法 ============
    
    def _validate_permission_name(self, name: str) -> bool:
        """验证权限名称格式"""
        import re
        # 权限名称格式：resource:action 或 简单名称
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]*(:?[a-zA-Z][a-zA-Z0-9_]*)?$'
        return bool(re.match(pattern, name)) and len(name) <= 100
    
    def _validate_role_name(self, name: str) -> bool:
        """验证角色名称格式"""
        import re
        # 角色名称只能包含字母、数字、下划线，长度2-50
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{1,49}$'
        return bool(re.match(pattern, name))
    
    # ============ 权限装饰器辅助方法 ============
    
    def require_permission(self, permission_name: str):
        """权限检查装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 从请求上下文获取用户ID
                user_id = kwargs.get('current_user_id') or getattr(args[0], 'current_user_id', None)
                if not user_id:
                    raise PermissionError("未找到用户信息")
                
                # 检查权限
                has_permission = await self.check_user_permission(user_id, permission_name)
                if not has_permission:
                    raise PermissionError(f"缺少权限: {permission_name}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_resource_permission(self, resource: str, action: str):
        """资源权限检查装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 从请求上下文获取用户ID
                user_id = kwargs.get('current_user_id') or getattr(args[0], 'current_user_id', None)
                if not user_id:
                    raise PermissionError("未找到用户信息")
                
                # 检查资源权限
                has_permission = await self.check_user_resource_permission(user_id, resource, action)
                if not has_permission:
                    raise PermissionError(f"缺少权限: {resource}:{action}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator 