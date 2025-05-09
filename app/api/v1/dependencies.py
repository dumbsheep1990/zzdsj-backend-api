"""
API依赖项和工具函数
提供统一的依赖注入和请求处理机制
"""

from typing import Optional, Dict, Any, List, Type, Callable
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

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


# 请求上下文管理
class RequestContext:
    """请求上下文，保存请求相关的状态和元数据"""
    
    def __init__(self, request: Request):
        """初始化请求上下文"""
        self.request = request
        self.start_time = request.state.start_time if hasattr(request.state, "start_time") else None
        self.trace_id = request.headers.get("X-Request-ID")
        self.metadata = {}
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        """获取元数据"""
        return self.metadata.get(key)
    
    def get_client_info(self) -> Dict[str, str]:
        """获取客户端信息"""
        client_info = {
            "user_agent": self.request.headers.get("User-Agent", ""),
            "host": self.request.client.host if self.request.client else "",
            "headers": dict(self.request.headers)
        }
        return client_info


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
