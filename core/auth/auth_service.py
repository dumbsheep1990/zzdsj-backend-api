"""
认证服务
整合用户管理和权限管理的功能，提供统一的认证授权接口
"""

import jwt
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .user_manager import UserManager
from .permission_manager import PermissionManager
from app.utils.core.config import get_config

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务 - Core层业务逻辑"""
    
    def __init__(self, db: Session):
        """初始化认证服务"""
        self.db = db
        self.user_manager = UserManager(db)
        self.permission_manager = PermissionManager(db)
        
        # JWT配置
        self.jwt_secret = get_config("security", "jwt_secret_key", 
                                   default="23f0767704249cd7be7181a0dad23c74e0739c98ce54d7140fc2e94dfa584fb0")
        self.jwt_algorithm = get_config("security", "jwt_algorithm", default="HS256")
        self.access_token_expire_minutes = get_config("security", "access_token_expire_minutes", default=30)
        self.refresh_token_expire_days = get_config("security", "refresh_token_expire_days", default=7)
    
    # ============ 认证相关 ============
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录 - 业务逻辑层"""
        try:
            # 用户认证
            auth_result = await self.user_manager.authenticate_user(username, password)
            if not auth_result["success"]:
                return auth_result
            
            user_data = auth_result["data"]
            
            # 生成访问令牌
            access_token = self._create_access_token(user_data)
            refresh_token = self._create_refresh_token(user_data)
            
            # 获取用户权限和角色
            permissions = await self.permission_manager.get_user_permissions(user_data["id"])
            roles = await self.permission_manager.get_user_roles(user_data["id"])
            
            return {
                "success": True,
                "data": {
                    "user": user_data,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": self.access_token_expire_minutes * 60,
                    "permissions": permissions.get("data", []),
                    "roles": roles.get("data", [])
                }
            }
            
        except Exception as e:
            logger.error(f"用户登录失败: {str(e)}")
            return {
                "success": False,
                "error": f"登录失败: {str(e)}",
                "error_code": "LOGIN_FAILED"
            }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新访问令牌"""
        try:
            # 验证刷新令牌
            payload = self._verify_token(refresh_token, token_type="refresh")
            if not payload:
                return {
                    "success": False,
                    "error": "无效的刷新令牌",
                    "error_code": "INVALID_REFRESH_TOKEN"
                }
            
            user_id = payload.get("sub")
            if not user_id:
                return {
                    "success": False,
                    "error": "令牌格式错误",
                    "error_code": "INVALID_TOKEN_FORMAT"
                }
            
            # 获取用户信息
            user_result = await self.user_manager.get_user_profile(user_id)
            if not user_result["success"]:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            user_data = user_result["data"]
            
            # 检查用户是否仍然激活
            if not user_data["is_active"]:
                return {
                    "success": False,
                    "error": "用户账户已被禁用",
                    "error_code": "USER_DISABLED"
                }
            
            # 生成新的访问令牌
            new_access_token = self._create_access_token(user_data)
            
            return {
                "success": True,
                "data": {
                    "access_token": new_access_token,
                    "token_type": "bearer",
                    "expires_in": self.access_token_expire_minutes * 60
                }
            }
            
        except Exception as e:
            logger.error(f"刷新令牌失败: {str(e)}")
            return {
                "success": False,
                "error": f"刷新令牌失败: {str(e)}",
                "error_code": "REFRESH_FAILED"
            }
    
    async def logout(self, user_id: str, token: str) -> Dict[str, Any]:
        """用户登出"""
        try:
            # 这里可以实现令牌黑名单机制
            # 目前简单返回成功
            return {
                "success": True,
                "data": {
                    "message": "登出成功"
                }
            }
            
        except Exception as e:
            logger.error(f"用户登出失败: {str(e)}")
            return {
                "success": False,
                "error": f"登出失败: {str(e)}",
                "error_code": "LOGOUT_FAILED"
            }
    
    # ============ 令牌验证 ============
    
    async def verify_access_token(self, token: str) -> Dict[str, Any]:
        """验证访问令牌"""
        try:
            payload = self._verify_token(token, token_type="access")
            if not payload:
                return {
                    "success": False,
                    "error": "无效的访问令牌",
                    "error_code": "INVALID_ACCESS_TOKEN"
                }
            
            user_id = payload.get("sub")
            if not user_id:
                return {
                    "success": False,
                    "error": "令牌格式错误",
                    "error_code": "INVALID_TOKEN_FORMAT"
                }
            
            # 获取用户信息
            user_result = await self.user_manager.get_user_profile(user_id)
            if not user_result["success"]:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }
            
            user_data = user_result["data"]
            
            # 检查用户是否仍然激活
            if not user_data["is_active"]:
                return {
                    "success": False,
                    "error": "用户账户已被禁用",
                    "error_code": "USER_DISABLED"
                }
            
            return {
                "success": True,
                "data": {
                    "user": user_data,
                    "token_payload": payload
                }
            }
            
        except Exception as e:
            logger.error(f"验证访问令牌失败: {str(e)}")
            return {
                "success": False,
                "error": f"令牌验证失败: {str(e)}",
                "error_code": "TOKEN_VERIFICATION_FAILED"
            }
    
    # ============ 权限检查 ============
    
    async def check_permission(self, user_id: str, permission_name: str) -> bool:
        """检查用户权限"""
        return await self.permission_manager.check_user_permission(user_id, permission_name)
    
    async def check_resource_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户资源权限"""
        return await self.permission_manager.check_user_resource_permission(user_id, resource, action)
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """获取用户上下文信息（包含权限和角色）"""
        try:
            # 获取用户基本信息
            user_result = await self.user_manager.get_user_profile(user_id)
            if not user_result["success"]:
                return user_result
            
            # 获取用户权限和角色
            permissions = await self.permission_manager.get_user_permissions(user_id)
            roles = await self.permission_manager.get_user_roles(user_id)
            
            return {
                "success": True,
                "data": {
                    "user": user_result["data"],
                    "permissions": permissions.get("data", []),
                    "roles": roles.get("data", [])
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户上下文失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户上下文失败: {str(e)}",
                "error_code": "GET_CONTEXT_FAILED"
            }
    
    # ============ 用户管理代理方法 ============
    
    async def register_user(self, username: str, email: str, password: str,
                          full_name: str = None, role: str = "user") -> Dict[str, Any]:
        """用户注册"""
        return await self.user_manager.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role
        )
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        return await self.user_manager.change_password(user_id, old_password, new_password)
    
    async def update_profile(self, user_id: str, **updates) -> Dict[str, Any]:
        """更新用户资料"""
        return await self.user_manager.update_user_profile(user_id, **updates)
    
    # ============ 私有方法 ============
    
    def _create_access_token(self, user_data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "role": user_data["role"],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": user_data["id"],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                return None
            
            # 检查过期时间
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("令牌已过期")
            return None
        except jwt.InvalidTokenError:
            logger.warning("无效的令牌")
            return None
        except Exception as e:
            logger.error(f"令牌验证错误: {str(e)}")
            return None
    
    # ============ 权限装饰器 ============
    
    def require_auth(self):
        """认证检查装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 从请求上下文获取令牌
                token = kwargs.get('access_token') or getattr(args[0], 'access_token', None)
                if not token:
                    raise PermissionError("缺少访问令牌")
                
                # 验证令牌
                verify_result = await self.verify_access_token(token)
                if not verify_result["success"]:
                    raise PermissionError(f"令牌验证失败: {verify_result['error']}")
                
                # 将用户信息添加到上下文
                kwargs['current_user'] = verify_result["data"]["user"]
                kwargs['current_user_id'] = verify_result["data"]["user"]["id"]
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_permission(self, permission_name: str):
        """权限检查装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 先进行认证检查
                auth_decorator = self.require_auth()
                authenticated_func = auth_decorator(func)
                
                # 获取用户ID
                user_id = kwargs.get('current_user_id')
                if not user_id:
                    raise PermissionError("未找到用户信息")
                
                # 检查权限
                has_permission = await self.check_permission(user_id, permission_name)
                if not has_permission:
                    raise PermissionError(f"缺少权限: {permission_name}")
                
                return await authenticated_func(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_resource_permission(self, resource: str, action: str):
        """资源权限检查装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 先进行认证检查
                auth_decorator = self.require_auth()
                authenticated_func = auth_decorator(func)
                
                # 获取用户ID
                user_id = kwargs.get('current_user_id')
                if not user_id:
                    raise PermissionError("未找到用户信息")
                
                # 检查资源权限
                has_permission = await self.check_resource_permission(user_id, resource, action)
                if not has_permission:
                    raise PermissionError(f"缺少权限: {resource}:{action}")
                
                return await authenticated_func(*args, **kwargs)
            return wrapper
        return decorator 