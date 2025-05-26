"""
API共享依赖注入系统
提供双层API架构的统一依赖注入和服务容器管理
"""

from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
import logging
from datetime import datetime
import uuid

# 导入数据库和认证相关
from app.utils.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


class BaseServiceContainer(ABC):
    """
    基础服务容器抽象类
    定义服务容器的基本接口和通用功能
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._services = {}
        self._init_core_services()
    
    @abstractmethod
    def _init_core_services(self):
        """初始化核心服务 - 子类必须实现"""
        pass
    
    def get_service(self, service_name: str):
        """获取指定服务"""
        return self._services.get(service_name)
    
    def has_service(self, service_name: str) -> bool:
        """检查服务是否存在"""
        return service_name in self._services
    
    def list_services(self) -> list:
        """列出所有可用服务"""
        return list(self._services.keys())


class RequestContext:
    """
    请求上下文
    包含请求相关的元数据和状态信息
    """
    
    def __init__(
        self,
        request: Request,
        request_id: Optional[str] = None,
        user: Optional[User] = None,
        api_type: str = "unknown"
    ):
        self.request = request
        self.request_id = request_id or str(uuid.uuid4())
        self.user = user
        self.api_type = api_type  # "external" or "internal"
        self.timestamp = datetime.now()
        self.client_ip = self._get_client_ip()
        self.user_agent = request.headers.get("user-agent", "")
        self.method = request.method
        self.url = str(request.url)
        self.path = request.url.path
        self._metadata = {}
    
    def _get_client_ip(self) -> str:
        """获取客户端真实IP"""
        # 优先从代理头获取
        forwarded_for = self.request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = self.request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 回退到直接连接IP
        return getattr(self.request.client, "host", "unknown")
    
    @property
    def user_id(self) -> Optional[str]:
        """获取用户ID"""
        return self.user.id if self.user else None
    
    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.user is not None
    
    @property
    def is_external_api(self) -> bool:
        """检查是否为对外API"""
        return self.api_type == "external"
    
    @property
    def is_internal_api(self) -> bool:
        """检查是否为内部API"""
        return self.api_type == "internal"
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self._metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "api_type": self.api_type,
            "timestamp": self.timestamp.isoformat(),
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "method": self.method,
            "url": self.url,
            "path": self.path,
            "is_authenticated": self.is_authenticated,
            "metadata": self._metadata
        }


class AuthenticationContext:
    """
    认证上下文
    管理不同API层的认证信息
    """
    
    def __init__(
        self,
        user: Optional[User] = None,
        auth_type: str = "none",  # "api_key", "jwt", "none"
        permissions: Optional[list] = None,
        roles: Optional[list] = None
    ):
        self.user = user
        self.auth_type = auth_type
        self.permissions = permissions or []
        self.roles = roles or []
    
    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.user is not None and self.auth_type != "none"
    
    @property
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.user and getattr(self.user, 'is_admin', False)
    
    @property
    def is_super_admin(self) -> bool:
        """检查是否为超级管理员"""
        return self.user and getattr(self.user, 'is_super_admin', False)
    
    def has_permission(self, permission: str) -> bool:
        """检查是否具有指定权限"""
        return permission in self.permissions
    
    def has_role(self, role: str) -> bool:
        """检查是否具有指定角色"""
        return role in self.roles
    
    def has_any_role(self, roles: list) -> bool:
        """检查是否具有任意指定角色"""
        return any(role in self.roles for role in roles)


# 通用依赖注入函数

def get_db_session() -> Session:
    """获取数据库会话"""
    return next(get_db())


async def get_request_context(
    request: Request,
    request_id: Optional[str] = Header(None, alias="x-request-id")
) -> RequestContext:
    """
    获取请求上下文
    根据路径自动判断API类型
    """
    # 根据路径判断API类型
    api_type = "unknown"
    if request.url.path.startswith("/api/external/"):
        api_type = "external"
    elif request.url.path.startswith("/api/internal/"):
        api_type = "internal"
    elif request.url.path.startswith("/api/v1/"):
        api_type = "external"  # v1被认为是对外API
    
    return RequestContext(
        request=request,
        request_id=request_id,
        api_type=api_type
    )


# 认证相关的基础函数

class AuthenticationError(Exception):
    """认证错误"""
    pass


class AuthorizationError(Exception):
    """授权错误"""
    pass


async def authenticate_api_key(api_key: str, db: Session) -> Optional[User]:
    """
    API密钥认证 - 用于对外API
    """
    try:
        # 这里应该实现具体的API密钥验证逻辑
        # 目前返回None，需要根据实际的认证系统实现
        
        # 示例逻辑（需要根据实际情况调整）
        from app.models.api_key import APIKey  # 假设有这个模型
        
        api_key_record = db.query(APIKey).filter(
            APIKey.key == api_key,
            APIKey.is_active == True
        ).first()
        
        if api_key_record:
            return api_key_record.user
        
        return None
    except Exception as e:
        logger.error(f"API密钥认证失败: {str(e)}")
        return None


async def authenticate_jwt_token(token: str, db: Session) -> Optional[User]:
    """
    JWT令牌认证 - 用于内部API
    """
    try:
        # 这里应该实现具体的JWT验证逻辑
        # 目前返回None，需要根据实际的认证系统实现
        
        from jose import jwt
        from app.config import settings
        
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        user_id = payload.get("user_id")
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        
        return None
    except Exception as e:
        logger.error(f"JWT认证失败: {str(e)}")
        return None


def get_api_key_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头提取API密钥"""
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        return authorization[7:]
    
    return authorization


def get_jwt_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头提取JWT令牌"""
    if not authorization:
        return None
    
    if authorization.startswith("Bearer "):
        return authorization[7:]
    
    return None


# 权限检查装饰器生成函数

def require_permissions(*permissions: str):
    """
    权限检查装饰器依赖生成器
    """
    async def permission_checker(
        context: RequestContext = Depends(get_request_context)
    ) -> bool:
        """检查用户是否具有所需权限"""
        if not permissions:
            return True
        
        if not context.is_authenticated:
            raise AuthenticationError("需要认证才能访问")
        
        # 这里应该实现具体的权限检查逻辑
        # 目前简化处理，需要根据实际权限系统实现
        
        try:
            # 获取用户权限
            user_permissions = []  # 从数据库或缓存获取用户权限
            
            # 检查是否具有所有必需权限
            missing_permissions = set(permissions) - set(user_permissions)
            if missing_permissions:
                raise AuthorizationError(f"缺少权限: {', '.join(missing_permissions)}")
            
            return True
            
        except Exception as e:
            logger.error(f"权限检查失败: {str(e)}")
            raise AuthorizationError("权限检查失败")
    
    return permission_checker


def require_roles(*roles: str):
    """
    角色检查装饰器依赖生成器
    """
    async def role_checker(
        context: RequestContext = Depends(get_request_context)
    ) -> bool:
        """检查用户是否具有所需角色"""
        if not roles:
            return True
        
        if not context.is_authenticated:
            raise AuthenticationError("需要认证才能访问")
        
        # 这里应该实现具体的角色检查逻辑
        # 目前简化处理，需要根据实际角色系统实现
        
        try:
            # 获取用户角色
            user_roles = []  # 从数据库或缓存获取用户角色
            
            # 检查是否具有任一必需角色
            if not any(role in user_roles for role in roles):
                raise AuthorizationError(f"需要以下角色之一: {', '.join(roles)}")
            
            return True
            
        except Exception as e:
            logger.error(f"角色检查失败: {str(e)}")
            raise AuthorizationError("角色检查失败")
    
    return role_checker


# 缓存和性能相关依赖

def get_cache_key_prefix(
    context: RequestContext = Depends(get_request_context)
) -> str:
    """
    生成缓存键前缀
    """
    return f"api:{context.api_type}:{context.user_id or 'anonymous'}:{context.path}"


def get_rate_limit_key(
    context: RequestContext = Depends(get_request_context)
) -> str:
    """
    生成限流键
    """
    identifier = context.user_id if context.is_authenticated else context.client_ip
    return f"rate_limit:{context.api_type}:{identifier}:{context.path}"


# 日志记录依赖

def log_api_request(
    context: RequestContext = Depends(get_request_context)
) -> RequestContext:
    """
    记录API请求日志
    """
    logger.info(
        f"API请求: {context.method} {context.path} [{context.api_type}]",
        extra={
            "request_id": context.request_id,
            "user_id": context.user_id,
            "api_type": context.api_type,
            "client_ip": context.client_ip,
            "user_agent": context.user_agent
        }
    )
    return context


# 常用依赖快捷方式

RequireAuthentication = Depends(lambda ctx=Depends(get_request_context): ctx.is_authenticated or AuthenticationError("需要认证"))
RequireAdmin = Depends(require_roles("admin"))
RequireSuperAdmin = Depends(require_roles("super_admin"))

def RequirePermission(*permissions: str):
    """权限检查快捷方式"""
    return Depends(require_permissions(*permissions))

def RequireRole(*roles: str):
    """角色检查快捷方式"""
    return Depends(require_roles(*roles)) 