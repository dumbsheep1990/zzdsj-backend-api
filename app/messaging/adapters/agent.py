"""
代理适配器
提供与代理系统的集成接口
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
from app.frameworks.llamaindex.agent import KnowledgeAgent

logger = logging.getLogger(__name__)


class AgentAdapter(BaseAdapter):
    """
    代理适配器
    为代理模块提供统一的消息处理接口
    """
    
    async def process_messages(
        self,
        messages: List[Message],
        agent: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Message]:
        """
        处理代理消息
        
        参数:
            messages: 消息列表
            agent: 代理实例
            context: 上下文信息
            
        返回:
            处理后的消息列表
        """
        # 获取用户查询
        user_query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_query = msg.content
                if isinstance(user_query, dict):
                    user_query = json.dumps(user_query, ensure_ascii=False)
                break
        
        if not user_query:
            return [
                ErrorMessage(
                    content={"message": "没有找到用户查询"},
                    metadata={"source": "agent_adapter"}
                )
            ]
        
        # 设置代理上下文
        if context:
            if hasattr(agent, "set_context"):
                agent.set_context(context)
            elif hasattr(agent, "context"):
                agent.context = context
        
        # 执行代理查询
        try:
            # 处理各种可能的调用方式
            if hasattr(agent, "aquery"):
                response = await agent.aquery(user_query)
            elif hasattr(agent, "arun"):
                response = await agent.arun(user_query)
            elif hasattr(agent, "agenerate_response"):
                response = await agent.agenerate_response(user_query)
            elif hasattr(agent, "query"):
                response = agent.query(user_query)
            elif hasattr(agent, "run"):
                response = agent.run(user_query)
            elif hasattr(agent, "generate_response"):
                response = agent.generate_response(user_query)
            else:
                return [
                    ErrorMessage(
                        content={"message": "代理不支持查询操作"},
                        metadata={"source": "agent_adapter"}
                    )
                ]
            
            # 处理响应
            if isinstance(response, str):
                # 字符串响应
                return [
                    TextMessage(
                        content=response,
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "agent"}
                    )
                ]
            elif isinstance(response, dict):
                # 字典响应
                if "response" in response:
                    main_content = response["response"]
                elif "answer" in response:
                    main_content = response["answer"]
                elif "content" in response:
                    main_content = response["content"]
                elif "result" in response:
                    main_content = response["result"]
                else:
                    main_content = json.dumps(response, ensure_ascii=False)
                
                messages = [
                    TextMessage(
                        content=main_content,
                        role=MessageRole.ASSISTANT,
                        metadata={"source": "agent"}
                    )
                ]
                
                # 检查是否有思考过程
                if "thinking" in response:
                    thinking = response["thinking"]
                    if thinking:
                        messages.insert(0, ThinkingMessage(
                            content=thinking,
                            role=MessageRole.SYSTEM,
                            metadata={"source": "agent_thinking"}
                        ))
                
                # 检查是否有工具调用
                if "tool_calls" in response:
                    for tool_call in response["tool_calls"]:
                        name = tool_call.get("name", "")
                        args = tool_call.get("args", {})
                        result = tool_call.get("result", None)
                        
                        # 添加工具调用消息
                        if name and (args or args == {}):
                            messages.append(FunctionCallMessage(
                                content={"name": name, "arguments": args},
                                role=MessageRole.ASSISTANT,
                                metadata={"source": "agent_tool"}
                            ))
                        
                        # 添加工具结果消息
                        if name and result is not None:
                            messages.append(FunctionReturnMessage(
                                content={"name": name, "result": result},
                                role=MessageRole.FUNCTION,
                                metadata={"source": "agent_tool"}
                            ))
                
                return messages
            else:
                # 其他类型响应，尝试转换为字符串
                try:
                    content = str(response)
                    return [
                        TextMessage(
                            content=content,
                            role=MessageRole.ASSISTANT,
                            metadata={"source": "agent"}
                        )
                    ]
                except:
                    return [
                        ErrorMessage(
                            content={"message": "无法解析代理响应"},
                            metadata={"source": "agent_adapter"}
                        )
                    ]
        except Exception as e:
            logger.error(f"代理执行错误: {str(e)}")
            return [
                ErrorMessage(
                    content={"message": f"代理执行错误: {str(e)}"},
                    metadata={"source": "agent_adapter"}
                )
            ]
    
    async def stream_messages(
        self,
        messages: List[Message],
        agent: Any,
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """
        流式处理代理消息
        
        参数:
            messages: 消息列表
            agent: 代理实例
            context: 上下文信息
            stream_id: 流ID
            
        返回:
            消息流生成器
        """
        # 获取用户查询
        user_query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_query = msg.content
                if isinstance(user_query, dict):
                    user_query = json.dumps(user_query, ensure_ascii=False)
                break
        
        if not user_query:
            stream = self.message_service.create_message_stream(stream_id, chunk_mode=False)
            await stream.start_stream()
            await stream.add_error("没有找到用户查询")
            await stream.end_stream()
            return stream.get_message_stream()
        
        # 设置代理上下文
        if context:
            if hasattr(agent, "set_context"):
                agent.set_context(context)
            elif hasattr(agent, "context"):
                agent.context = context
        
        # 执行代理查询
        return await self.stream_service.process_agent_stream(
            agent=agent,
            query=user_query,
            stream_id=stream_id
        )
    
    async def to_sse_response(
        self,
        messages: List[Message],
        agent: Any,
        context: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        转换为SSE响应
        
        参数:
            messages: 消息列表
            agent: 代理实例
            context: 上下文信息
            stream_id: 流ID
            
        返回:
            SSE响应对象
        """
        # 获取用户查询
        user_query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_query = msg.content
                if isinstance(user_query, dict):
                    user_query = json.dumps(user_query, ensure_ascii=False)
                break
        
        if not user_query:
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
        
        # 设置代理上下文
        if context:
            if hasattr(agent, "set_context"):
                agent.set_context(context)
            elif hasattr(agent, "context"):
                agent.context = context
        
        # 创建消息流
        stream = self.message_service.create_message_stream(stream_id, chunk_mode=True)
        
        # 获取回调管理器
        callback_manager = self.message_service.create_callback_manager(stream)
        
        # 配置代理
        if hasattr(agent, "callback_manager"):
            agent.callback_manager = callback_manager
        
        # 开始流
        await stream.start_stream()
        
        # 执行查询
        try:
            asyncio.create_task(self._run_agent_query(agent, user_query))
        except Exception as e:
            logger.error(f"代理调用错误: {str(e)}")
            await stream.add_error(f"代理调用错误: {str(e)}")
            await stream.end_stream()
        
        # 返回SSE响应
        return StreamingResponse(
            stream.get_sse_stream(),
            media_type="text/event-stream"
        )
    
    async def _run_agent_query(self, agent: Any, query: str):
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
            elif hasattr(agent, "agenerate_response"):
                await agent.agenerate_response(query)
            else:
                # 同步调用
                if hasattr(agent, "query"):
                    agent.query(query)
                elif hasattr(agent, "run"):
                    agent.run(query)
                elif hasattr(agent, "generate_response"):
                    agent.generate_response(query)
        except Exception as e:
            logger.error(f"代理执行错误: {str(e)}")
    
    def to_json_response(
        self,
        messages: List[Message],
        include_metadata: bool = False,
        include_thinking: bool = True
    ) -> Dict[str, Any]:
        """
        转换为JSON响应
        
        参数:
            messages: 消息列表
            include_metadata: 是否包含元数据
            include_thinking: 是否包含思考过程
            
        返回:
            JSON响应字典
        """
        # 处理响应
        response = {
            "messages": []
        }
        
        thinking = None
        main_content = None
        tool_calls = []
        
        # 分类处理消息
        for msg in messages:
            if msg.type == MessageType.THINKING:
                thinking = msg.content
            elif msg.type == MessageType.FUNCTION_CALL:
                tool_calls.append({
                    "name": msg.content.get("name", ""),
                    "args": msg.content.get("arguments", {}),
                    "result": None
                })
            elif msg.type == MessageType.FUNCTION_RETURN:
                # 查找匹配的工具调用
                for tool_call in tool_calls:
                    if tool_call["name"] == msg.content.get("name", ""):
                        tool_call["result"] = msg.content.get("result", None)
                        break
            elif msg.type == MessageType.TEXT and main_content is None:
                # 第一个文本消息作为主要内容
                main_content = msg.content
            
            # 所有消息都加入消息列表
            if include_metadata:
                response["messages"].append(msg.to_dict(include_metadata=True))
            else:
                response["messages"].append(msg.to_dict(include_metadata=False))
        
        # 设置主要响应内容
        if main_content:
            response["response"] = main_content
        
        # 添加思考过程
        if include_thinking and thinking:
            response["thinking"] = thinking
        
        # 添加工具调用
        if tool_calls:
            response["tool_calls"] = tool_calls
        
        return response
    
    async def process_agent_query(
        self,
        query: str,
        agent_name: Optional[str] = None,
        agent: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        stream_id: Optional[str] = None
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        处理代理查询
        
        参数:
            query: 查询内容
            agent_name: 代理名称
            agent: 代理实例
            context: 上下文信息
            stream: 是否流式处理
            stream_id: 流ID
            
        返回:
            处理后的响应对象
        """
        # 验证代理
        if agent is None and agent_name:
            # 如果有代理名称，可以添加从工厂获取代理实例的逻辑
            # 例如：agent = get_agent_by_name(agent_name)
            pass
        
        if agent is None:
            if stream:
                # 创建错误流
                stream = self.message_service.create_message_stream(stream_id, chunk_mode=False)
                await stream.start_stream()
                await stream.add_error("未提供有效的代理")
                await stream.end_stream()
                
                # 返回SSE响应
                return StreamingResponse(
                    stream.get_sse_stream(),
                    media_type="text/event-stream"
                )
            else:
                return {
                    "error": "未提供有效的代理",
                    "messages": [
                        {
                            "type": "error",
                            "content": {"message": "未提供有效的代理"}
                        }
                    ]
                }
        
        # 创建消息
        message = TextMessage(
            content=query,
            role=MessageRole.USER
        )
        
        # 处理查询
        if stream:
            return await self.to_sse_response(
                messages=[message],
                agent=agent,
                context=context,
                stream_id=stream_id
            )
        else:
            response_messages = await self.process_messages(
                messages=[message],
                agent=agent,
                context=context
            )
            
            return self.to_json_response(
                messages=response_messages,
                include_metadata=False,
                include_thinking=True
            )
