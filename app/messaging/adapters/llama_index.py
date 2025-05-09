"""
LlamaIndex适配器
提供与LlamaIndex框架的集成接口
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
import json

from fastapi.responses import StreamingResponse
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole as LlamaMessageRole
from llama_index.core.callbacks import CallbackManager
from llama_index.core.llms.base import LLM, ChatResponse
from llama_index.core.node_parser import SentenceSplitter

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage
)
from app.messaging.core.formatters import (
    convert_llm_message_to_internal, convert_thinking_to_internal,
    convert_tool_call_to_internal, convert_tool_result_to_internal
)
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service
from app.messaging.adapters.base import BaseAdapter
from app.frameworks.llamaindex.core import get_llm, get_service_context

logger = logging.getLogger(__name__)


class LlamaIndexAdapter(BaseAdapter):
    """LlamaIndex适配器，提供与LlamaIndex框架的集成"""
    
    async def process_messages(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> List[Message]:
        """
        处理消息
        
        参数:
            messages: 消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            
        返回:
            处理后的消息列表
        """
        # 转换消息格式
        llama_messages = self.message_service.convert_to_llama_messages(messages)
        
        # 添加系统提示
        if system_prompt:
            system_msg = ChatMessage(role=LlamaMessageRole.SYSTEM, content=system_prompt)
            llama_messages.insert(0, system_msg)
        
        # 获取LLM
        llm = get_llm(model_name, temperature)
        
        # 进行聊天
        try:
            response = await llm.achat(llama_messages)
            result_message = response.message
            
            # 转换回内部消息格式
            internal_messages = self.message_service.convert_from_llama_messages([result_message])
            return internal_messages
        except Exception as e:
            logger.error(f"LLM调用错误: {str(e)}")
            return [
                ErrorMessage(
                    content={"message": f"LLM调用错误: {str(e)}"},
                    metadata={"source": "llama_index_adapter"}
                )
            ]
    
    async def stream_messages(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        流式处理消息
        
        参数:
            messages: 消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        return await self.stream_service.process_llm_chat_stream(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt,
            stream_id=stream_id
        )
    
    async def to_sse_response(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        转换为SSE响应
        
        参数:
            messages: 消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            
        返回:
            SSE响应对象
        """
        return await self.stream_service.get_sse_response(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt,
            stream_id=stream_id
        )
    
    def to_json_response(
        self,
        messages: List[Message],
        include_metadata: bool = False
    ) -> Dict[str, Any]:
        """
        转换为JSON响应
        
        参数:
            messages: 消息列表
            include_metadata: 是否包含元数据
            
        返回:
            JSON响应字典
        """
        response = {
            "messages": [msg.to_dict(include_metadata=include_metadata) for msg in messages]
        }
        
        # 提取最后一条非错误消息的内容
        for msg in reversed(messages):
            if msg.type != MessageType.ERROR:
                response["content"] = msg.content
                break
        
        return response
    
    async def process_document(
        self,
        document: str,
        chunk_size: int = 1024,
        chunk_overlap: int = 20
    ) -> List[Dict[str, Any]]:
        """
        处理文档，将其分割为块
        
        参数:
            document: 文档内容
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            
        返回:
            文档块列表
        """
        node_parser = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        nodes = node_parser.get_nodes_from_documents([document])
        
        chunks = []
        for node in nodes:
            chunks.append({
                "content": node.text,
                "metadata": node.metadata
            })
            
        return chunks
    
    async def process_query_with_context(
        self,
        query: str,
        context: List[Dict[str, Any]],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_id: Optional[str] = None
    ) -> Union[List[Message], AsyncGenerator[Message, None]]:
        """
        使用上下文处理查询
        
        参数:
            query: 查询内容
            context: 上下文信息
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream: 是否流式处理
            stream_id: 流ID
            
        返回:
            处理后的消息列表或消息流生成器
        """
        # 构建系统提示
        context_str = "\n\n".join([item.get("content", "") for item in context if "content" in item])
        
        enhanced_system_prompt = f"""
请使用以下上下文信息回答用户的问题:

{context_str}

{system_prompt or ""}
"""
        
        # 构建消息
        messages = [
            TextMessage(
                content=query,
                role=MessageRole.USER
            )
        ]
        
        # 处理查询
        if stream:
            return await self.stream_messages(
                messages=messages,
                model_name=model_name,
                temperature=temperature,
                system_prompt=enhanced_system_prompt,
                stream_id=stream_id
            )
        else:
            return await self.process_messages(
                messages=messages,
                model_name=model_name,
                temperature=temperature,
                system_prompt=enhanced_system_prompt
            )
