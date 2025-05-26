"""
Frontend API专用依赖注入系统
提供JWT/Session认证、用户权限控制、前端特定功能等
"""

from typing import Optional, Dict, Any, Union
from fastapi import Depends, HTTPException, Header, Request, Cookie, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
import jwt
from jose import JWTError

# 导入共享组件
from app.api.shared.dependencies import (
    BaseServiceContainer, 
    RequestContext,
    get_db_session,
    get_request_context
)
from app.api.shared.exceptions import (
    AuthenticationFailedException,
    InsufficientPermissionException,
    InvalidRequestException
)

# 导入数据库模型
from app.utils.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


class FrontendServiceContainer(BaseServiceContainer):
    """
    Frontend API服务容器 - 为前端提供完整功能服务
    初始化前端需要的所有服务
    """
    
    def _init_core_services(self):
        """初始化Frontend API核心服务"""
        try:
            # 导入原项目实际存在的服务
            from app.services.user_service import UserService
            from app.services.assistant_service import AssistantService
            from app.services.chat_service import ChatService
            from app.services.unified_knowledge_service import UnifiedKnowledgeService as KnowledgeService
            from app.services.voice_service import VoiceService
            
            # 用户相关服务
            self._services["user"] = UserService(self.db)
            
            # 核心业务服务 - 基于原项目实际服务
            self._services["assistant"] = AssistantService(self.db)
            self._services["chat"] = ChatService(self.db)
            self._services["knowledge"] = KnowledgeService(self.db)
            
            # 多媒体服务（原项目存在的）
            self._services["voice"] = VoiceService(self.db)
            
            logger.info("Frontend API服务容器初始化完成")
            
        except Exception as e:
            logger.error(f"Frontend API服务容器初始化失败: {str(e)}")
            # 不抛出异常，允许服务降级
    
    def get_user_service(self):
        """获取用户服务"""
        return self.get_service("user")
    
    def get_assistant_service(self):
        """获取助手服务"""
        return self.get_service("assistant")
    
    def get_chat_service(self):
        """获取聊天服务"""
        return self.get_service("chat")
    
    def get_knowledge_service(self):
        """获取知识库服务"""
        return self.get_service("knowledge")
    
    def get_voice_service(self):
        """获取语音服务"""
        return self.get_service("voice")


# ================================
# JWT认证相关
# ================================

def get_jwt_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从请求头提取JWT令牌"""
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    return authorization[7:]  # 移除 "Bearer " 前缀


def get_session_id_from_cookie(session_id: Optional[str] = Cookie(None)) -> Optional[str]:
    """从Cookie提取Session ID"""
    return session_id


async def verify_jwt_token(token: str, db: Session) -> Optional[User]:
    """
    验证JWT令牌并返回用户对象
    """
    try:
        # TODO: 从配置获取JWT密钥
        SECRET_KEY = "your-secret-key"  # 应该从环境变量或配置文件获取
        ALGORITHM = "HS256"
        
        # 解码JWT令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            return None
        
        # 从数据库获取用户
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except JWTError as e:
        logger.warning(f"JWT验证失败: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"JWT验证异常: {str(e)}")
        return None


async def verify_session(session_id: str, db: Session) -> Optional[User]:
    """
    验证Session ID并返回用户对象
    """
    try:
        # TODO: 实际实现应该从Session存储（Redis等）获取用户信息
        # 这里简化处理，假设有一个Session模型
        
        """
        from app.models.session import UserSession
        
        session = db.query(UserSession).filter(
            UserSession.session_id == session_id,
            UserSession.expires_at > datetime.now(),
            UserSession.is_active == True
        ).first()
        
        if not session:
            return None
        
        user = db.query(User).filter(User.id == session.user_id).first()
        
        if not user or not user.is_active:
            return None
        
        # 更新最后访问时间
        session.last_accessed_at = datetime.now()
        db.commit()
        
        return user
        """
        
        # 简化实现，返回None
        return None
        
    except Exception as e:
        logger.error(f"Session验证失败: {str(e)}")
        return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    jwt_token: Optional[str] = Depends(get_jwt_token_from_header),
    session_id: Optional[str] = Depends(get_session_id_from_cookie)
) -> User:
    """Frontend用户认证 - 基于JWT或Session"""
    
    user = None
    
    # 优先尝试JWT认证
    if jwt_token:
        user = await verify_jwt_token(jwt_token, db)
        if user:
            logger.debug(f"用户通过JWT认证: {user.id}")
            return user
    
    # 回退到Session认证
    if session_id:
        user = await verify_session(session_id, db)
        if user:
            logger.debug(f"用户通过Session认证: {user.id}")
            return user
    
    # 认证失败
    raise AuthenticationFailedException("需要用户登录")


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
    jwt_token: Optional[str] = Depends(get_jwt_token_from_header),
    session_id: Optional[str] = Depends(get_session_id_from_cookie)
) -> Optional[User]:
    """可选的用户认证 - 允许匿名访问"""
    
    try:
        return await get_current_user(request, db, jwt_token, session_id)
    except AuthenticationFailedException:
        return None


# ================================
# 权限控制相关
# ================================

class UserPermissions:
    """用户权限枚举"""
    
    # 基础权限
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    
    # 知识库权限
    KNOWLEDGE_CREATE = "knowledge.create"
    KNOWLEDGE_EDIT = "knowledge.edit"
    KNOWLEDGE_DELETE = "knowledge.delete"
    KNOWLEDGE_SHARE = "knowledge.share"
    
    # 助手权限
    ASSISTANT_CREATE = "assistant.create"
    ASSISTANT_EDIT = "assistant.edit"
    ASSISTANT_DELETE = "assistant.delete"
    ASSISTANT_SHARE = "assistant.share"
    
    # 工作空间权限
    WORKSPACE_CREATE = "workspace.create"
    WORKSPACE_MANAGE = "workspace.manage"
    WORKSPACE_INVITE = "workspace.invite"
    
    # 高级权限
    ADMIN_ACCESS = "admin.access"
    SYSTEM_CONFIG = "system.config"


async def check_user_permission(
    permission: str,
    user: User = Depends(get_current_user)
) -> bool:
    """检查用户是否具有指定权限"""
    try:
        # TODO: 实现具体的权限检查逻辑
        # 这里简化处理，可以从用户的角色或权限表查询
        
        # 示例权限检查逻辑
        if hasattr(user, 'permissions'):
            return permission in user.permissions
        
        # 如果没有具体的权限系统，可以基于用户角色判断
        if hasattr(user, 'is_admin') and user.is_admin:
            return True  # 管理员拥有所有权限
        
        # 基础用户拥有基础权限
        basic_permissions = [
            UserPermissions.READ,
            UserPermissions.KNOWLEDGE_CREATE,
            UserPermissions.ASSISTANT_CREATE,
            UserPermissions.WORKSPACE_CREATE
        ]
        
        return permission in basic_permissions
        
    except Exception as e:
        logger.error(f"权限检查失败: {str(e)}")
        return False


def require_permission(permission: str):
    """权限检查装饰器依赖生成器"""
    async def permission_checker(
        user: User = Depends(get_current_user)
    ) -> User:
        """检查用户是否具有所需权限"""
        has_permission = await check_user_permission(permission, user)
        
        if not has_permission:
            raise InsufficientPermissionException(
                message=f"需要 {permission} 权限",
                required_permission=permission
            )
        
        return user
    
    return permission_checker


# ================================
# 数据过滤相关
# ================================

class FrontendDataFilter:
    """Frontend API数据过滤器 - 返回前端需要的完整数据"""
    
    @staticmethod
    def filter_user_data(user_data: Dict[str, Any], include_sensitive: bool = False) -> Dict[str, Any]:
        """过滤用户数据"""
        if not user_data:
            return {}
        
        result = {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "nickname": user_data.get("nickname"),
            "email": user_data.get("email"),
            "avatar_url": user_data.get("avatar_url"),
            "created_at": user_data.get("created_at"),
            "updated_at": user_data.get("updated_at"),
            "is_active": user_data.get("is_active"),
            "preferences": user_data.get("preferences", {}),
            "settings": user_data.get("settings", {}),
            "profile": user_data.get("profile", {})
        }
        
        # 包含敏感信息（用户自己查看时）
        if include_sensitive:
            result.update({
                "phone": user_data.get("phone"),
                "last_login_at": user_data.get("last_login_at"),
                "login_count": user_data.get("login_count"),
                "permissions": user_data.get("permissions", []),
                "roles": user_data.get("roles", [])
            })
        
        return result
    
    @staticmethod
    def filter_assistant_data(assistant_data: Dict[str, Any], include_private: bool = False) -> Dict[str, Any]:
        """过滤助手数据 - 返回前端需要的完整信息"""
        if not assistant_data:
            return {}
        
        result = {
            "id": assistant_data.get("id"),
            "name": assistant_data.get("name"),
            "description": assistant_data.get("description"),
            "model": assistant_data.get("model"),
            "avatar_url": assistant_data.get("avatar_url"),
            "created_at": assistant_data.get("created_at"),
            "updated_at": assistant_data.get("updated_at"),
            "is_public": assistant_data.get("is_public", False),
            "capabilities": assistant_data.get("capabilities", []),
            "tags": assistant_data.get("tags", []),
            "category": assistant_data.get("category"),
            "usage_count": assistant_data.get("usage_count", 0),
            "rating": assistant_data.get("rating", 0),
            "owner": assistant_data.get("owner", {}),
            "metadata": assistant_data.get("metadata", {})
        }
        
        # 包含私有信息（所有者查看时）
        if include_private:
            result.update({
                "system_prompt": assistant_data.get("system_prompt"),
                "config": assistant_data.get("config", {}),
                "training_data": assistant_data.get("training_data", []),
                "internal_settings": assistant_data.get("internal_settings", {}),
                "usage_analytics": assistant_data.get("usage_analytics", {})
            })
        
        return result
    
    @staticmethod
    def filter_chat_data(chat_data: Dict[str, Any], include_metadata: bool = True) -> Dict[str, Any]:
        """过滤聊天数据"""
        if not chat_data:
            return {}
        
        result = {
            "id": chat_data.get("id"),
            "title": chat_data.get("title"),
            "messages": chat_data.get("messages", []),
            "assistant_id": chat_data.get("assistant_id"),
            "created_at": chat_data.get("created_at"),
            "updated_at": chat_data.get("updated_at"),
            "status": chat_data.get("status", "active"),
            "is_pinned": chat_data.get("is_pinned", False),
            "tags": chat_data.get("tags", [])
        }
        
        if include_metadata:
            result.update({
                "message_count": chat_data.get("message_count", 0),
                "total_tokens": chat_data.get("total_tokens", 0),
                "last_message_at": chat_data.get("last_message_at"),
                "context_summary": chat_data.get("context_summary"),
                "participants": chat_data.get("participants", [])
            })
        
        return result
    
    @staticmethod
    def filter_knowledge_base_data(kb_data: Dict[str, Any], include_stats: bool = False) -> Dict[str, Any]:
        """过滤知识库数据"""
        if not kb_data:
            return {}
        
        result = {
            "id": kb_data.get("id"),
            "name": kb_data.get("name"),
            "description": kb_data.get("description"),
            "created_at": kb_data.get("created_at"),
            "updated_at": kb_data.get("updated_at"),
            "is_public": kb_data.get("is_public", False),
            "category": kb_data.get("category"),
            "tags": kb_data.get("tags", []),
            "owner": kb_data.get("owner", {}),
            "permissions": kb_data.get("permissions", {}),
            "settings": kb_data.get("settings", {})
        }
        
        if include_stats:
            result.update({
                "document_count": kb_data.get("document_count", 0),
                "total_size": kb_data.get("total_size", 0),
                "index_status": kb_data.get("index_status"),
                "last_indexed_at": kb_data.get("last_indexed_at"),
                "usage_stats": kb_data.get("usage_stats", {}),
                "performance_metrics": kb_data.get("performance_metrics", {})
            })
        
        return result


# ================================
# Frontend专用依赖注入函数
# ================================

async def get_frontend_service_container(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> FrontendServiceContainer:
    """获取Frontend服务容器"""
    container = FrontendServiceContainer(db)
    
    # 可以根据用户设置特定的服务配置
    # 例如：根据用户偏好设置个性化配置
    
    return container


async def get_frontend_context(
    request: Request,
    user: User = Depends(get_current_user)
) -> RequestContext:
    """获取Frontend请求上下文"""
    context = RequestContext(
        request=request,
        user=user,
        api_type="frontend"
    )
    
    # 设置前端特定的上下文信息
    context.set_metadata("user_preferences", getattr(user, 'preferences', {}))
    context.set_metadata("user_permissions", getattr(user, 'permissions', []))
    context.set_metadata("workspace_id", request.headers.get("X-Workspace-ID"))
    
    return context


async def get_optional_frontend_context(
    request: Request,
    user: Optional[User] = Depends(get_optional_user)
) -> RequestContext:
    """获取可选的Frontend请求上下文 - 允许匿名访问"""
    context = RequestContext(
        request=request,
        user=user,
        api_type="frontend"
    )
    
    if user:
        context.set_metadata("user_preferences", getattr(user, 'preferences', {}))
        context.set_metadata("user_permissions", getattr(user, 'permissions', []))
    
    context.set_metadata("workspace_id", request.headers.get("X-Workspace-ID"))
    
    return context


# ================================
# 工具函数
# ================================

def check_resource_ownership(resource_user_id: str, current_user: User) -> bool:
    """检查资源所有权"""
    return resource_user_id == current_user.id or getattr(current_user, 'is_admin', False)


def check_workspace_access(workspace_id: str, user: User) -> bool:
    """检查工作空间访问权限"""
    # TODO: 实现具体的工作空间权限检查
    # 这里简化处理
    return True


def get_user_context_data(user: User) -> Dict[str, Any]:
    """获取用户上下文数据"""
    return {
        "id": user.id,
        "username": getattr(user, 'username', ''),
        "preferences": getattr(user, 'preferences', {}),
        "settings": getattr(user, 'settings', {}),
        "permissions": getattr(user, 'permissions', []),
        "roles": getattr(user, 'roles', [])
    }


# ================================
# 常用依赖快捷方式
# ================================

# Frontend用户认证依赖
FrontendAuth = Depends(get_current_user)

# 可选认证依赖（允许匿名）
FrontendOptionalAuth = Depends(get_optional_user)

# Frontend服务容器依赖
FrontendServices = Depends(get_frontend_service_container)

# Frontend上下文依赖
FrontendContext = Depends(get_frontend_context)

# 可选上下文依赖
FrontendOptionalContext = Depends(get_optional_frontend_context)

# 权限检查快捷方式
def RequirePermission(permission: str):
    """权限检查快捷方式"""
    return Depends(require_permission(permission))

# 常用权限依赖
RequireKnowledgeCreate = RequirePermission(UserPermissions.KNOWLEDGE_CREATE)
RequireAssistantCreate = RequirePermission(UserPermissions.ASSISTANT_CREATE)
RequireWorkspaceManage = RequirePermission(UserPermissions.WORKSPACE_MANAGE)
RequireAdminAccess = RequirePermission(UserPermissions.ADMIN_ACCESS) 