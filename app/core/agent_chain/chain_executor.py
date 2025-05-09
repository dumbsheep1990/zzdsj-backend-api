"""
Agent链执行器
负责按照预定义的顺序或规则执行多个Agent
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Callable
import logging
import asyncio
import json
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException

from app.messaging.core.models import (
    Message, MessageRole, MessageType, TextMessage
)
from app.messaging.services.message_service import MessageService, get_message_service
from app.messaging.services.stream_service import StreamService, get_stream_service
from app.messaging.adapters.agent import AgentAdapter
from app.messaging.adapters.lightrag import LightRAGAdapter
from app.core.agent_chain.message_router import MessageRouter, get_message_router
from app.models.assistants import Assistant
from app.models.assistant_knowledge_graph import AssistantKnowledgeGraph
from app.models.database import get_db

logger = logging.getLogger(__name__)


class AgentChainExecutor:
    """
    Agent链执行器
    管理多个Agent的调用顺序和消息传递
    """
    
    def __init__(
        self,
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None,
        message_router: Optional[MessageRouter] = None,
        db: Optional[Session] = None
    ):
        """初始化Agent链执行器"""
        self.message_service = message_service or get_message_service()
        self.stream_service = stream_service or get_stream_service()
        self.message_router = message_router or get_message_router()
        self.db = db
        
    async def execute_chain(
        self,
        chain_config: Dict[str, Any],
        input_message: str,
        user_id: Optional[str] = None,
        stream: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> Union[List[Message], StreamService]:
        """
        执行Agent调用链
        
        Args:
            chain_config: 调用链配置
            input_message: 用户输入消息
            user_id: 用户ID
            stream: 是否使用流式响应
            context: 上下文信息
            
        Returns:
            执行结果消息或流式服务
        """
        if not self.db:
            raise ValueError("数据库会话未初始化")
        
        # 解析调用链配置
        agents = chain_config.get("agents", [])
        if not agents:
            raise ValueError("调用链配置中没有定义Agent")
        
        # 获取执行模式
        execution_mode = chain_config.get("execution_mode", "sequential")
        
        # 创建执行上下文
        execution_context = {
            "chain_id": chain_config.get("id", f"chain-{uuid.uuid4()}"),
            "user_id": user_id,
            "start_time": datetime.now(),
            "context": context or {},
            "results": {},
            "current_input": input_message
        }
        
        # 根据执行模式选择执行方法
        if execution_mode == "sequential":
            return await self._execute_sequential(agents, execution_context, stream)
        elif execution_mode == "parallel":
            return await self._execute_parallel(agents, execution_context, stream)
        elif execution_mode == "conditional":
            return await self._execute_conditional(agents, chain_config.get("conditions", {}), execution_context, stream)
        else:
            raise ValueError(f"不支持的执行模式: {execution_mode}")
            
    async def _execute_sequential(
        self,
        agents: List[Dict[str, Any]],
        context: Dict[str, Any],
        stream: bool = False
    ) -> Union[List[Message], StreamService]:
        """
        按顺序执行多个Agent
        
        Args:
            agents: Agent列表
            context: 执行上下文
            stream: 是否使用流式响应
            
        Returns:
            执行结果消息或流式服务
        """
        # 如果是流式响应，创建流式服务
        if stream:
            # 使用最后一个Agent的流式响应
            last_agent = agents[-1]
            final_stream = self.stream_service.create_stream(
                conversation_id=context.get("chain_id"),
                user_id=context.get("user_id")
            )
            
            # 启动后台任务执行调用链
            asyncio.create_task(self._execute_sequential_background(
                agents, context, final_stream
            ))
            
            return final_stream
        
        # 非流式响应，同步执行
        all_messages = []
        current_input = context.get("current_input")
        
        # 依次执行每个Agent
        for i, agent_config in enumerate(agents):
            agent_id = agent_config.get("id")
            if not agent_id:
                raise ValueError(f"Agent配置缺少ID: {agent_config}")
                
            # 获取Agent
            agent = self._get_agent_by_id(agent_id)
            if not agent:
                raise ValueError(f"Agent不存在: {agent_id}")
                
            # 创建Agent适配器
            agent_adapter = AgentAdapter(self.message_service, self.stream_service)
            
            # 创建输入消息
            input_msg = TextMessage(
                content=current_input,
                role=MessageRole.USER
            )
            
            # 获取Agent关联的知识图谱
            knowledge_graphs = self._get_agent_knowledge_graphs(agent.id)
            
            # 如果Agent配置了知识图谱，先使用LightRAG增强输入
            if knowledge_graphs and len(knowledge_graphs) > 0:
                # 获取知识图谱ID列表
                graph_ids = [kg.graph_id for kg in knowledge_graphs]
                
                # 获取查询模式
                query_mode = agent_config.get("lightrag_query_mode", "hybrid")
                
                # 创建LightRAG适配器
                lightrag_adapter = LightRAGAdapter(self.message_service, self.stream_service)
                
                try:
                    # 使用知识图谱增强输入
                    logger.info(f"使用知识图谱增强Agent输入: {len(graph_ids)}个图谱, 模式: {query_mode}")
                    enhanced_messages = await lightrag_adapter.process_messages(
                        messages=[input_msg],
                        graph_ids=graph_ids,
                        query_mode=query_mode
                    )
                    
                    # 提取知识图谱响应
                    if len(enhanced_messages) > 1:
                        knowledge_response = enhanced_messages[-1]
                        if knowledge_response.role == MessageRole.ASSISTANT and knowledge_response.content:
                            # 创建增强输入消息
                            input_msg = TextMessage(
                                content=f"用户问题: {current_input}\n\n相关知识: {knowledge_response.content}",
                                role=MessageRole.USER
                            )
                            logger.info("成功使用知识图谱增强输入")
                except Exception as e:
                    logger.warning(f"知识图谱增强失败: {str(e)}")
            
            # 执行Agent
            logger.info(f"执行Agent[{i+1}/{len(agents)}]: {agent.name} (ID: {agent.id})")
            response_messages = await agent_adapter.process_messages(
                messages=[input_msg],
                model_name=agent.model,
                temperature=agent.temperature,
                system_prompt=agent.system_prompt,
                memory_key=f"agent_chain_{context.get('chain_id')}_{agent.id}"
            )
            
            # 保存结果
            context["results"][agent_id] = response_messages
            all_messages.append(response_messages)
            
            # 提取输出作为下一个Agent的输入
            if i < len(agents) - 1:
                # 提取最终响应作为下一个Agent的输入
                final_response = await self.message_router.extract_final_response(response_messages)
                if isinstance(final_response.content, str):
                    current_input = final_response.content
                else:
                    current_input = str(final_response.content)
        
        # 合并所有消息
        combined_messages = await self.message_router.combine_messages(all_messages)
        return combined_messages
        
    async def _execute_sequential_background(
        self,
        agents: List[Dict[str, Any]],
        context: Dict[str, Any],
        stream_service: StreamService
    ) -> None:
        """
        在后台按顺序执行多个Agent，结果通过流式服务返回
        
        Args:
            agents: Agent列表
            context: 执行上下文
            stream_service: 流式服务实例
        """
        try:
            current_input = context.get("current_input")
            
            # 依次执行每个Agent
            for i, agent_config in enumerate(agents):
                agent_id = agent_config.get("id")
                if not agent_id:
                    raise ValueError(f"Agent配置缺少ID: {agent_config}")
                    
                # 获取Agent
                agent = self._get_agent_by_id(agent_id)
                if not agent:
                    raise ValueError(f"Agent不存在: {agent_id}")
                    
                # 创建Agent适配器
                agent_adapter = AgentAdapter(self.message_service, self.stream_service)
                
                # 创建输入消息
                input_msg = TextMessage(
                    content=current_input,
                    role=MessageRole.USER
                )
                
                # 获取Agent关联的知识图谱
                knowledge_graphs = self._get_agent_knowledge_graphs(agent.id)
                
                # 如果Agent配置了知识图谱，先使用LightRAG增强输入
                if knowledge_graphs and len(knowledge_graphs) > 0:
                    # 获取知识图谱ID列表
                    graph_ids = [kg.graph_id for kg in knowledge_graphs]
                    
                    # 获取查询模式
                    query_mode = agent_config.get("lightrag_query_mode", "hybrid")
                    
                    # 创建LightRAG适配器
                    lightrag_adapter = LightRAGAdapter(self.message_service, self.stream_service)
                    
                    try:
                        # 通知前端正在检索知识
                        status_msg = TextMessage(
                            content=f"正在从知识图谱检索相关信息...",
                            role=MessageRole.SYSTEM
                        )
                        await stream_service.add_message(status_msg, is_intermediate=True)
                        
                        # 使用知识图谱增强输入
                        enhanced_messages = await lightrag_adapter.process_messages(
                            messages=[input_msg],
                            graph_ids=graph_ids,
                            query_mode=query_mode
                        )
                        
                        # 提取知识图谱响应
                        if len(enhanced_messages) > 1:
                            knowledge_response = enhanced_messages[-1]
                            if knowledge_response.role == MessageRole.ASSISTANT and knowledge_response.content:
                                # 创建增强输入消息
                                input_msg = TextMessage(
                                    content=f"用户问题: {current_input}\n\n相关知识: {knowledge_response.content}",
                                    role=MessageRole.USER
                                )
                                logger.info("成功使用知识图谱增强输入")
                    except Exception as e:
                        logger.warning(f"知识图谱增强失败: {str(e)}")
                
                # 执行Agent
                logger.info(f"执行Agent[{i+1}/{len(agents)}]: {agent.name} (ID: {agent.id})")
                
                # 只有最后一个Agent使用流式响应
                if i == len(agents) - 1:
                    # 最后一个Agent直接流式输出
                    await agent_adapter.stream_to_service(
                        messages=[input_msg],
                        model_name=agent.model,
                        temperature=agent.temperature,
                        system_prompt=agent.system_prompt,
                        memory_key=f"agent_chain_{context.get('chain_id')}_{agent.id}",
                        stream_service=stream_service
                    )
                else:
                    # 中间Agent使用同步执行
                    response_messages = await agent_adapter.process_messages(
                        messages=[input_msg],
                        model_name=agent.model,
                        temperature=agent.temperature,
                        system_prompt=agent.system_prompt,
                        memory_key=f"agent_chain_{context.get('chain_id')}_{agent.id}"
                    )
                    
                    # 保存结果
                    context["results"][agent_id] = response_messages
                    
                    # 如果是中间Agent，将其输出作为下一个Agent的输入
                    if i < len(agents) - 1:
                        # 提取最终响应作为下一个Agent的输入
                        final_response = await self.message_router.extract_final_response(response_messages)
                        if isinstance(final_response.content, str):
                            current_input = final_response.content
                        else:
                            current_input = str(final_response.content)
                            
                        # 向流式服务发送中间Agent处理状态
                        intermediate_msg = TextMessage(
                            content=f"[系统] 正在处理: 已完成 Agent {agent.name}，进入下一步...",
                            role=MessageRole.SYSTEM
                        )
                        await stream_service.add_message(intermediate_msg, is_intermediate=True)
            
            # 完成所有Agent执行
            await stream_service.complete()
            
        except Exception as e:
            logger.error(f"执行Agent链时出错: {str(e)}")
            error_msg = TextMessage(
                content=f"执行Agent链时出错: {str(e)}",
                role=MessageRole.SYSTEM
            )
            await stream_service.add_message(error_msg)
            await stream_service.complete(error=True)
        
    async def _execute_parallel(
        self,
        agents: List[Dict[str, Any]],
        context: Dict[str, Any],
        stream: bool = False
    ) -> Union[List[Message], StreamService]:
        """
        并行执行多个Agent
        
        Args:
            agents: Agent列表
            context: 执行上下文
            stream: 是否使用流式响应
            
        Returns:
            执行结果消息或流式服务
        """
        # 暂不支持并行执行的流式响应
        if stream:
            raise NotImplementedError("暂不支持并行执行的流式响应")
        
        # 创建任务列表
        tasks = []
        input_message = context.get("current_input")
        
        # 为每个Agent创建执行任务
        for agent_config in agents:
            agent_id = agent_config.get("id")
            if not agent_id:
                raise ValueError(f"Agent配置缺少ID: {agent_config}")
                
            # 获取Agent
            agent = self._get_agent_by_id(agent_id)
            if not agent:
                raise ValueError(f"Agent不存在: {agent_id}")
                
            # 创建任务
            task = self._execute_single_agent(
                agent=agent,
                input_message=input_message,
                context=context
            )
            tasks.append(task)
        
        # 并行执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        all_messages = []
        for i, result in enumerate(results):
            agent_id = agents[i].get("id")
            
            if isinstance(result, Exception):
                logger.error(f"执行Agent {agent_id} 时出错: {str(result)}")
                error_msg = TextMessage(
                    content=f"执行Agent {agent_id} 时出错: {str(result)}",
                    role=MessageRole.SYSTEM
                )
                all_messages.append([error_msg])
            else:
                context["results"][agent_id] = result
                all_messages.append(result)
        
        # 合并所有消息
        combined_messages = await self.message_router.combine_messages(all_messages)
        return combined_messages
        
    async def _execute_conditional(
        self,
        agents: List[Dict[str, Any]],
        conditions: Dict[str, Any],
        context: Dict[str, Any],
        stream: bool = False
    ) -> Union[List[Message], StreamService]:
        """
        根据条件执行Agent
        
        Args:
            agents: Agent列表
            conditions: 条件配置
            context: 执行上下文
            stream: 是否使用流式响应
            
        Returns:
            执行结果消息或流式服务
        """
        # 暂不支持条件执行的流式响应
        if stream:
            raise NotImplementedError("暂不支持条件执行的流式响应")
        
        # 实现条件执行逻辑
        raise NotImplementedError("条件执行模式尚未实现")
        
    async def _execute_single_agent(
        self,
        agent: Assistant,
        input_message: str,
        context: Dict[str, Any]
    ) -> List[Message]:
        """
        执行单个Agent
        
        Args:
            agent: Agent实例
            input_message: 输入消息
            context: 执行上下文
            
        Returns:
            执行结果消息
        """
        # 创建Agent适配器
        agent_adapter = AgentAdapter(self.message_service, self.stream_service)
        
        # 创建输入消息
        input_msg = TextMessage(
            content=input_message,
            role=MessageRole.USER
        )
        
        # 执行Agent
        logger.info(f"执行Agent: {agent.name} (ID: {agent.id})")
        response_messages = await agent_adapter.process_messages(
            messages=[input_msg],
            model_name=agent.model,
            temperature=agent.temperature,
            system_prompt=agent.system_prompt,
            memory_key=f"agent_chain_{context.get('chain_id')}_{agent.id}"
        )
        
        return response_messages
        
    def _get_agent_by_id(self, agent_id: int) -> Optional[Assistant]:
        """
        通过ID获取Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent实例
        """
        from app.models.assistants import Assistant
        
        # 查询数据库获取Agent
        agent = self.db.query(Assistant).filter(Assistant.id == agent_id).first()
        return agent


# 创建依赖项函数
def get_agent_chain_executor(
    db: Session = Depends(get_db),
    message_service: MessageService = Depends(get_message_service),
    stream_service: StreamService = Depends(get_stream_service),
    message_router: MessageRouter = Depends(get_message_router)
) -> AgentChainExecutor:
    """
    获取Agent链执行器实例
    
    Args:
        db: 数据库会话
        message_service: 消息服务
        stream_service: 流式服务
        message_router: 消息路由器
        
    Returns:
        AgentChainExecutor实例
    """
    return AgentChainExecutor(
        message_service=message_service,
        stream_service=stream_service,
        message_router=message_router,
        db=db
    )
