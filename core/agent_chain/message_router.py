"""
消息路由和转换模块
负责不同Agent之间的消息格式转换和路由
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from datetime import datetime

from app.messaging.core.models import (
    Message, MessageRole, MessageType, TextMessage, 
    ImageMessage, FileMessage, MCPToolMessage
)
from app.messaging.services.message_service import MessageService, get_message_service
from app.models.assistants import Assistant

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    消息路由器，负责在多个Agent之间路由和转换消息
    """
    
    def __init__(self, message_service: Optional[MessageService] = None):
        """初始化消息路由器"""
        self.message_service = message_service or get_message_service()
    
    async def format_for_target_agent(
        self, 
        messages: List[Message], 
        source_agent: Assistant, 
        target_agent: Assistant
    ) -> List[Message]:
        """
        将源Agent的消息转换为目标Agent可接受的格式
        
        Args:
            messages: 需要转换的消息列表
            source_agent: 源Agent信息
            target_agent: 目标Agent信息
            
        Returns:
            转换后的消息列表
        """
        # 如果目标Agent与源Agent使用相同的消息格式，直接返回
        if source_agent.id == target_agent.id or source_agent.config.get("message_format") == target_agent.config.get("message_format"):
            return messages
        
        # 根据目标Agent支持的消息类型进行转换
        target_message_types = target_agent.config.get("supported_message_types", ["text"])
        converted_messages = []
        
        for msg in messages:
            # 文本消息是通用的，直接保留
            if msg.type == MessageType.TEXT:
                converted_messages.append(msg)
                continue
            
            # 处理特殊类型的消息
            if msg.type == MessageType.IMAGE and "image" in target_message_types:
                converted_messages.append(msg)
            elif msg.type == MessageType.FILE and "file" in target_message_types:
                converted_messages.append(msg)
            elif msg.type == MessageType.MCP_TOOL and "mcp_tool" in target_message_types:
                converted_messages.append(msg)
            else:
                # 不支持的消息类型转换为文本
                text_content = self._convert_to_text_description(msg)
                text_msg = TextMessage(
                    content=text_content,
                    role=msg.role
                )
                converted_messages.append(text_msg)
        
        return converted_messages
    
    def _convert_to_text_description(self, message: Message) -> str:
        """
        将不支持的消息类型转换为文本描述
        
        Args:
            message: 需要转换的消息
            
        Returns:
            文本描述
        """
        if message.type == MessageType.IMAGE:
            return f"[图片消息: {message.content.get('alt_text', '图片内容')}]"
        elif message.type == MessageType.FILE:
            return f"[文件消息: {message.content.get('file_name', '文件内容')}]"
        elif message.type == MessageType.MCP_TOOL:
            return f"[工具调用: {message.content.get('tool_name', '工具')} - {message.content.get('result', '工具结果')}]"
        elif message.type == MessageType.VOICE:
            return f"[语音消息: {message.content.get('transcription', '语音内容')}]"
        elif message.type == MessageType.DEEP_RESEARCH:
            return f"[深度研究: {message.content.get('summary', '研究结果')}]"
        elif message.type == MessageType.CODE:
            return f"[代码: {message.content.get('language', 'code')}]\n{message.content.get('code', '')}"
        elif message.type == MessageType.TABLE:
            return f"[表格数据: {message.content.get('caption', '表格内容')}]"
        else:
            return f"[未知消息类型: {message.type}]"
    
    async def extract_final_response(self, messages: List[Message]) -> Message:
        """
        从消息列表中提取最终响应
        
        Args:
            messages: 消息列表
            
        Returns:
            最终响应消息
        """
        # 通常最后一条助手消息是最终响应
        for msg in reversed(messages):
            if msg.role == MessageRole.ASSISTANT:
                return msg
        
        # 如果没有找到助手消息，创建一个空的文本消息
        return TextMessage(
            content="未找到助手响应",
            role=MessageRole.ASSISTANT
        )
    
    async def combine_messages(
        self, 
        messages_list: List[List[Message]]
    ) -> List[Message]:
        """
        合并多组消息
        
        Args:
            messages_list: 多组消息列表
            
        Returns:
            合并后的消息列表
        """
        combined = []
        
        # 遍历每组消息
        for messages in messages_list:
            combined.extend(messages)
        
        return combined


def get_message_router() -> MessageRouter:
    """
    获取消息路由器实例
    
    Returns:
        MessageRouter实例
    """
    return MessageRouter()
