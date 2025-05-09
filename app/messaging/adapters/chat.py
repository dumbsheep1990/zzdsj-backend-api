"""
聊天适配器
提供与聊天系统的集成接口
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
import json

from fastapi.responses import StreamingResponse

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage
)
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service
from app.messaging.adapters.base import BaseAdapter
from app.messaging.adapters.llama_index import LlamaIndexAdapter
from app.frameworks.llamaindex.chat import create_chat_engine

logger = logging.getLogger(__name__)


class ChatAdapter(BaseAdapter):
    """
    聊天适配器
    为聊天模块提供统一的消息处理接口
    """
    
    def __init__(
        self,
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None,
        llama_index_adapter: Optional[LlamaIndexAdapter] = None
    ):
        """
        初始化聊天适配器
        
        参数:
            message_service: 消息服务实例，如不提供则获取全局实例
            stream_service: 流服务实例，如不提供则获取全局实例
            llama_index_adapter: LlamaIndex适配器实例，如不提供则创建新实例
        """
        super().__init__(message_service, stream_service)
        self.llama_index_adapter = llama_index_adapter or LlamaIndexAdapter(
            message_service, stream_service
        )
    
    async def process_messages(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        memory_key: Optional[str] = None
    ) -> List[Message]:
        """
        处理聊天消息
        
        参数:
            messages: 聊天消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            memory_key: 记忆键，用于管理聊天历史
            
        返回:
            处理后的消息列表
        """
        # 处理历史记忆逻辑
        memory_messages = []
        if memory_key:
            # 这里可以添加从缓存中获取历史记忆的逻辑
            # 例如：memory_messages = await self._get_chat_memory(memory_key)
            pass
        
        # 合并历史记忆和当前消息
        all_messages = memory_messages + messages
        
        # 使用LlamaIndex适配器处理消息
        response_messages = await self.llama_index_adapter.process_messages(
            messages=all_messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt
        )
        
        # 处理保存记忆逻辑
        if memory_key and response_messages:
            # 这里可以添加保存历史记忆的逻辑
            # 例如：await self._save_chat_memory(memory_key, all_messages + response_messages)
            pass
        
        return response_messages
    
    async def stream_messages(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None,
        memory_key: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        流式处理聊天消息
        
        参数:
            messages: 聊天消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            memory_key: 记忆键，用于管理聊天历史
            
        返回:
            消息流生成器
        """
        # 处理历史记忆逻辑
        memory_messages = []
        if memory_key:
            # 这里可以添加从缓存中获取历史记忆的逻辑
            # 例如：memory_messages = await self._get_chat_memory(memory_key)
            pass
        
        # 合并历史记忆和当前消息
        all_messages = memory_messages + messages
        
        # 使用LlamaIndex适配器流式处理消息
        stream_generator = await self.llama_index_adapter.stream_messages(
            messages=all_messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt,
            stream_id=stream_id
        )
        
        # 收集所有消息用于保存记忆
        if memory_key:
            collected_messages = []
            async for message in stream_generator:
                collected_messages.append(message)
                yield message
                
            # 在流结束后保存记忆
            # 例如：await self._save_chat_memory(memory_key, all_messages + collected_messages)
        else:
            # 直接传递消息流
            async for message in stream_generator:
                yield message
    
    async def to_sse_response(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None,
        memory_key: Optional[str] = None
    ) -> StreamingResponse:
        """
        转换为SSE响应
        
        参数:
            messages: 聊天消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            memory_key: 记忆键，用于管理聊天历史
            
        返回:
            SSE响应对象
        """
        # 处理历史记忆逻辑
        memory_messages = []
        if memory_key:
            # 这里可以添加从缓存中获取历史记忆的逻辑
            # 例如：memory_messages = await self._get_chat_memory(memory_key)
            pass
        
        # 合并历史记忆和当前消息
        all_messages = memory_messages + messages
        
        # 使用LlamaIndex适配器创建SSE响应
        return await self.llama_index_adapter.to_sse_response(
            messages=all_messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt,
            stream_id=stream_id
        )
    
    def to_json_response(
        self,
        messages: List[Message],
        include_metadata: bool = False,
        include_history: bool = False,
        memory_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        转换为JSON响应
        
        参数:
            messages: 聊天消息列表
            include_metadata: 是否包含元数据
            include_history: 是否包含历史记录
            memory_key: 记忆键，用于获取历史记录
            
        返回:
            JSON响应字典
        """
        response = self.llama_index_adapter.to_json_response(
            messages=messages,
            include_metadata=include_metadata
        )
        
        # 添加历史记录
        if include_history and memory_key:
            # 这里可以添加获取历史记录的逻辑
            # 例如：history = self._get_chat_history(memory_key)
            # response["history"] = history
            pass
        
        return response
    
    async def process_conversation(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_id: Optional[str] = None
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        处理完整的对话
        
        参数:
            user_message: 用户消息内容
            conversation_id: 对话ID，用于关联历史记录
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream: 是否流式处理
            stream_id: 流ID
            
        返回:
            处理后的响应对象
        """
        # 创建用户消息
        message = TextMessage(
            content=user_message,
            role=MessageRole.USER
        )
        
        # 处理消息
        if stream:
            return await self.to_sse_response(
                messages=[message],
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt,
                stream_id=stream_id,
                memory_key=conversation_id
            )
        else:
            response_messages = await self.process_messages(
                messages=[message],
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt,
                memory_key=conversation_id
            )
            
            return self.to_json_response(
                messages=response_messages,
                include_metadata=False,
                include_history=True,
                memory_key=conversation_id
            )
    
    # 辅助方法，可以在实现中添加
    async def _get_chat_memory(self, memory_key: str) -> List[Message]:
        """从缓存中获取聊天历史记忆"""
        # 实现获取历史记忆的逻辑
        return []
    
    async def _save_chat_memory(self, memory_key: str, messages: List[Message]) -> None:
        """保存聊天历史记忆到缓存"""
        # 实现保存历史记忆的逻辑
        pass
    
    def _get_chat_history(self, memory_key: str) -> List[Dict[str, Any]]:
        """获取格式化的聊天历史记录"""
        # 实现获取格式化历史记录的逻辑
        return []
