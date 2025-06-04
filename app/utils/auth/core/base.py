"""
Auth模块核心基类
提供认证授权的抽象基类和通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)


class AuthStatus(Enum):
    """认证状态枚举"""
    UNKNOWN = "unknown"
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    EXPIRED = "expired"
    INVALID = "invalid"
    REVOKED = "revoked"


class TokenType(Enum):
    """令牌类型枚举"""
    ACCESS = "access"
    REFRESH = "refresh"
    API = "api"
    SESSION = "session"


class AuthComponent(ABC):
    """
    认证组件抽象基类
    所有认证相关组件都应该继承此类
    支持令牌管理、会话管理和权限缓存
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = AuthStatus.UNKNOWN
        self.metadata = {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")
        
        # 令牌存储和会话管理
        self._active_tokens: Dict[str, Dict[str, Any]] = {}
        self._user_sessions: Dict[str, Dict[str, Any]] = {}
        self._permission_cache: Dict[str, Dict[str, Any]] = {}
        self._blacklisted_tokens: Set[str] = set()
        self._lock = asyncio.Lock()
        
        # 配置参数
        self.token_expiry = self.config.get("token_expiry_minutes", 60)
        self.session_timeout = self.config.get("session_timeout_minutes", 1440)  # 24小时
        self.max_sessions_per_user = self.config.get("max_sessions_per_user", 5)
        self.permission_cache_ttl = self.config.get("permission_cache_ttl_minutes", 30)
    
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
    
    async def create_token(self, user_id: str, token_type: TokenType = TokenType.ACCESS, 
                          expires_in: Optional[int] = None) -> Dict[str, Any]:
        """
        创建令牌
        
        Args:
            user_id: 用户ID
            token_type: 令牌类型
            expires_in: 过期时间(分钟)
            
        Returns:
            Dict[str, Any]: 令牌信息
        """
        async with self._lock:
            # 生成令牌
            token = self._generate_token()
            
            # 计算过期时间
            if expires_in is None:
                expires_in = self.token_expiry
            
            expires_at = datetime.now() + timedelta(minutes=expires_in)
            
            # 存储令牌信息
            token_info = {
                "token": token,
                "user_id": user_id,
                "type": token_type.value,
                "created_at": datetime.now(),
                "expires_at": expires_at,
                "is_active": True
            }
            
            self._active_tokens[token] = token_info
            
            self.logger.info(f"为用户 {user_id} 创建了 {token_type.value} 令牌")
            
            return {
                "token": token,
                "expires_at": expires_at.isoformat(),
                "expires_in": expires_in * 60  # 返回秒数
            }
    
    async def revoke_token(self, token: str) -> bool:
        """
        撤销令牌
        
        Args:
            token: 要撤销的令牌
            
        Returns:
            bool: 是否成功撤销
        """
        async with self._lock:
            if token in self._active_tokens:
                # 标记为非活跃状态
                self._active_tokens[token]["is_active"] = False
                self._active_tokens[token]["revoked_at"] = datetime.now()
                
                # 添加到黑名单
                self._blacklisted_tokens.add(token)
                
                user_id = self._active_tokens[token]["user_id"]
                self.logger.info(f"撤销了用户 {user_id} 的令牌")
                
                return True
            
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """
        清理过期令牌
        
        Returns:
            int: 清理的令牌数量
        """
        async with self._lock:
            now = datetime.now()
            expired_tokens = []
            
            for token, info in self._active_tokens.items():
                if info["expires_at"] < now:
                    expired_tokens.append(token)
            
            # 移除过期令牌
            for token in expired_tokens:
                del self._active_tokens[token]
                self._blacklisted_tokens.discard(token)
            
            if expired_tokens:
                self.logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")
            
            return len(expired_tokens)
    
    async def create_session(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建用户会话
        
        Args:
            user_id: 用户ID
            metadata: 会话元数据
            
        Returns:
            str: 会话ID
        """
        async with self._lock:
            session_id = self._generate_session_id()
            
            # 检查用户会话数量限制
            user_sessions = [s for s in self._user_sessions.values() 
                           if s["user_id"] == user_id and s["is_active"]]
            
            if len(user_sessions) >= self.max_sessions_per_user:
                # 移除最旧的会话
                oldest_session = min(user_sessions, key=lambda x: x["created_at"])
                await self.invalidate_session(oldest_session["session_id"])
            
            # 创建新会话
            session_info = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now(),
                "last_active": datetime.now(),
                "expires_at": datetime.now() + timedelta(minutes=self.session_timeout),
                "is_active": True,
                "metadata": metadata or {}
            }
            
            self._user_sessions[session_id] = session_info
            
            self.logger.info(f"为用户 {user_id} 创建了新会话: {session_id}")
            
            return session_id
    
    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        验证会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 会话信息，如果无效则返回None
        """
        async with self._lock:
            if session_id not in self._user_sessions:
                return None
            
            session = self._user_sessions[session_id]
            
            # 检查会话是否活跃
            if not session["is_active"]:
                return None
            
            # 检查会话是否过期
            if session["expires_at"] < datetime.now():
                session["is_active"] = False
                return None
            
            # 更新最后活跃时间
            session["last_active"] = datetime.now()
            
            return session.copy()
    
    async def invalidate_session(self, session_id: str) -> bool:
        """
        使会话失效
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功使会话失效
        """
        async with self._lock:
            if session_id in self._user_sessions:
                self._user_sessions[session_id]["is_active"] = False
                self._user_sessions[session_id]["invalidated_at"] = datetime.now()
                
                user_id = self._user_sessions[session_id]["user_id"]
                self.logger.info(f"使用户 {user_id} 的会话失效: {session_id}")
                
                return True
            
            return False
    
    async def get_user_permissions(self, user_id: str, force_refresh: bool = False) -> List[str]:
        """
        获取用户权限（带缓存）
        
        Args:
            user_id: 用户ID
            force_refresh: 是否强制刷新缓存
            
        Returns:
            List[str]: 用户权限列表
        """
        cache_key = f"permissions:{user_id}"
        
        async with self._lock:
            # 检查缓存
            if not force_refresh and cache_key in self._permission_cache:
                cache_info = self._permission_cache[cache_key]
                cache_expires = cache_info["expires_at"]
                
                if cache_expires > datetime.now():
                    return cache_info["permissions"]
            
            # 缓存过期或需要刷新，从数据源获取权限
            # 这里应该调用具体的权限获取逻辑
            permissions = await self._fetch_user_permissions(user_id)
            
            # 更新缓存
            self._permission_cache[cache_key] = {
                "permissions": permissions,
                "expires_at": datetime.now() + timedelta(minutes=self.permission_cache_ttl),
                "cached_at": datetime.now()
            }
            
            return permissions
    
    async def _fetch_user_permissions(self, user_id: str) -> List[str]:
        """
        从数据源获取用户权限（子类实现）
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[str]: 权限列表
        """
        # 默认实现，子类应该重写这个方法
        return []
    
    def _generate_token(self) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(32)
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = str(int(datetime.now().timestamp()))
        random_part = secrets.token_hex(16)
        return hashlib.sha256(f"{timestamp}{random_part}".encode()).hexdigest()
    
    def get_status(self) -> AuthStatus:
        """获取认证状态"""
        return self.status
    
    def set_status(self, status: AuthStatus) -> None:
        """设置认证状态"""
        old_status = self.status
        self.status = status
        self.logger.info(f"认证组件 {self.name} 状态变更: {old_status.value} -> {status.value}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取组件元数据"""
        metadata = self.metadata.copy()
        
        # 添加统计信息
        metadata.update({
            "active_tokens_count": len([t for t in self._active_tokens.values() if t["is_active"]]),
            "active_sessions_count": len([s for s in self._user_sessions.values() if s["is_active"]]),
            "blacklisted_tokens_count": len(self._blacklisted_tokens),
            "cached_permissions_count": len(self._permission_cache)
        })
        
        return metadata
    
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
        self.created_at = datetime.now()
        self.last_login = None
        self.login_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInfo':
        """从字典创建"""
        instance = cls(
            user_id=data.get("user_id", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            metadata=data.get("metadata", {})
        )
        
        # 解析时间字段
        if "created_at" in data:
            try:
                instance.created_at = datetime.fromisoformat(data["created_at"])
            except:
                pass
        
        if "last_login" in data and data["last_login"]:
            try:
                instance.last_login = datetime.fromisoformat(data["last_login"])
            except:
                pass
        
        instance.login_count = data.get("login_count", 0)
        
        return instance
    
    def has_role(self, role: str) -> bool:
        """检查是否有指定角色"""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        return permission in self.permissions
    
    def has_any_role(self, roles: List[str]) -> bool:
        """检查是否有任意一个指定角色"""
        return any(role in self.roles for role in roles)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """检查是否有所有指定权限"""
        return all(permission in self.permissions for permission in permissions)
    
    def update_login(self) -> None:
        """更新登录信息"""
        self.last_login = datetime.now()
        self.login_count += 1 