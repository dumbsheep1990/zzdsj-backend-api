"""
聊天MCP客户端模块
定义聊天类型MCP服务的接口
"""

from abc import abstractmethod
from typing import Dict, Any, Optional, List, Union
from .base import BaseMCPClient, ClientCapability

class ChatMCPClient(BaseMCPClient):
    """聊天类型MCP客户端"""
    
    @property
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        return [ClientCapability.CHAT, ClientCapability.TOOLS]
    
    @abstractmethod
    async def send_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送消息到聊天模型
        
        参数:
            messages: 消息列表，每条消息包含role和content
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            tools: 可用工具列表
            **kwargs: 其他参数
            
        返回:
            模型响应
        """
        pass
    
    @abstractmethod
    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式发送消息到聊天模型
        
        参数:
            messages: 消息列表，每条消息包含role和content
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            tools: 可用工具列表
            **kwargs: 其他参数
            
        返回:
            模型响应流迭代器
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的聊天模型列表
        
        返回:
            模型信息列表
        """
        pass

# 用于类型注解
from typing import AsyncIterator
