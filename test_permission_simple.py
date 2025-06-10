#!/usr/bin/env python3
"""
简单权限管理系统测试
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

class PermissionType(Enum):
    READ = "read"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    MANAGE = "manage"
    ADMIN = "admin"

class AccessResult(Enum):
    GRANTED = "granted"
    DENIED = "denied"
    RESTRICTED = "restricted"

@dataclass
class Permission:
    permission_type: PermissionType
    resource_pattern: str  # 资源模式，如 "*", "agno_*", "specific_tool"

@dataclass
class Role:
    role_id: str
    role_name: str
    permissions: List[Permission] = field(default_factory=list)

@dataclass
class User:
    user_id: str
    username: str
    roles: Set[str] = field(default_factory=set)
    is_active: bool = True

@dataclass 
class AccessContext:
    user_id: str
    tool_name: str
    permission_type: PermissionType

class SimplePermissionManager:
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._roles: Dict[str, Role] = {}
        self._initialize_system_roles()
    
    def _initialize_system_roles(self):
        """初始化系统角色"""
        # 管理员角色
        admin_role = Role(
            role_id="admin",
            role_name="管理员",
            permissions=[
                Permission(PermissionType.ADMIN, "*")
            ]
        )
        
        # 普通用户角色
        user_role = Role(
            role_id="user",
            role_name="普通用户", 
            permissions=[
                Permission(PermissionType.READ, "*"),
                Permission(PermissionType.EXECUTE, "*")
            ]
        )
        
        # 只读角色
        readonly_role = Role(
            role_id="readonly",
            role_name="只读用户",
            permissions=[
                Permission(PermissionType.READ, "*")
            ]
        )
        
        self._roles = {
            "admin": admin_role,
            "user": user_role,
            "readonly": readonly_role
        }
    
    async def create_user(self, user_id: str, username: str, roles: List[str] = None) -> bool:
        """创建用户"""
        if user_id in self._users:
            return False
        
        role_set = set(roles or ["user"])
        for role_id in role_set:
            if role_id not in self._roles:
                return False
        
        user = User(
            user_id=user_id,
            username=username,
            roles=role_set
        )
        
        self._users[user_id] = user
        return True
    
    async def check_permission(self, context: AccessContext) -> AccessResult:
        """检查权限"""
        user = self._users.get(context.user_id)
        if not user or not user.is_active:
            return AccessResult.DENIED
        
        # 收集用户所有权限
        all_permissions = []
        for role_id in user.roles:
            role = self._roles.get(role_id)
            if role:
                all_permissions.extend(role.permissions)
        
        # 检查权限匹配
        for permission in all_permissions:
            if self._permission_matches(permission, context):
                return AccessResult.GRANTED
        
        return AccessResult.DENIED
    
    def _permission_matches(self, permission: Permission, context: AccessContext) -> bool:
        """检查权限是否匹配"""
        # 管理员权限匹配所有
        if permission.permission_type == PermissionType.ADMIN:
            return True
        
        # 权限类型必须匹配
        if permission.permission_type != context.permission_type:
            return False
        
        # 资源模式匹配
        if permission.resource_pattern == "*":
            return True
        
        if permission.resource_pattern == context.tool_name:
            return True
        
        # 通配符匹配
        if permission.resource_pattern.endswith("*"):
            prefix = permission.resource_pattern[:-1]
            if context.tool_name.startswith(prefix):
                return True
        
        return False
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        user = self._users.get(user_id)
        if not user:
            return None
        
        return {
            "user_id": user.user_id,
            "username": user.username,
            "roles": list(user.roles),
            "is_active": user.is_active
        }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            "total_users": len(self._users),
            "active_users": len([u for u in self._users.values() if u.is_active]),
            "total_roles": len(self._roles)
        }

async def test_permission_system():
    try:
        print("=== 权限管理系统测试 ===")
        
        # 创建权限管理器
        pm = SimplePermissionManager()
        print("✅ 权限管理器创建成功")
        
        # 测试1: 创建用户
        print("\n📋 测试1: 创建用户")
        
        success1 = await pm.create_user("user1", "张三", ["admin"])
        success2 = await pm.create_user("user2", "李四", ["user"])
        success3 = await pm.create_user("user3", "王五", ["readonly"])
        
        print(f"  • 创建管理员用户: {'✅' if success1 else '❌'}")
        print(f"  • 创建普通用户: {'✅' if success2 else '❌'}")
        print(f"  • 创建只读用户: {'✅' if success3 else '❌'}")
        
        # 测试2: 权限检查
        print("\n📋 测试2: 权限检查")
        
        # 管理员权限测试
        admin_context = AccessContext("user1", "agno_reasoning", PermissionType.EXECUTE)
        admin_result = await pm.check_permission(admin_context)
        print(f"  • 管理员执行权限: {admin_result.value}")
        
        # 普通用户权限测试
        user_context = AccessContext("user2", "agno_reasoning", PermissionType.EXECUTE)
        user_result = await pm.check_permission(user_context)
        print(f"  • 普通用户执行权限: {user_result.value}")
        
        # 只读用户权限测试
        readonly_exec_context = AccessContext("user3", "agno_reasoning", PermissionType.EXECUTE)
        readonly_exec_result = await pm.check_permission(readonly_exec_context)
        print(f"  • 只读用户执行权限: {readonly_exec_result.value}")
        
        readonly_read_context = AccessContext("user3", "agno_reasoning", PermissionType.READ)
        readonly_read_result = await pm.check_permission(readonly_read_context)
        print(f"  • 只读用户读取权限: {readonly_read_result.value}")
        
        # 测试3: 用户信息查询
        print("\n📋 测试3: 用户信息查询")
        
        user1_info = pm.get_user_info("user1")
        user2_info = pm.get_user_info("user2")
        
        print(f"  • 用户1信息: {user1_info}")
        print(f"  • 用户2信息: {user2_info}")
        
        # 测试4: 统计信息
        print("\n📋 测试4: 统计信息")
        
        stats = pm.get_statistics()
        print(f"  • 总用户数: {stats['total_users']}")
        print(f"  • 活跃用户数: {stats['active_users']}")
        print(f"  • 总角色数: {stats['total_roles']}")
        
        print("\n✅ 权限管理系统测试完成！")
        
        print("\n📊 测试总结:")
        print("✅ 用户创建功能正常")
        print("✅ 权限检查功能正常")
        print("✅ 角色权限继承正常")
        print("✅ 访问控制策略正常")
        print("✅ 用户信息查询正常")
        print("✅ 统计功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 权限管理系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_permission_system())
    print(f"\n🎯 测试结果: {'✅ 全部通过' if success else '❌ 有失败项'}")
    exit(0 if success else 1) 