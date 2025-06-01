"""
API依赖项和工具函数
提供统一的依赖注入和请求处理机制
"""

from typing import Optional, Dict, Any, List, Type, Callable
from fastapi import Depends, HTTPException, Request, status, Header
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
import hashlib
import json

from app.models.database import get_db
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service
from app.messaging.adapters.base import BaseAdapter
from app.messaging.adapters.chat import ChatAdapter
from app.messaging.adapters.agent import AgentAdapter
from app.messaging.adapters.knowledge import KnowledgeAdapter
from app.messaging.adapters.llama_index import LlamaIndexAdapter
from app.messaging.adapters.lightrag import LightRAGAdapter
from app.messaging.core.models import MessageFormat

# 导入共享组件
from app.api.shared.dependencies import (
    BaseServiceContainer, 
    RequestContext,
    get_db_session,
    get_request_context
)
from app.api.shared.exceptions import (
    AuthenticationFailedException,
    RateLimitExceededException,
    InvalidRequestException
)

# 导入数据库模型
from app.utils.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


# 消息服务依赖项
def get_message_adapter(
    message_service: MessageService = Depends(get_message_service),
    stream_service: StreamService = Depends(get_stream_service)
) -> LlamaIndexAdapter:
    """获取基础的LlamaIndex消息适配器"""
    return LlamaIndexAdapter(message_service, stream_service)


def get_chat_adapter(
    message_service: MessageService = Depends(get_message_service),
    stream_service: StreamService = Depends(get_stream_service)
) -> ChatAdapter:
    """获取聊天消息适配器"""
    return ChatAdapter(message_service, stream_service)


def get_agent_adapter(
    message_service: MessageService = Depends(get_message_service),
    stream_service: StreamService = Depends(get_stream_service)
) -> AgentAdapter:
    """获取代理消息适配器"""
    return AgentAdapter(message_service, stream_service)


def get_knowledge_adapter(
    message_service: MessageService = Depends(get_message_service),
    stream_service: StreamService = Depends(get_stream_service)
) -> KnowledgeAdapter:
    """获取知识库消息适配器"""
    return KnowledgeAdapter(message_service, stream_service)


def get_lightrag_adapter(
    message_service: MessageService = Depends(get_message_service),
    stream_service: StreamService = Depends(get_stream_service)
) -> LightRAGAdapter:
    """获取LightRAG知识图谱适配器"""
    return LightRAGAdapter(message_service, stream_service)


# 通用响应格式化器
class ResponseFormatter:
    """API响应格式化器，统一处理不同类型的响应"""
    
    @staticmethod
    def format_success(data: Any, message: str = "操作成功") -> Dict[str, Any]:
        """格式化成功响应"""
        return {
            "status": "success",
            "message": message,
            "data": data
        }
    
    @staticmethod
    def format_error(message: str, code: str = "internal_error", status_code: int = 500) -> Dict[str, Any]:
        """格式化错误响应"""
        return {
            "status": "error",
            "error": {
                "code": code,
                "message": message
            }
        }
    
    @staticmethod
    def format_openai_compatible(data: Any) -> Dict[str, Any]:
        """格式化为OpenAI兼容的响应格式"""
        # 如果已经是OpenAI格式，直接返回
        if isinstance(data, dict) and "choices" in data:
            return data
            
        # 否则转换为OpenAI格式
        message_service = get_message_service()
        return message_service.format_as_openai_response(data)


def get_request_context(request: Request) -> RequestContext:
    """获取请求上下文"""
    return RequestContext(request)


# 权限检查依赖项（示例）
def check_permissions(
    required_permissions: List[str],
    db: Session = Depends(get_db),
    request_context: RequestContext = Depends(get_request_context)
) -> bool:
    """检查用户是否拥有所需权限"""
    # 这里应该实现实际的权限检查逻辑
    # 示例实现
    return True


class V1ServiceContainer(BaseServiceContainer):
    """
    V1 API服务容器 - 专门为第三方API提供精简版服务
    只初始化对外API需要的核心服务
    """
    
    def _init_core_services(self):
        """初始化V1 API核心服务"""
        try:
            # 只初始化对外API需要的服务
            from app.services.assistant_service import AssistantService
            from app.services.chat_service import ChatService
            from app.services.knowledge_service import KnowledgeQueryService
            from app.services.search_service import SearchService
            from app.services.ai_service import AIService
            from app.services.tool_service import ToolService
            
            # 核心业务服务 - 查询版本
            self._services["assistant"] = AssistantService(self.db)
            self._services["chat"] = ChatService(self.db)
            self._services["knowledge"] = KnowledgeQueryService(self.db)  # 只查询
            self._services["search"] = SearchService(self.db)
            
            # AI能力服务
            self._services["ai"] = AIService(self.db)
            
            # 工具调用服务 - 限制版本
            self._services["tools"] = ToolService(self.db, external_api=True)
            
            logger.info("V1 API服务容器初始化完成")
            
        except Exception as e:
            logger.error(f"V1 API服务容器初始化失败: {str(e)}")
            # 不抛出异常，允许服务降级
    
    def get_assistant_service(self):
        """获取助手服务"""
        return self.get_service("assistant")
    
    def get_chat_service(self):
        """获取聊天服务"""
        return self.get_service("chat")
    
    def get_knowledge_service(self):
        """获取知识库服务"""
        return self.get_service("knowledge")
    
    def get_search_service(self):
        """获取搜索服务"""
        return self.get_service("search")
    
    def get_ai_service(self):
        """获取AI服务"""
        return self.get_service("ai")
    
    def get_tools_service(self):
        """获取工具服务"""
        return self.get_service("tools")


class APIKey:
    """API密钥信息类"""
    
    def __init__(
        self,
        key: str,
        user_id: str,
        name: str,
        is_active: bool = True,
        rate_limit: int = 1000,
        allowed_endpoints: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.key = key
        self.user_id = user_id
        self.name = name
        self.is_active = is_active
        self.rate_limit = rate_limit  # 每小时请求限制
        self.allowed_endpoints = allowed_endpoints or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
    
    @property
    def masked_key(self) -> str:
        """返回掩码后的API密钥"""
        if len(self.key) <= 8:
            return "*" * len(self.key)
        return self.key[:4] + "*" * (len(self.key) - 8) + self.key[-4:]


# ================================
# API密钥认证相关
# ================================

def get_api_key_from_header(authorization: Optional[str] = Header(None)) -> str:
    """从请求头提取API密钥"""
    if not authorization:
        raise AuthenticationFailedException("缺少Authorization头")
    
    if not authorization.startswith("Bearer "):
        raise AuthenticationFailedException("Authorization头格式错误，应为 'Bearer <api_key>'")
    
    api_key = authorization[7:]  # 移除 "Bearer " 前缀
    if not api_key or len(api_key) < 10:
        raise AuthenticationFailedException("API密钥格式无效")
    
    return api_key


async def validate_api_key(api_key: str, db: Session) -> APIKey:
    """
    验证API密钥
    这里简化实现，实际应该从数据库查询
    """
    try:
        # TODO: 实际实现应该从数据库查询API密钥
        # 这里简化处理，假设有一个默认的API密钥
        
        # 示例API密钥验证逻辑
        if api_key == "test_api_key_12345":
            return APIKey(
                key=api_key,
                user_id="test_user_001",
                name="测试API密钥",
                is_active=True,
                rate_limit=1000
            )
        
        # 实际实现示例（需要相应的数据库模型）
        """
        from app.models.api_key import APIKeyModel
        
        api_key_record = db.query(APIKeyModel).filter(
            APIKeyModel.key_hash == hashlib.sha256(api_key.encode()).hexdigest(),
            APIKeyModel.is_active == True
        ).first()
        
        if not api_key_record:
            return None
        
        return APIKey(
            key=api_key,
            user_id=api_key_record.user_id,
            name=api_key_record.name,
            is_active=api_key_record.is_active,
            rate_limit=api_key_record.rate_limit,
            allowed_endpoints=api_key_record.allowed_endpoints
        )
        """
        
        return None
        
    except Exception as e:
        logger.error(f"API密钥验证失败: {str(e)}")
        return None


async def get_api_user(
    api_key: str = Depends(get_api_key_from_header),
    db: Session = Depends(get_db)
) -> APIKey:
    """V1 API用户认证 - 基于API密钥"""
    
    # 验证API密钥
    api_key_record = await validate_api_key(api_key, db)
    if not api_key_record:
        raise AuthenticationFailedException("无效的API密钥")
    
    if not api_key_record.is_active:
        raise AuthenticationFailedException("API密钥已被禁用")
    
    return api_key_record


# ================================
# 限流控制相关
# ================================

class RateLimiter:
    """简单的内存限流器"""
    
    def __init__(self):
        self._requests = {}  # {user_id: [(timestamp, endpoint), ...]}
    
    async def check_limit(
        self, 
        user_id: str, 
        endpoint: str, 
        limit: int = 1000, 
        window: int = 3600  # 1小时
    ) -> bool:
        """检查是否超过限流"""
        now = datetime.now()
        window_start = now - timedelta(seconds=window)
        
        # 获取用户请求历史
        if user_id not in self._requests:
            self._requests[user_id] = []
        
        user_requests = self._requests[user_id]
        
        # 清理过期请求
        user_requests[:] = [
            (timestamp, ep) for timestamp, ep in user_requests 
            if timestamp > window_start
        ]
        
        # 检查是否超过限制
        if len(user_requests) >= limit:
            return False
        
        # 记录当前请求
        user_requests.append((now, endpoint))
        return True
    
    async def get_remaining_quota(
        self, 
        user_id: str, 
        limit: int = 1000, 
        window: int = 3600
    ) -> int:
        """获取剩余配额"""
        now = datetime.now()
        window_start = now - timedelta(seconds=window)
        
        if user_id not in self._requests:
            return limit
        
        user_requests = self._requests[user_id]
        current_count = len([
            req for req in user_requests 
            if req[0] > window_start
        ])
        
        return max(0, limit - current_count)


# 全局限流器实例
rate_limiter = RateLimiter()


async def check_api_rate_limit(
    request: Request,
    api_user: APIKey = Depends(get_api_user)
) -> bool:
    """API限流检查"""
    
    endpoint = request.url.path
    rate_limit = api_user.rate_limit or 1000
    
    # 检查是否超过限制
    if not await rate_limiter.check_limit(api_user.user_id, endpoint, rate_limit):
        remaining = await rate_limiter.get_remaining_quota(api_user.user_id, rate_limit)
        raise RateLimitExceededException(
            message=f"API调用频率过高，每小时限制{rate_limit}次",
            retry_after=3600,  # 1小时后重试
            details={
                "rate_limit": rate_limit,
                "remaining": remaining,
                "reset_time": (datetime.now() + timedelta(hours=1)).isoformat()
            }
        )
    
    return True


# ================================
# 数据过滤相关
# ================================

class V1DataFilter:
    """V1 API数据过滤器 - 过滤敏感信息"""
    
    @staticmethod
    def filter_assistant_data(assistant_data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤助手数据 - 只返回第三方需要的字段"""
        if not assistant_data:
            return {}
        
        return {
            "id": assistant_data.get("id"),
            "name": assistant_data.get("name"),
            "description": assistant_data.get("description"),
            "model": assistant_data.get("model"),
            "avatar_url": assistant_data.get("avatar_url"),
            "created_at": assistant_data.get("created_at"),
            "is_public": assistant_data.get("is_public", False),
            "capabilities": assistant_data.get("capabilities", []),
            "tags": assistant_data.get("tags", [])
            # 不返回：system_prompt, config, internal_settings等敏感信息
        }
    
    @staticmethod
    def filter_chat_data(chat_data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤聊天数据"""
        if not chat_data:
            return {}
        
        return {
            "id": chat_data.get("id"),
            "message": chat_data.get("message"),
            "response": chat_data.get("response"),
            "timestamp": chat_data.get("timestamp"),
            "assistant_id": chat_data.get("assistant_id"),
            "status": chat_data.get("status", "completed"),
            "metadata": {
                "tokens_used": chat_data.get("tokens_used"),
                "response_time": chat_data.get("response_time")
            }
            # 不返回：user_id, session_info, internal_logs等
        }
    
    @staticmethod
    def filter_knowledge_data(knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤知识库数据"""
        if not knowledge_data:
            return {}
        
        return {
            "id": knowledge_data.get("id"),
            "title": knowledge_data.get("title"),
            "content": knowledge_data.get("content"),
            "source": knowledge_data.get("source"),
            "relevance_score": knowledge_data.get("relevance_score"),
            "created_at": knowledge_data.get("created_at"),
            "document_type": knowledge_data.get("document_type"),
            "tags": knowledge_data.get("tags", [])
            # 不返回：internal_id, processing_logs, owner_info等
        }


# ================================
# V1专用依赖注入函数
# ================================

async def get_v1_service_container(
    db: Session = Depends(get_db),
    api_user: APIKey = Depends(get_api_user)
) -> V1ServiceContainer:
    """获取V1服务容器"""
    container = V1ServiceContainer(db)
    
    # 可以根据API用户设置特定的服务配置
    # 例如：根据用户权限限制某些服务的功能
    
    return container


async def get_v1_context(
    request: Request,
    api_user: APIKey = Depends(get_api_user),
    _rate_limit: bool = Depends(check_api_rate_limit)
) -> RequestContext:
    """获取V1请求上下文"""
    context = RequestContext(
        request=request,
        user=None,  # V1 API使用APIKey而不是User对象
        api_type="v1_external"
    )
    
    # 设置API用户信息
    context.set_metadata("api_user_id", api_user.user_id)
    context.set_metadata("api_key_name", api_user.name)
    context.set_metadata("rate_limit", api_user.rate_limit)
    
    return context


# ================================
# 工具函数
# ================================

def mask_sensitive_data(data: Any, fields_to_mask: list = None) -> Any:
    """掩码敏感数据"""
    if fields_to_mask is None:
        fields_to_mask = ["password", "token", "key", "secret", "api_key"]
    
    if isinstance(data, dict):
        return {
            key: "***MASKED***" if key.lower() in fields_to_mask else mask_sensitive_data(value, fields_to_mask)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item, fields_to_mask) for item in data]
    else:
        return data


def generate_api_response_metadata(
    api_user: APIKey,
    endpoint: str,
    processing_time: float = None
) -> Dict[str, Any]:
    """生成API响应元数据"""
    metadata = {
        "api_version": "v1",
        "endpoint": endpoint,
        "rate_limit": api_user.rate_limit,
        "timestamp": datetime.now().isoformat()
    }
    
    if processing_time:
        metadata["processing_time"] = f"{processing_time:.3f}s"
    
    return metadata


# ================================
# 常用依赖快捷方式
# ================================

# V1 API认证依赖
V1Auth = Depends(get_api_user)

# V1 API认证 + 限流依赖
V1AuthWithRateLimit = Depends(check_api_rate_limit)

# V1服务容器依赖
V1Services = Depends(get_v1_service_container)

# V1上下文依赖
V1Context = Depends(get_v1_context)
