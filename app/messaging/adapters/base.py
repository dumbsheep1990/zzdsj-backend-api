"""
基础适配器
定义适配器的基本接口和共享功能
"""

from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from abc import ABC, abstractmethod

from app.messaging.core.models import Message
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service


class BaseAdapter(ABC):
    """基础适配器抽象类，定义所有适配器的共同接口"""
    
    def __init__(
        self,
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None
    ):
        """
        初始化基础适配器
        
        参数:
            message_service: 消息服务实例，如不提供则获取全局实例
            stream_service: 流服务实例，如不提供则获取全局实例
        """
        self.message_service = message_service or get_message_service()
        self.stream_service = stream_service or get_stream_service()
    
    @abstractmethod
    async def process_messages(self, *args, **kwargs) -> List[Message]:
        """
        处理消息
        
        参数:
            args, kwargs: 适配器特定参数
            
        返回:
            消息列表
        """
        pass
    
    @abstractmethod
    async def stream_messages(self, *args, **kwargs) -> AsyncGenerator[Message, None]:
        """
        流式处理消息
        
        参数:
            args, kwargs: 适配器特定参数
            
        返回:
            消息流生成器
        """
        pass
    
    @abstractmethod
    async def to_sse_response(self, *args, **kwargs):
        """
        转换为SSE响应
        
        参数:
            args, kwargs: 适配器特定参数
            
        返回:
            SSE响应对象
        """
        pass
    
    @abstractmethod
    def to_json_response(self, *args, **kwargs) -> Dict[str, Any]:
        """
        转换为JSON响应
        
        参数:
            args, kwargs: 适配器特定参数
            
        返回:
            JSON响应字典
        """
        pass
