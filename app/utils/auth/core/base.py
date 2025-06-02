"""
Auth模块核心基类
提供认证授权的抽象基类和通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class AuthStatus(Enum):
    """认证状态枚举"""
    UNKNOWN = "unknown"
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVOKED = "revoked"


class AuthComponent(ABC):
    """
    认证组件抽象基类
    所有认证相关组件都应该继承此类
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = AuthStatus.UNKNOWN
        self.metadata = {}
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        认证用户
        
        Args:
            credentials: 认证凭据
            
        Returns:
            Dict[str, Any]: 认证结果
        """
        pass
    
    @abstractmethod
    async def authorize(self, user: Dict[str, Any], resource: str, action: str) -> bool:
        """
        授权检查
        
        Args:
            user: 用户信息
            resource: 资源
            action: 动作
            
        Returns:
            bool: 是否有权限
        """
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证令牌
        
        Args:
            token: 令牌
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息，如果无效则返回None
        """
        pass
    
    def get_status(self) -> AuthStatus:
        """获取认证状态"""
        return self.status
    
    def set_status(self, status: AuthStatus) -> None:
        """设置认证状态"""
        self.status = status
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取组件元数据"""
        return self.metadata.copy()
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """更新组件元数据"""
        self.metadata.update(metadata)


class UserInfo:
    """用户信息数据类"""
    
    def __init__(self, user_id: str, username: str, email: str = "",
                 roles: Optional[List[str]] = None, permissions: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInfo':
        """从字典创建"""
        return cls(
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {})
        )
    
    def has_role(self, role: str) -> bool:
        """检查是否有指定角色"""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions 