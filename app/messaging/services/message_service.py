"""
消息服务
提供统一的消息处理和转发服务
"""

import logging
from typing import Dict, Any, List, Optional, Union, AsyncGenerator, Callable
import json
import asyncio
from datetime import datetime

from llama_index.core.llms import ChatMessage, MessageRole as LlamaMessageRole
from llama_index.core.callbacks import CallbackManager
from llama_index.core.callbacks.base import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType, EventPayload

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage,
    MCPToolMessage, VoiceMessage, DeepResearchMessage, CodeMessage, TableMessage
)
from app.messaging.core.formatters import (
    convert_llm_message_to_internal, convert_thinking_to_internal,
    convert_tool_call_to_internal, convert_tool_result_to_internal,
    convert_from_openai_message, convert_messages_to_openai_format,
    format_response_as_openai
)
from app.messaging.core.stream import MessageStream, ChunkMessageStream


logger = logging.getLogger(__name__)


class MessageCallbackHandler(BaseCallbackHandler):
    """消息回调处理器，用于将LlamaIndex回调转换为消息流"""
    
    def __init__(self, message_stream: MessageStream):
        """
        初始化消息回调处理器
        
        参数:
            message_stream: 消息流对象
        """
        super().__init__()
        self.message_stream = message_stream
        
    def on_event_start(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        事件开始回调
        
        参数:
            event_type: 事件类型
            payload: 事件载荷
        """
        if event_type == CBEventType.LLM_STREAM:
            asyncio.create_task(self.message_stream.start_stream())
    
    def on_event_end(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        事件结束回调
        
        参数:
            event_type: 事件类型
            payload: 事件载荷
        """
        if event_type == CBEventType.LLM_STREAM:
            # 对于ChunkMessageStream，需要先完成文本
            if isinstance(self.message_stream, ChunkMessageStream):
                asyncio.create_task(self.message_stream.finalize_text())
                
            asyncio.create_task(self.message_stream.end_stream())
    
    def on_event(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        事件处理回调
        
        参数:
            event_type: 事件类型
            payload: 事件载荷
        """
        payload = payload or {}
        
        if event_type == CBEventType.LLM_CHUNK:
            # 处理LLM文本块
            chunk = payload.get(EventPayload.CHUNK, "")
            if chunk and isinstance(self.message_stream, ChunkMessageStream):
                asyncio.create_task(self.message_stream.add_text_chunk(chunk))
            elif chunk:
                asyncio.create_task(self.message_stream.add_text(chunk))
                
        elif event_type == CBEventType.FUNCTION_CALL:
            # 处理函数调用
            function_name = payload.get(EventPayload.FUNCTION_NAME, "")
            function_args = payload.get(EventPayload.FUNCTION_ARGS, {})
            asyncio.create_task(self.message_stream.add_function_call(
                function_name, function_args
            ))
            
        elif event_type == CBEventType.FUNCTION_RETURN:
            # 处理函数返回
            function_name = payload.get(EventPayload.FUNCTION_NAME, "")
            function_output = payload.get("function_output", None)
            call_id = payload.get("call_id", None)
            asyncio.create_task(self.message_stream.add_function_return(
                function_name, function_output, call_id
            ))
            
        elif event_type == CBEventType.AGENT_STEP:
            # 处理代理步骤
            if "thinking" in payload:
                thinking = payload.get("thinking", "")
                step = payload.get("step", None)
                asyncio.create_task(self.message_stream.add_thinking(thinking, step))


class MessageService:
    """消息服务，提供统一的消息处理能力"""
    
    def __init__(self):
        """初始化消息服务"""
        self._callback_managers = {}
        self._message_streams = {}
    
    def create_message_stream(self, stream_id: Optional[str] = None, chunk_mode: bool = True) -> MessageStream:
        """
        创建消息流
        
        参数:
            stream_id: 可选的流ID，如果为None则自动生成
            chunk_mode: 是否使用块模式(用于LLM流式输出)
            
        返回:
            消息流对象
        """
        stream_id = stream_id or f"stream-{datetime.now().timestamp()}"
        stream = ChunkMessageStream() if chunk_mode else MessageStream()
        self._message_streams[stream_id] = stream
        return stream
    
    def get_message_stream(self, stream_id: str) -> Optional[MessageStream]:
        """
        获取消息流
        
        参数:
            stream_id: 流ID
            
        返回:
            消息流对象，如果不存在则返回None
        """
        return self._message_streams.get(stream_id)
    
    def create_callback_manager(self, stream: MessageStream) -> CallbackManager:
        """
        创建回调管理器
        
        参数:
            stream: 消息流对象
            
        返回:
            回调管理器
        """
        callback_handler = MessageCallbackHandler(stream)
        return CallbackManager([callback_handler])
    
    def get_callback_for_stream(self, stream_id: str) -> Optional[CallbackManager]:
        """
        获取与流关联的回调管理器
        
        参数:
            stream_id: 流ID
            
        返回:
            回调管理器，如果不存在则返回None
        """
        if stream_id in self._message_streams:
            stream = self._message_streams[stream_id]
            if stream_id not in self._callback_managers:
                self._callback_managers[stream_id] = self.create_callback_manager(stream)
            return self._callback_managers[stream_id]
        return None
    
    def convert_to_llama_messages(self, messages: List[Message]) -> List[ChatMessage]:
        """
        将内部消息转换为LlamaIndex的ChatMessage
        
        参数:
            messages: 内部消息列表
            
        返回:
            LlamaIndex ChatMessage列表
        """
        llama_messages = []
        
        for msg in messages:
            role = LlamaMessageRole.ASSISTANT
            
            if msg.role == MessageRole.USER:
                role = LlamaMessageRole.USER
            elif msg.role == MessageRole.SYSTEM:
                role = LlamaMessageRole.SYSTEM
            elif msg.role == MessageRole.FUNCTION:
                role = LlamaMessageRole.TOOL
                
            content = msg.content
            
            # 如果是复杂消息类型，先转换为OpenAI格式再处理
            if msg.type in [
                MessageType.IMAGE, MessageType.VOICE, MessageType.DEEP_RESEARCH,
                MessageType.CODE, MessageType.TABLE, MessageType.HYBRID, MessageType.MCP_TOOL
            ]:
                openai_format = msg.to_openai_format()
                if isinstance(openai_format.get("content"), list):
                    # 如果是多部分内容，将其处理为文本
                    text_parts = []
                    for part in openai_format["content"]:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    content = "\n".join(text_parts)
                else:
                    content = openai_format.get("content", "")
            
            # 将字典或列表转换为字符串
            if isinstance(content, dict) or isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)
                
            llama_message = ChatMessage(
                role=role,
                content=content
            )
            
            # 特殊处理函数调用
            if msg.type == MessageType.FUNCTION_CALL or (
                msg.type == MessageType.MCP_TOOL and 
                msg.content.get("result") is None
            ):
                # 获取函数名称和参数
                if msg.type == MessageType.FUNCTION_CALL:
                    func_name = msg.content.get("name", "")
                    func_args = msg.content.get("arguments", {})
                else: # MCP_TOOL
                    func_name = f"mcp_{msg.content.get('name', '')}"
                    func_args = msg.content.get("parameters", {})
                
                llama_message.additional_kwargs = {
                    "function_call": {
                        "name": func_name,
                        "arguments": json.dumps(func_args, ensure_ascii=False)
                    }
                }
            
            llama_messages.append(llama_message)
            
        return llama_messages
    
    def convert_from_llama_messages(self, llama_messages: List[ChatMessage]) -> List[Message]:
        """
        将LlamaIndex的ChatMessage转换为内部消息
        
        参数:
            llama_messages: LlamaIndex ChatMessage列表
            
        返回:
            内部消息列表
        """
        messages = []
        
        for llama_msg in llama_messages:
            role = MessageRole.ASSISTANT
            
            if llama_msg.role == LlamaMessageRole.USER:
                role = MessageRole.USER
            elif llama_msg.role == LlamaMessageRole.SYSTEM:
                role = MessageRole.SYSTEM
            elif llama_msg.role == LlamaMessageRole.TOOL:
                role = MessageRole.FUNCTION
                
            # 检查是否有函数调用
            if hasattr(llama_msg, "additional_kwargs") and "function_call" in llama_msg.additional_kwargs:
                func_call = llama_msg.additional_kwargs["function_call"]
                func_name = func_call.get("name", "")
                func_args_str = func_call.get("arguments", "{}")
                
                try:
                    func_args = json.loads(func_args_str)
                except:
                    func_args = {}
                    
                # 检查是否是MCP工具调用
                if func_name.startswith("mcp_"):
                    messages.append(MCPToolMessage(
                        role=role,
                        content={
                            "name": func_name[4:],  # 去掉mcp_前缀
                            "parameters": func_args
                        }
                    ))
                else:
                    messages.append(FunctionCallMessage(
                        role=role,
                        content={
                            "name": func_name,
                            "arguments": func_args
                        }
                    ))
            else:
                # 普通消息
                content = llama_msg.content or ""
                
                # 检查是否有思考过程
                if "<thinking>" in content and "</thinking>" in content:
                    # 分离思考和回答
                    thinking_start = content.find("<thinking>") + len("<thinking>")
                    thinking_end = content.find("</thinking>")
                    thinking_content = content[thinking_start:thinking_end].strip()
                    
                    # 添加思考消息
                    messages.append(ThinkingMessage(
                        content=thinking_content,
                        role=MessageRole.SYSTEM
                    ))
                    
                    # 处理剩余内容作为普通消息
                    remaining = content[:thinking_start-len("<thinking>")] + content[thinking_end+len("</thinking>"):]
                    if remaining.strip():
                        messages.append(TextMessage(
                            content=remaining.strip(),
                            role=role
                        ))
                # 检查是否是代码块
                elif "```" in content:
                    # 处理代码块
                    code_blocks = []
                    explanation = ""
                    parts = content.split("```")
                    
                    if len(parts) >= 3:  # 至少有一个代码块 (前文本, 代码, 后文本)
                        explanation = parts[0].strip()
                        # 获取最后一个代码块
                        for i in range(1, len(parts), 2):
                            if i < len(parts):
                                code_part = parts[i].strip()
                                language = ""
                                if "\n" in code_part:
                                    # 分离语言和代码
                                    first_line = code_part.split("\n")[0].strip()
                                    if first_line and not first_line.startswith("#") and not first_line.startswith("//"):
                                        language = first_line
                                        code_content = "\n".join(code_part.split("\n")[1:])
                                    else:
                                        code_content = code_part
                                else:
                                    code_content = code_part
                                
                                code_blocks.append((language, code_content))
                        
                        # 如果有多个代码块，选最后一个
                        if code_blocks:
                            last_language, last_code = code_blocks[-1]
                            messages.append(CodeMessage(
                                role=role,
                                content={
                                    "code": last_code,
                                    "language": last_language,
                                    "explanation": explanation
                                }
                            ))
                        else:
                            messages.append(TextMessage(
                                content=content,
                                role=role
                            ))
                    else:
                        # 没有完整的代码块，转为普通文本
                        messages.append(TextMessage(
                            content=content,
                            role=role
                        ))
                else:
                    # 普通消息
                    messages.append(TextMessage(
                        content=content,
                        role=role
                    ))
        
        return messages
        
    def convert_from_openai_message(self, openai_message: Dict[str, Any]) -> Message:
        """
        将OpenAI格式消息转换为内部消息
        
        参数:
            openai_message: OpenAI格式消息
            
        返回:
            内部消息对象
        """
        return convert_from_openai_message(openai_message)
    
    def convert_to_openai_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        将内部消息列表转换为OpenAI格式
        
        参数:
            messages: 内部消息列表
            
        返回:
            OpenAI格式消息列表
        """
        return convert_messages_to_openai_format(messages)
    
    def format_as_openai_response(self, messages: List[Message]) -> Dict[str, Any]:
        """
        将消息列表格式化为OpenAI格式的响应
        
        参数:
            messages: 内部消息列表
            
        返回:
            OpenAI格式响应字典
        """
        return format_response_as_openai(messages)


# 全局单例
_message_service_instance = None

def get_message_service() -> MessageService:
    """
    获取消息服务单例
    
    返回:
        消息服务实例
    """
    global _message_service_instance
    if _message_service_instance is None:
        _message_service_instance = MessageService()
    return _message_service_instance
