"""
LightRAG适配器
将LightRAG知识图谱查询能力集成到统一消息系统中
"""

from typing import List, Dict, Any, Optional, Union, Callable
import logging
from enum import Enum

from app.messaging.adapters.base import BaseAdapter
from app.messaging.core.models import (
    Message, MessageRole, MessageType, TextMessage
)
from app.messaging.services.message_service import MessageService
from app.messaging.services.stream_service import StreamService
from app.frameworks.lightrag.client import get_lightrag_client

logger = logging.getLogger(__name__)


class LightRAGQueryMode(str, Enum):
    """LightRAG查询模式"""
    HYBRID = "hybrid"
    LOCAL = "local"
    GLOBAL = "global"
    NAIVE = "naive"
    MIX = "mix"


class LightRAGAdapter(BaseAdapter):
    """LightRAG知识图谱适配器"""
    
    def __init__(
        self,
        message_service: MessageService,
        stream_service: StreamService
    ):
        """初始化LightRAG适配器"""
        super().__init__(message_service, stream_service)
        self.client = get_lightrag_client()
    
    def _extract_query(self, messages: List[Message]) -> str:
        """提取查询内容，通常是最后一条用户消息"""
        for message in reversed(messages):
            if message.role == MessageRole.USER:
                if isinstance(message.content, str):
                    return message.content
                else:
                    return str(message.content)
        return ""
    
    def _parse_query_mode(self, query: str) -> tuple[str, str, bool, bool]:
        """
        解析查询前缀以确定查询模式
        
        Args:
            query: 原始查询文本
            
        Returns:
            tuple: (实际查询文本, 查询模式, 是否只返回上下文, 是否跳过RAG)
        """
        query_mode = "hybrid"
        return_context_only = False
        bypass_rag = False
        actual_query = query
        
        if query.startswith("/"):
            prefix_parts = query.split(" ", 1)
            if len(prefix_parts) > 1:
                prefix, actual_query = prefix_parts
                prefix = prefix.lower().strip("/")
                
                # 映射前缀到参数
                if prefix == "bypass":
                    bypass_rag = True
                    query_mode = "hybrid"
                elif prefix == "context":
                    return_context_only = True
                    query_mode = "hybrid"
                elif prefix.endswith("context"):
                    return_context_only = True
                    query_mode = prefix.replace("context", "")
                else:
                    query_mode = prefix
        
        return actual_query, query_mode, return_context_only, bypass_rag
    
    async def process_messages(
        self,
        messages: List[Message],
        graph_ids: List[str] = None,
        query_mode: str = None,
        return_context_only: bool = None,
        bypass_rag: bool = None,
        model_name: str = None,
        **kwargs
    ) -> List[Message]:
        """
        处理消息并使用LightRAG检索知识
        
        Args:
            messages: 消息列表
            graph_ids: 知识图谱ID列表
            query_mode: 查询模式
            return_context_only: 是否只返回上下文
            bypass_rag: 是否跳过RAG直接查询LLM
            model_name: 模型名称
            **kwargs: 其他参数
            
        Returns:
            List[Message]: 响应消息列表
        """
        # 获取查询内容
        query = self._extract_query(messages)
        
        # 解析查询前缀
        actual_query, parsed_mode, parsed_context_only, parsed_bypass = self._parse_query_mode(query)
        
        # 参数优先级：显式参数 > 解析前缀
        query_mode = query_mode if query_mode is not None else parsed_mode
        return_context_only = return_context_only if return_context_only is not None else parsed_context_only
        bypass_rag = bypass_rag if bypass_rag is not None else parsed_bypass
        
        # 检查LightRAG客户端是否可用
        if not self.client.is_available():
            error_msg = TextMessage(
                content="LightRAG服务不可用，无法执行知识图谱查询",
                role=MessageRole.SYSTEM,
                type=MessageType.ERROR
            )
            return [*messages, error_msg]
        
        # 执行检索
        results = []
        for graph_id in graph_ids or []:
            try:
                graph_results = self.client.query(
                    query_text=actual_query,
                    workdir_id=graph_id,
                    mode=query_mode,
                    return_context_only=return_context_only,
                    bypass_rag=bypass_rag
                )
                
                if graph_results.get("success", False):
                    results.append(graph_results)
                else:
                    logger.warning(f"查询图谱 {graph_id} 失败: {graph_results.get('error', '未知错误')}")
            except Exception as e:
                logger.error(f"查询图谱 {graph_id} 时出错: {str(e)}")
        
        # 构建响应
        if not results:
            error_msg = TextMessage(
                content="没有找到相关的知识图谱信息",
                role=MessageRole.ASSISTANT
            )
            return [*messages, error_msg]
        
        if return_context_only:
            # 只返回上下文
            contexts = []
            for result in results:
                context = result.get("context", "")
                if context:
                    contexts.append(f"图谱 {result.get('graph_id', 'unknown')} 上下文:\n{context}")
            
            response_content = "\n\n".join(contexts)
        else:
            # 返回完整回答
            answers = []
            for result in results:
                answer = result.get("answer", "")
                if answer:
                    graph_id = result.get("graph_id", "unknown")
                    answers.append(f"图谱 {graph_id} 回答:\n{answer}")
            
            response_content = "\n\n".join(answers) if answers else "无法获取回答"
        
        # 创建响应消息
        response = TextMessage(
            content=response_content,
            role=MessageRole.ASSISTANT
        )
        
        return [*messages, response]
    
    async def to_sse_response(
        self,
        messages: List[Message],
        graph_ids: List[str] = None,
        query_mode: str = None,
        return_context_only: bool = None,
        bypass_rag: bool = None,
        **kwargs
    ) -> StreamService:
        """
        处理消息并返回SSE流
        
        Args:
            messages: 消息列表
            graph_ids: 知识图谱ID列表
            query_mode: 查询模式
            return_context_only: 是否只返回上下文
            bypass_rag: 是否跳过RAG直接查询LLM
            **kwargs: 其他参数
            
        Returns:
            StreamService: 流服务
        """
        # 创建流服务
        stream_service = self.stream_service.create_stream(
            conversation_id=kwargs.get("conversation_id", f"lightrag-{id(self)}"),
            user_id=kwargs.get("user_id")
        )
        
        # 获取查询内容
        query = self._extract_query(messages)
        
        # 解析查询前缀
        actual_query, parsed_mode, parsed_context_only, parsed_bypass = self._parse_query_mode(query)
        
        # 参数优先级：显式参数 > 解析前缀
        query_mode = query_mode if query_mode is not None else parsed_mode
        return_context_only = return_context_only if return_context_only is not None else parsed_context_only
        bypass_rag = bypass_rag if bypass_rag is not None else parsed_bypass
        
        # 检查LightRAG客户端是否可用
        if not self.client.is_available():
            error_msg = TextMessage(
                content="LightRAG服务不可用，无法执行知识图谱查询",
                role=MessageRole.SYSTEM,
                type=MessageType.ERROR
            )
            await stream_service.add_message(error_msg)
            await stream_service.complete(error=True)
            return stream_service
        
        try:
            # 执行流式查询
            for graph_id in graph_ids or []:
                try:
                    # 向流中添加状态消息
                    status_msg = TextMessage(
                        content=f"正在查询图谱 {graph_id}...",
                        role=MessageRole.SYSTEM
                    )
                    await stream_service.add_message(status_msg, is_intermediate=True)
                    
                    # 执行查询
                    response = self.client.query_stream(
                        query_text=actual_query,
                        workdir_id=graph_id,
                        mode=query_mode,
                        return_context_only=return_context_only,
                        bypass_rag=bypass_rag
                    )
                    
                    # 处理流式响应
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = line.decode('utf-8')
                                if data.startswith('data: '):
                                    data = data[6:]  # 移除"data: "前缀
                                    
                                    if data == "[DONE]":
                                        continue
                                        
                                    try:
                                        # 尝试解析JSON
                                        import json
                                        json_data = json.loads(data)
                                        
                                        chunk = json_data.get('chunk', '')
                                        if chunk:
                                            # 向流中添加文本块
                                            chunk_msg = TextMessage(
                                                content=chunk,
                                                role=MessageRole.ASSISTANT
                                            )
                                            await stream_service.add_message(chunk_msg, is_chunk=True)
                                    except:
                                        # 如果无法解析JSON，直接将数据作为chunk发送
                                        chunk_msg = TextMessage(
                                            content=data,
                                            role=MessageRole.ASSISTANT
                                        )
                                        await stream_service.add_message(chunk_msg, is_chunk=True)
                            except Exception as e:
                                logger.error(f"处理SSE数据时出错: {str(e)}")
                except Exception as e:
                    logger.error(f"查询图谱 {graph_id} 时出错: {str(e)}")
                    error_msg = TextMessage(
                        content=f"查询图谱 {graph_id} 时出错: {str(e)}",
                        role=MessageRole.SYSTEM,
                        type=MessageType.ERROR
                    )
                    await stream_service.add_message(error_msg, is_intermediate=True)
            
            # 完成流
            await stream_service.complete()
        except Exception as e:
            logger.error(f"流式查询出错: {str(e)}")
            error_msg = TextMessage(
                content=f"流式查询出错: {str(e)}",
                role=MessageRole.SYSTEM,
                type=MessageType.ERROR
            )
            await stream_service.add_message(error_msg)
            await stream_service.complete(error=True)
        
        return stream_service
