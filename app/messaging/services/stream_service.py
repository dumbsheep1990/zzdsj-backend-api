"""
流服务模块
提供流式消息处理和SSE响应能力
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncGenerator, Callable
import json
from datetime import datetime

from fastapi.responses import StreamingResponse
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole as LlamaMessageRole
from llama_index.core.callbacks import CallbackManager
from llama_index.core.llms.base import LLM, ChatResponse

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    FunctionCallMessage, FunctionReturnMessage, ThinkingMessage, 
    ImageMessage, HybridMessage, StatusMessage, ErrorMessage, DoneMessage
)
from app.messaging.core.stream import MessageStream, ChunkMessageStream
from app.messaging.services.message_service import MessageService, get_message_service
from app.frameworks.llamaindex.core import get_llm, get_service_context

logger = logging.getLogger(__name__)


class StreamService:
    """流服务，提供流式消息处理能力"""
    
    def __init__(self, message_service: Optional[MessageService] = None):
        """
        初始化流服务
        
        参数:
            message_service: 消息服务实例，如不提供则获取全局实例
        """
        self.message_service = message_service or get_message_service()
    
    async def process_llm_chat_stream(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        处理LLM聊天流，返回消息流
        
        参数:
            messages: 消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=True)
        
        # 获取回调管理器
        callback_manager = self.message_service.create_callback_manager(stream)
        
        # 获取LLM
        llm = get_llm(model_name, temperature)
        llm.callback_manager = callback_manager
        
        # 转换消息格式
        llama_messages = self.message_service.convert_to_llama_messages(messages)
        
        # 添加系统提示
        if system_prompt:
            system_msg = ChatMessage(role=LlamaMessageRole.SYSTEM, content=system_prompt)
            llama_messages.insert(0, system_msg)
        
        # 后台处理聊天请求
        asyncio.create_task(self._run_llm_chat(llm, llama_messages))
        
        # 返回消息流
        return stream.get_message_stream()
    
    async def _run_llm_chat(self, llm: LLM, messages: List[ChatMessage]):
        """
        运行LLM聊天
        
        参数:
            llm: LLM实例
            messages: 消息列表
        """
        try:
            response = await llm.achat(messages)
        except Exception as e:
            logger.error(f"LLM调用错误: {str(e)}")
    
    async def get_sse_response(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        获取SSE响应
        
        参数:
            messages: 消息列表
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            
        返回:
            StreamingResponse
        """
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=True)
        
        # 获取回调管理器
        callback_manager = self.message_service.create_callback_manager(stream)
        
        # 获取LLM
        llm = get_llm(model_name, temperature)
        llm.callback_manager = callback_manager
        
        # 转换消息格式
        llama_messages = self.message_service.convert_to_llama_messages(messages)
        
        # 添加系统提示
        if system_prompt:
            system_msg = ChatMessage(role=LlamaMessageRole.SYSTEM, content=system_prompt)
            llama_messages.insert(0, system_msg)
        
        # 后台处理聊天请求
        asyncio.create_task(self._run_llm_chat(llm, llama_messages))
        
        # 返回SSE流
        return StreamingResponse(
            stream.get_sse_stream(),
            media_type="text/event-stream"
        )
    
    async def process_function_stream(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        func: Callable,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        处理函数调用流，返回消息流
        
        参数:
            function_name: 函数名称
            arguments: 函数参数
            func: 函数对象
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=False)
        
        # 开始流
        await stream.start_stream()
        
        # 添加函数调用消息
        call_id = await stream.add_function_call(function_name, arguments)
        
        # 执行函数
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
                
            # 添加函数返回消息
            await stream.add_function_return(function_name, result, call_id)
        except Exception as e:
            logger.error(f"函数调用错误: {str(e)}")
            await stream.add_error(f"函数调用错误: {str(e)}")
        
        # 结束流
        await stream.end_stream()
        
        # 返回消息流
        return stream.get_message_stream()
    
    async def process_agent_stream(
        self,
        agent,
        query: str,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        处理代理流，返回消息流
        
        参数:
            agent: 代理实例
            query: 查询内容
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=True)
        
        # 获取回调管理器
        callback_manager = self.message_service.create_callback_manager(stream)
        
        # 配置代理
        if hasattr(agent, "callback_manager"):
            agent.callback_manager = callback_manager
        
        # 开始流
        await stream.start_stream()
        
        # 添加查询消息
        await stream.add_text(f"处理查询: {query}", MessageRole.SYSTEM)
        
        # 执行查询
        try:
            asyncio.create_task(self._run_agent_query(agent, query))
        except Exception as e:
            logger.error(f"代理调用错误: {str(e)}")
            await stream.add_error(f"代理调用错误: {str(e)}")
            await stream.end_stream()
        
        # 返回消息流
        return stream.get_message_stream()
    
    async def _run_agent_query(self, agent, query: str):
        """
        运行代理查询
        
        参数:
            agent: 代理实例
            query: 查询内容
        """
        try:
            # 检查代理API
            if hasattr(agent, "aquery"):
                await agent.aquery(query)
            elif hasattr(agent, "arun"):
                await agent.arun(query)
            elif hasattr(agent, "achat"):
                await agent.achat(query)
            else:
                # 同步调用
                if hasattr(agent, "query"):
                    agent.query(query)
                elif hasattr(agent, "run"):
                    agent.run(query)
                elif hasattr(agent, "chat"):
                    agent.chat(query)
        except Exception as e:
            logger.error(f"代理执行错误: {str(e)}")
    
    async def process_knowledge_stream(
        self,
        search_func: Callable,
        query: str,
        search_params: Dict[str, Any],
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        处理知识库搜索流，返回消息流
        
        参数:
            search_func: 搜索函数
            query: 查询内容
            search_params: 搜索参数
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=False)
        
        # 开始流
        await stream.start_stream()
        
        # 添加搜索开始消息
        await stream.add_text(f"搜索: {query}", MessageRole.SYSTEM)
        
        # 添加函数调用消息
        call_id = await stream.add_function_call("knowledge_search", {
            "query": query,
            **search_params
        })
        
        # 执行搜索
        try:
            if asyncio.iscoroutinefunction(search_func):
                results = await search_func(query, **search_params)
            else:
                results = search_func(query, **search_params)
                
            # 添加函数返回消息
            await stream.add_function_return("knowledge_search", results, call_id)
            
            # 处理结果
            if results and isinstance(results, list):
                for idx, item in enumerate(results):
                    if isinstance(item, dict) and "content" in item:
                        await stream.add_text(
                            f"结果 {idx+1}: {item['content'][:200]}...",
                            MessageRole.ASSISTANT
                        )
        except Exception as e:
            logger.error(f"知识库搜索错误: {str(e)}")
            await stream.add_error(f"知识库搜索错误: {str(e)}")
        
        # 结束流
        await stream.end_stream()
        
        # 返回消息流
        return stream.get_message_stream()


# 全局单例
_stream_service_instance = None

def get_stream_service() -> StreamService:
    """
    获取流服务单例
    
    返回:
        流服务实例
    """
    global _stream_service_instance
    if _stream_service_instance is None:
        _stream_service_instance = StreamService()
    return _stream_service_instance
