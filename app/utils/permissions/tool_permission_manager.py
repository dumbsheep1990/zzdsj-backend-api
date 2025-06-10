"""
工具权限控制系统
支持基于角色的访问控制(RBAC)、细粒度权限管理、权限缓存等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import hashlib


class PermissionType(Enum):
    """权限类型"""
    READ = "read"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    MANAGE = "manage"
    ADMIN = "admin"


class PermissionScope(Enum):
    """权限范围"""
    GLOBAL = "global"
    FRAMEWORK = "framework"
    TOOL = "tool"
    CATEGORY = "category"


class AccessResult(Enum):
    """访问结果"""
    GRANTED = "granted"
    DENIED = "denied"
    RESTRICTED = "restricted"


@dataclass
class Permission:
    """权限定义"""
    permission_type: PermissionType
    scope: PermissionScope
    resource_id: str
    conditions: Optional[Dict[str, Any]] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Role:
    """角色定义"""
    role_id: str
    role_name: str
    description: str
    permissions: List[Permission] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    is_system_role: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class User:
    """用户定义"""
    user_id: str
    username: str
    roles: Set[str] = field(default_factory=set)
    direct_permissions: List[Permission] = field(default_factory=list)
    groups: Set[str] = field(default_factory=set)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_access: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AccessContext:
    """访问上下文"""
    user_id: str
    tool_name: str
    permission_type: PermissionType
    request_time: datetime = field(default_factory=datetime.now)
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class AccessLog:
    """访问日志"""
    log_id: str
    user_id: str
    tool_name: str
    permission_type: PermissionType
    access_result: AccessResult
    timestamp: datetime
    context: AccessContext
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class ToolPermissionManager:
    """工具权限管理器"""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # 核心数据存储
        self._users: Dict[str, User] = {}
        self._roles: Dict[str, Role] = {}
        self._groups: Dict[str, Set[str]] = {}
        
        # 权限缓存
        self._permission_cache: Dict[str, Dict[str, AccessResult]] = {}
        self._cache_ttl = 300
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # 访问日志
        self._access_logs: List[AccessLog] = []
        self._max_log_entries = 10000
        
        # 权限策略配置
        self._policy_config = {
            "cache_enabled": True,
            "audit_logging": True,
            "default_deny": True,
            "session_timeout": 3600,
            "max_failed_attempts": 5,
            "lockout_duration": 900,
            "require_explicit_grant": True
        }
        
        # 初始化系统角色
        self._initialize_system_roles()
    
    def _initialize_system_roles(self):
        """初始化系统预定义角色"""
        # 超级管理员角色
        admin_role = Role(
            role_id="system_admin",
            role_name="系统管理员",
            description="拥有所有权限的超级管理员",
            permissions=[
                Permission(
                    permission_type=PermissionType.ADMIN,
                    scope=PermissionScope.GLOBAL,
                    resource_id="*"
                )
            ],
            is_system_role=True
        )
        
        # 普通用户角色
        user_role = Role(
            role_id="normal_user",
            role_name="普通用户",
            description="具有基本工具执行权限的普通用户",
            permissions=[
                Permission(
                    permission_type=PermissionType.READ,
                    scope=PermissionScope.GLOBAL,
                    resource_id="*"
                ),
                Permission(
                    permission_type=PermissionType.EXECUTE,
                    scope=PermissionScope.TOOL,
                    resource_id="*",
                    conditions={"rate_limit": 100}
                )
            ],
            is_system_role=True
        )
        
        # 只读用户角色
        readonly_role = Role(
            role_id="readonly_user",
            role_name="只读用户",
            description="只能查看工具信息，不能执行",
            permissions=[
                Permission(
                    permission_type=PermissionType.READ,
                    scope=PermissionScope.GLOBAL,
                    resource_id="*"
                )
            ],
            is_system_role=True
        )
        
        # 开发者角色
        developer_role = Role(
            role_id="developer",
            role_name="开发者",
            description="拥有工具配置和管理权限的开发者",
            permissions=[
                Permission(
                    permission_type=PermissionType.READ,
                    scope=PermissionScope.GLOBAL,
                    resource_id="*"
                ),
                Permission(
                    permission_type=PermissionType.EXECUTE,
                    scope=PermissionScope.GLOBAL,
                    resource_id="*"
                ),
                Permission(
                    permission_type=PermissionType.CONFIGURE,
                    scope=PermissionScope.GLOBAL,
                    resource_id="*"
                )
            ],
            is_system_role=True
        )
        
        # 注册系统角色
        for role in [admin_role, user_role, readonly_role, developer_role]:
            self._roles[role.role_id] = role
    
    async def create_user(self, user_id: str, username: str, roles: List[str] = None) -> bool:
        """创建用户"""
        try:
            if user_id in self._users:
                self._logger.warning(f"User {user_id} already exists")
                return False
            
            role_set = set(roles or ["normal_user"])
            for role_id in role_set:
                if role_id not in self._roles:
                    self._logger.error(f"Role {role_id} does not exist")
                    return False
            
            user = User(
                user_id=user_id,
                username=username,
                roles=role_set
            )
            
            self._users[user_id] = user
            self._logger.info(f"Created user: {username} ({user_id}) with roles: {role_set}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to create user {user_id}: {e}")
            return False
    
    async def check_permission(self, context: AccessContext) -> AccessResult:
        """检查权限"""
        try:
            user = self._users.get(context.user_id)
            if not user or not user.is_active:
                return AccessResult.DENIED
            
            user.last_access = context.request_time
            
            if self._policy_config["cache_enabled"]:
                cached_result = await self._get_cached_permission(context)
                if cached_result is not None:
                    return cached_result
            
            result = await self._evaluate_permissions(user, context)
            
            if self._policy_config["cache_enabled"]:
                await self._cache_permission_result(context, result)
            
            return result
            
        except Exception as e:
            self._logger.error(f"Permission check failed for user {context.user_id}: {e}")
            return AccessResult.DENIED
    
    async def _evaluate_permissions(self, user: User, context: AccessContext) -> AccessResult:
        """评估用户权限"""
        all_permissions = []
        all_permissions.extend(user.direct_permissions)
        
        for role_id in user.roles:
            role_permissions = await self._get_role_permissions(role_id)
            all_permissions.extend(role_permissions)
        
        for permission in all_permissions:
            if await self._permission_matches(permission, context):
                if await self._check_permission_conditions(permission, context):
                    return AccessResult.GRANTED
        
        return AccessResult.DENIED if self._policy_config["default_deny"] else AccessResult.RESTRICTED
    
    async def _get_role_permissions(self, role_id: str) -> List[Permission]:
        """获取角色的所有权限"""
        permissions = []
        visited_roles = set()
        
        async def collect_permissions(current_role_id: str):
            if current_role_id in visited_roles:
                return
            
            visited_roles.add(current_role_id)
            
            role = self._roles.get(current_role_id)
            if not role:
                return
            
            permissions.extend(role.permissions)
            
            for parent_role_id in role.parent_roles:
                await collect_permissions(parent_role_id)
        
        await collect_permissions(role_id)
        return permissions
    
    async def _permission_matches(self, permission: Permission, context: AccessContext) -> bool:
        """检查权限是否匹配请求"""
        if permission.permission_type != context.permission_type and permission.permission_type != PermissionType.ADMIN:
            return False
        
        if permission.scope == PermissionScope.GLOBAL:
            return permission.resource_id == "*"
        elif permission.scope == PermissionScope.TOOL:
            return permission.resource_id == "*" or permission.resource_id == context.tool_name
        elif permission.scope == PermissionScope.FRAMEWORK:
            tool_framework = await self._get_tool_framework(context.tool_name)
            return permission.resource_id == "*" or permission.resource_id == tool_framework
        elif permission.scope == PermissionScope.CATEGORY:
            tool_category = await self._get_tool_category(context.tool_name)
            return permission.resource_id == "*" or permission.resource_id == tool_category
        
        return False
    
    async def _check_permission_conditions(self, permission: Permission, context: AccessContext) -> bool:
        """检查权限条件约束"""
        if not permission.conditions:
            return True
        
        if permission.expires_at and context.request_time > permission.expires_at:
            return False
        
        if "allowed_ips" in permission.conditions:
            allowed_ips = permission.conditions["allowed_ips"]
            if context.client_ip and context.client_ip not in allowed_ips:
                return False
        
        return True
    
    async def _get_tool_framework(self, tool_name: str) -> str:
        """获取工具所属框架"""
        if "agno" in tool_name.lower():
            return "agno"
        elif "haystack" in tool_name.lower():
            return "haystack"
        elif "fastmcp" in tool_name.lower():
            return "fastmcp"
        elif "owl" in tool_name.lower():
            return "owl"
        elif "llamaindex" in tool_name.lower():
            return "llamaindex"
        return "unknown"
    
    async def _get_tool_category(self, tool_name: str) -> str:
        """获取工具所属类别"""
        if "reasoning" in tool_name.lower():
            return "reasoning"
        elif "search" in tool_name.lower():
            return "search"
        elif "knowledge" in tool_name.lower():
            return "knowledge"
        elif "extract" in tool_name.lower():
            return "extraction"
        return "general"
    
    async def _get_cached_permission(self, context: AccessContext) -> Optional[AccessResult]:
        """获取缓存的权限结果"""
        cache_key = f"user:{context.user_id}"
        
        if cache_key in self._permission_cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if cache_time and (datetime.now() - cache_time).seconds < self._cache_ttl:
                tool_permissions = self._permission_cache[cache_key]
                return tool_permissions.get(f"{context.tool_name}:{context.permission_type.value}")
        
        return None
    
    async def _cache_permission_result(self, context: AccessContext, result: AccessResult):
        """缓存权限结果"""
        cache_key = f"user:{context.user_id}"
        
        if cache_key not in self._permission_cache:
            self._permission_cache[cache_key] = {}
        
        tool_key = f"{context.tool_name}:{context.permission_type.value}"
        self._permission_cache[cache_key][tool_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
    
    async def get_user_permissions(self, user_id: str) -> List[Permission]:
        """获取用户的所有权限"""
        user = self._users.get(user_id)
        if not user:
            return []
        
        all_permissions = []
        all_permissions.extend(user.direct_permissions)
        
        for role_id in user.roles:
            role_permissions = await self._get_role_permissions(role_id)
            all_permissions.extend(role_permissions)
        
        return all_permissions
    
    def get_permission_statistics(self) -> Dict[str, Any]:
        """获取权限统计信息"""
        return {
            "total_users": len(self._users),
            "active_users": len([u for u in self._users.values() if u.is_active]),
            "total_roles": len(self._roles),
            "system_roles": len([r for r in self._roles.values() if r.is_system_role]),
            "cached_permissions": len(self._permission_cache),
            "access_logs": len(self._access_logs),
            "policy_config": self._policy_config.copy()
        }


# 全局工具权限管理器实例
tool_permission_manager = ToolPermissionManager() 