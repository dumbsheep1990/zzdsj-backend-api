"""
消息格式转换器
提供消息与不同格式(SSE、JSON等)之间的转换功能
"""

from typing import Dict, Any, List, Optional, Union, AsyncGenerator
import json
import time
from datetime import datetime
from app.messaging.core.models import Message, MessageType, MessageRole, DoneMessage

# 导入压缩上下文消息模块
from app.messaging.core.compressed_context import CompressedContextMessage, convert_compressed_context_to_internal


def format_to_json(message: Message) -> str:
    """
    将消息转换为JSON字符串格式
    
    参数:
        message: 待转换的消息对象
        
    返回:
        JSON字符串
    """
    return message.to_json()


def format_to_sse(message: Message, event_name: Optional[str] = None) -> str:
    """
    将消息转换为SSE格式
    
    参数:
        message: 待转换的消息对象
        event_name: 可选的事件名称，默认使用消息类型
        
    返回:
        SSE格式字符串
    """
    event = event_name or message.type
    return f"event: {event}\ndata: {message.to_json()}\n\n"


async def format_messages_to_sse_stream(
    messages_generator: AsyncGenerator[Message, None]
) -> AsyncGenerator[str, None]:
    """
    将消息生成器转换为SSE流
    
    参数:
        messages_generator: 消息生成器
        
    返回:
        SSE格式字符串的异步生成器
    """
    async for message in messages_generator:
        yield format_to_sse(message)


def convert_llm_message_to_internal(
    message: Dict[str, Any], 
    source_type: str = "llm"
) -> Message:
    """
    将LLM消息转换为内部消息格式
    
    参数:
        message: LLM消息字典
        source_type: 来源类型，如llm、openai等
        
    返回:
        标准消息对象
    """
    from app.messaging.core.models import (
        TextMessage, FunctionCallMessage, 
        FunctionReturnMessage, MessageRole
    )
    
    # 处理角色
    role = message.get("role", "assistant")
    if role in [r.value for r in MessageRole]:
        role = MessageRole(role)
    else:
        role = MessageRole.ASSISTANT
    
    # 检查消息类型
    if "function_call" in message:
        # 函数调用消息
        function_call = message["function_call"]
        return FunctionCallMessage(
            role=role,
            content={
                "name": function_call.get("name", ""),
                "arguments": function_call.get("arguments", {})
            },
            metadata={"source": source_type}
        )
    elif message.get("role") == "function" and "content" in message:
        # 函数返回消息
        return FunctionReturnMessage(
            role=MessageRole.FUNCTION,
            content={
                "name": message.get("name", ""),
                "result": message["content"]
            },
            metadata={"source": source_type}
        )
    else:
        # 普通文本消息
        return TextMessage(
            role=role,
            content=message.get("content", ""),
            metadata={"source": source_type}
        )


def convert_thinking_to_internal(thinking_content: str, step: Optional[int] = None) -> Message:
    """
    将思考过程转换为内部消息格式
    
    参数:
        thinking_content: 思考内容文本
        step: 可选的步骤编号
        
    返回:
        思考消息对象
    """
    from app.messaging.core.models import ThinkingMessage
    
    metadata = {}
    if step is not None:
        metadata["step"] = step
    
    return ThinkingMessage(
        content=thinking_content,
        role=MessageRole.SYSTEM,
        step=step,
        metadata=metadata
    )


def convert_tool_call_to_internal(
    name: str,
    arguments: Dict[str, Any],
    call_id: Optional[str] = None
) -> Message:
    """
    将工具调用转换为内部消息格式
    
    参数:
        name: 工具名称
        arguments: 工具参数
        call_id: 可选的调用ID
        
    返回:
        函数调用消息对象
    """
    from app.messaging.core.models import FunctionCallMessage, MessageRole
    
    metadata = {}
    if call_id:
        metadata["call_id"] = call_id
    
    return FunctionCallMessage(
        role=MessageRole.ASSISTANT,
        content={
            "name": name,
            "arguments": arguments
        },
        metadata=metadata
    )


def convert_tool_result_to_internal(
    name: str,
    result: Any,
    call_id: Optional[str] = None
) -> Message:
    """
    将工具结果转换为内部消息格式
    
    参数:
        name: 工具名称
        result: 工具结果
        call_id: 可选的调用ID
        
    返回:
        函数返回消息对象
    """
    from app.messaging.core.models import FunctionReturnMessage, MessageRole
    
    content = {
        "name": name,
        "result": result
    }
    
    if call_id:
        content["call_id"] = call_id
    
    return FunctionReturnMessage(
        role=MessageRole.FUNCTION,
        content=content,
        metadata={"call_id": call_id} if call_id else {}
    )


def convert_from_openai_message(openai_message: Dict[str, Any]) -> Message:
    """
    将OpenAI消息格式转换为内部消息格式
    
    参数:
        openai_message: OpenAI消息字典
        
    返回:
        标准消息对象
    """
    from app.messaging.core.models import (
        MessageRole, TextMessage, FunctionCallMessage, 
        FunctionReturnMessage, ImageMessage, VoiceMessage, CompressedContextMessage
    )
    from app.messaging.core.compressed_context import convert_compressed_context_to_internal
    
    # 处理角色映射
    role_map = {
        "user": MessageRole.USER,
        "assistant": MessageRole.ASSISTANT,
        "system": MessageRole.SYSTEM,
        "function": MessageRole.FUNCTION,
        "tool": MessageRole.FUNCTION  # OpenAI新格式使用tool
    }
    
    role = role_map.get(openai_message.get("role", "assistant"), MessageRole.ASSISTANT)
    content = openai_message.get("content")
    
    # 检查是否是工具调用
    if "tool_calls" in openai_message:
        # 处理OpenAI新格式工具调用
        tool_call = openai_message["tool_calls"][0]  # 取第一个工具调用
        call_id = tool_call.get("id")
        function_data = tool_call.get("function", {})
        
        try:
            arguments = json.loads(function_data.get("arguments", "{}"))
        except json.JSONDecodeError:
            arguments = {}
            
        return FunctionCallMessage(
            role=role,
            content={
                "name": function_data.get("name", ""),
                "arguments": arguments
            },
            metadata={"call_id": call_id} if call_id else {}
        )
    elif "function_call" in openai_message:
        # 处理OpenAI旧格式函数调用
        function_call = openai_message["function_call"]
        
        try:
            arguments = json.loads(function_call.get("arguments", "{}"))
        except json.JSONDecodeError:
            arguments = {}
            
        return FunctionCallMessage(
            role=role,
            content={
                "name": function_call.get("name", ""),
                "arguments": arguments
            }
        )
    elif openai_message.get("role") == "tool" or openai_message.get("role") == "function":
        # 处理工具/函数返回
        tool_call_id = openai_message.get("tool_call_id")
        name = openai_message.get("name", "")
        
        return FunctionReturnMessage(
            role=MessageRole.FUNCTION,
            content={
                "name": name,
                "result": content,
                "call_id": tool_call_id
            },
            metadata={"call_id": tool_call_id} if tool_call_id else {}
        )
    
    # 检查复杂内容类型
    if isinstance(content, list):
        # 查找内容块类型
        has_image = False
        has_audio = False
        text_content = ""
        image_url = ""
        audio_url = ""
        
        for item in content:
            if isinstance(item, dict):
                item_type = item.get("type")
                
                if item_type == "text":
                    text_content += item.get("text", "") + "\n"
                elif item_type == "image_url":
                    has_image = True
                    image_data = item.get("image_url", {})
                    image_url = image_data.get("url", "")
                elif item_type == "audio_url":
                    has_audio = True
                    audio_data = item.get("audio_url", {})
                    audio_url = audio_data.get("url", "")
        
        text_content = text_content.strip()
        
        # 根据内容类型返回对应消息
        if has_image:
            return ImageMessage(
                role=role,
                content={
                    "url": image_url,
                    "caption": text_content if text_content else None
                }
            )
        elif has_audio:
            return VoiceMessage(
                role=role,
                content={
                    "url": audio_url,
                    "transcript": text_content if text_content else None
                }
            )
        else:
            return TextMessage(
                role=role,
                content=text_content
            )
    
    # 处理音频特殊结构
    if "audio" in openai_message and isinstance(openai_message["audio"], dict):
        audio_url = openai_message["audio"].get("url", "")
        return VoiceMessage(
            role=role,
            content={
                "url": audio_url,
                "transcript": content
            }
        )
    
    # 处理普通文本消息
    return TextMessage(
        role=role,
        content=content or ""
    )


def convert_messages_to_openai_format(messages: List[Message]) -> List[Dict[str, Any]]:
    """
    将内部消息列表转换为OpenAI格式的消息列表
    
    参数:
        messages: 内部消息列表
        
    返回:
        OpenAI格式的消息列表
    """
    return [msg.to_openai_format() for msg in messages]


def format_response_as_openai(messages: List[Message]) -> Dict[str, Any]:
    """
    将响应格式化为类似OpenAI的响应格式
    
    参数:
        messages: 内部消息列表
        
    返回:
        OpenAI格式的响应字典
    """
    # 获取最后一条助手消息
    assistant_message = None
    for msg in reversed(messages):
        if msg.role == MessageRole.ASSISTANT and msg.type != MessageType.ERROR:
            assistant_message = msg
            break
    
    if not assistant_message:
        # 如果没有助手消息，查找是否有错误消息
        for msg in reversed(messages):
            if msg.type == MessageType.ERROR:
                return {
                    "error": {
                        "message": msg.content.get("message", "未知错误"),
                        "type": "internal_error",
                        "code": msg.content.get("code") or "internal_error"
                    }
                }
        
        # 如果没有错误消息，返回空响应
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": ""
                },
                "finish_reason": "stop"
            }],
            "model": "internal",
            "id": f"msg-{int(time.time() * 1000)}",
            "created": int(time.time())
        }
    
    # 根据消息类型处理
    openai_message = assistant_message.to_openai_format()
    
    # 构建OpenAI格式的响应
    return {
        "choices": [{
            "message": openai_message,
            "finish_reason": "stop"
        }],
        "model": "internal",
        "id": f"msg-{int(time.time() * 1000)}",
        "created": int(time.time())
    }
