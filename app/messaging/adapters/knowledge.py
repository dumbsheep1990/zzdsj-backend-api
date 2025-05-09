"""
知识库适配器
提供与知识库系统的集成接口
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

logger = logging.getLogger(__name__)


class KnowledgeAdapter(BaseAdapter):
    """
    知识库适配器
    为知识库模块提供统一的消息处理接口
    """
    
    def __init__(
        self,
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None,
        llama_index_adapter: Optional[LlamaIndexAdapter] = None
    ):
        """
        初始化知识库适配器
        
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
        search_func: callable,
        search_params: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> List[Message]:
        """
        处理知识库查询消息
        
        参数:
            messages: 消息列表
            search_func: 搜索函数
            search_params: 搜索参数
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            
        返回:
            处理后的消息列表
        """
        # 获取用户查询
        query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                query = msg.content
                if isinstance(query, dict):
                    query = json.dumps(query, ensure_ascii=False)
                break
        
        if not query:
            return [
                ErrorMessage(
                    content={"message": "没有找到用户查询"},
                    metadata={"source": "knowledge_adapter"}
                )
            ]
        
        # 执行知识库搜索
        search_params = search_params or {}
        try:
            # 执行搜索
            if asyncio.iscoroutinefunction(search_func):
                results = await search_func(query, **search_params)
            else:
                results = search_func(query, **search_params)
                
            # 处理搜索结果
            if not results or len(results) == 0:
                return [
                    TextMessage(
                        content="未找到相关信息",
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "knowledge_search"}
                    )
                ]
            
            # 提取上下文信息
            context = []
            for item in results:
                if isinstance(item, dict):
                    if "content" in item:
                        context.append({"content": item["content"]})
                    elif "text" in item:
                        context.append({"content": item["text"]})
                    else:
                        # 尝试转换为字符串
                        context.append({"content": str(item)})
                elif isinstance(item, str):
                    context.append({"content": item})
                else:
                    # 尝试转换为字符串
                    context.append({"content": str(item)})
            
            # 使用上下文处理查询
            return await self.llama_index_adapter.process_query_with_context(
                query=query,
                context=context,
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt,
                stream=False
            )
            
        except Exception as e:
            logger.error(f"知识库搜索错误: {str(e)}")
            return [
                ErrorMessage(
                    content={"message": f"知识库搜索错误: {str(e)}"},
                    metadata={"source": "knowledge_adapter"}
                )
            ]
    
    async def stream_messages(
        self,
        messages: List[Message],
        search_func: callable,
        search_params: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        流式处理知识库查询消息
        
        参数:
            messages: 消息列表
            search_func: 搜索函数
            search_params: 搜索参数
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        # 获取用户查询
        query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                query = msg.content
                if isinstance(query, dict):
                    query = json.dumps(query, ensure_ascii=False)
                break
        
        if not query:
            stream = self.message_service.create_message_stream(stream_id, chunk_mode=False)
            await stream.start_stream()
            await stream.add_error("没有找到用户查询")
            await stream.end_stream()
            return stream.get_message_stream()
        
        # 执行知识库搜索
        search_params = search_params or {}
        
        # 使用流服务处理知识库搜索
        return await self.stream_service.process_knowledge_stream(
            search_func=search_func,
            query=query,
            search_params=search_params,
            stream_id=stream_id
        )
    
    async def to_sse_response(
        self,
        messages: List[Message],
        search_func: callable,
        search_params: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        转换为SSE响应
        
        参数:
            messages: 消息列表
            search_func: 搜索函数
            search_params: 搜索参数
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream_id: 流ID
            
        返回:
            SSE响应对象
        """
        # 获取用户查询
        query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                query = msg.content
                if isinstance(query, dict):
                    query = json.dumps(query, ensure_ascii=False)
                break
        
        if not query:
            # 创建错误流
            stream = self.message_service.create_message_stream(stream_id, chunk_mode=False)
            await stream.start_stream()
            await stream.add_error("没有找到用户查询")
            await stream.end_stream()
            
            # 返回SSE响应
            return StreamingResponse(
                stream.get_sse_stream(),
                media_type="text/event-stream"
            )
        
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=True)
        
        # 开始流
        await stream.start_stream()
        
        # 添加查询开始消息
        await stream.add_text(f"搜索: {query}", MessageRole.SYSTEM)
        
        # 执行搜索
        search_params = search_params or {}
        try:
            # 执行搜索
            if asyncio.iscoroutinefunction(search_func):
                results_future = asyncio.create_task(search_func(query, **search_params))
                results = await results_future
            else:
                results = search_func(query, **search_params)
                
            # 处理搜索结果
            if not results or len(results) == 0:
                await stream.add_text("未找到相关信息", MessageRole.ASSISTANT)
                await stream.end_stream()
                
                # 返回SSE响应
                return StreamingResponse(
                    stream.get_sse_stream(),
                    media_type="text/event-stream"
                )
            
            # 提取上下文信息
            context = []
            for item in results:
                if isinstance(item, dict):
                    if "content" in item:
                        context.append({"content": item["content"]})
                    elif "text" in item:
                        context.append({"content": item["text"]})
                    else:
                        # 尝试转换为字符串
                        context.append({"content": str(item)})
                elif isinstance(item, str):
                    context.append({"content": item})
                else:
                    # 尝试转换为字符串
                    context.append({"content": str(item)})
            
            # 构建增强系统提示
            context_str = "\n\n".join([item.get("content", "") for item in context if "content" in item])
            enhanced_system_prompt = f"""
请使用以下上下文信息回答用户的问题:

{context_str}

{system_prompt or ""}
"""
            
            # 创建消息
            user_message = TextMessage(
                content=query,
                role=MessageRole.USER
            )
            
            # 使用LlamaIndex适配器创建SSE响应
            return await self.llama_index_adapter.to_sse_response(
                messages=[user_message],
                model_name=model_name,
                temperature=temperature,
                system_prompt=enhanced_system_prompt,
                stream_id=stream_id
            )
            
        except Exception as e:
            logger.error(f"知识库搜索错误: {str(e)}")
            await stream.add_error(f"知识库搜索错误: {str(e)}")
            await stream.end_stream()
            
            # 返回SSE响应
            return StreamingResponse(
                stream.get_sse_stream(),
                media_type="text/event-stream"
            )
    
    def to_json_response(
        self,
        messages: List[Message],
        include_metadata: bool = False,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        转换为JSON响应
        
        参数:
            messages: 消息列表
            include_metadata: 是否包含元数据
            include_sources: 是否包含来源信息
            
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
        
        # 提取来源信息
        if include_sources:
            sources = []
            for msg in messages:
                if msg.metadata and "source" in msg.metadata:
                    source = msg.metadata["source"]
                    if source not in sources:
                        sources.append(source)
            
            if sources:
                response["sources"] = sources
        
        return response
    
    async def process_knowledge_query(
        self,
        query: str,
        search_func: callable,
        search_params: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_id: Optional[str] = None
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        处理知识库查询
        
        参数:
            query: 查询内容
            search_func: 搜索函数
            search_params: 搜索参数
            model_name: 模型名称
            temperature: 温度参数
            system_prompt: 系统提示
            stream: 是否流式处理
            stream_id: 流ID
            
        返回:
            处理后的响应对象
        """
        # 创建消息
        message = TextMessage(
            content=query,
            role=MessageRole.USER
        )
        
        # 处理查询
        if stream:
            return await self.to_sse_response(
                messages=[message],
                search_func=search_func,
                search_params=search_params,
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt,
                stream_id=stream_id
            )
        else:
            response_messages = await self.process_messages(
                messages=[message],
                search_func=search_func,
                search_params=search_params,
                model_name=model_name,
                temperature=temperature,
                system_prompt=system_prompt
            )
            
            return self.to_json_response(
                messages=response_messages,
                include_metadata=False,
                include_sources=True
            )
