"""
消息流处理模块
提供消息流生成和处理功能
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage
)
from app.messaging.core.formatters import format_to_sse

logger = logging.getLogger(__name__)


class MessageStream:
    """消息流处理器"""
    
    def __init__(self):
        """初始化消息流处理器"""
        self.messages = []
        self.queue = asyncio.Queue()
        self.is_streaming = False
    
    async def add_message(self, message: Message):
        """
        添加消息到流中
        
        参数:
            message: 要添加的消息
        """
        self.messages.append(message)
        await self.queue.put(message)
    
    async def start_stream(self):
        """开始流式处理"""
        self.is_streaming = True
        status_message = StatusMessage(
            content={"status": "start"},
            metadata={"timestamp": datetime.now().isoformat()}
        )
        await self.add_message(status_message)
    
    async def end_stream(self):
        """结束流式处理"""
        self.is_streaming = False
        done_message = DoneMessage(
            content={"done": True},
            metadata={"timestamp": datetime.now().isoformat()}
        )
        await self.add_message(done_message)
    
    async def add_error(self, error_message: str, error_code: Optional[str] = None):
        """
        添加错误消息
        
        参数:
            error_message: 错误消息
            error_code: 错误代码
        """
        content = {"message": error_message}
        if error_code:
            content["code"] = error_code
            
        error = ErrorMessage(
            content=content,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        await self.add_message(error)
    
    async def add_text(self, text: str, role: MessageRole = MessageRole.ASSISTANT):
        """
        添加文本消息
        
        参数:
            text: 文本内容
            role: 消息角色
        """
        message = TextMessage(
            content=text,
            role=role,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        await self.add_message(message)
    
    async def add_function_call(
        self, 
        name: str, 
        arguments: Dict[str, Any],
        call_id: Optional[str] = None
    ):
        """
        添加函数调用消息
        
        参数:
            name: 函数名称
            arguments: 函数参数
            call_id: 调用ID
        """
        metadata = {"timestamp": datetime.now().isoformat()}
        if call_id:
            metadata["call_id"] = call_id
            
        message = FunctionCallMessage(
            content={
                "name": name,
                "arguments": arguments
            },
            metadata=metadata
        )
        await self.add_message(message)
        return message.id
    
    async def add_function_return(
        self, 
        name: str, 
        result: Any,
        call_id: Optional[str] = None
    ):
        """
        添加函数返回消息
        
        参数:
            name: 函数名称
            result: 函数结果
            call_id: 调用ID
        """
        content = {
            "name": name,
            "result": result
        }
        
        if call_id:
            content["call_id"] = call_id
        
        message = FunctionReturnMessage(
            role=MessageRole.FUNCTION,
            content=content,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        await self.add_message(message)
    
    async def add_thinking(self, content: str, step: Optional[int] = None):
        """
        添加思考过程消息
        
        参数:
            content: 思考内容
            step: 步骤编号
        """
        metadata = {"timestamp": datetime.now().isoformat()}
        if step is not None:
            metadata["step"] = step
            
        message = ThinkingMessage(
            content=content,
            step=step,
            metadata=metadata
        )
        await self.add_message(message)
    
    async def add_image(self, url: str, caption: Optional[str] = None):
        """
        添加图像消息
        
        参数:
            url: 图像URL
            caption: 图像说明
        """
        content = {"url": url}
        if caption:
            content["caption"] = caption
            
        message = ImageMessage(
            content=content,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        await self.add_message(message)
    
    async def get_message_stream(self) -> AsyncGenerator[Message, None]:
        """
        获取消息流
        
        返回:
            消息流异步生成器
        """
        while True:
            message = await self.queue.get()
            yield message
            self.queue.task_done()
            
            # 如果是完成消息，结束流
            if message.type == MessageType.DONE:
                break
    
    async def get_sse_stream(self) -> AsyncGenerator[str, None]:
        """
        获取SSE格式的消息流
        
        返回:
            SSE格式字符串的异步生成器
        """
        async for message in self.get_message_stream():
            yield format_to_sse(message)


class ChunkMessageStream(MessageStream):
    """块状消息流处理器，用于处理LLM的分块输出"""
    
    def __init__(self):
        """初始化块状消息流处理器"""
        super().__init__()
        self.current_text = ""
        self.last_message_id = None
    
    async def add_text_chunk(self, chunk: str):
        """
        添加文本块
        
        参数:
            chunk: 文本块内容
        """
        self.current_text += chunk
        
        message = TextMessage(
            content=chunk,
            metadata={
                "is_chunk": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if self.last_message_id:
            message.metadata["previous_id"] = self.last_message_id
            
        self.last_message_id = message.id
        await self.add_message(message)
    
    async def finalize_text(self):
        """完成文本流，发送完整文本"""
        if self.current_text:
            message = TextMessage(
                content=self.current_text,
                metadata={
                    "is_final": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            await self.add_message(message)
            self.current_text = ""
            self.last_message_id = None
