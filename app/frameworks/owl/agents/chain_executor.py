"""
OWL框架Agent链执行器
负责协调和执行多个Agent组成的链式调用
"""

from typing import Any, Dict, List, Optional, Union, AsyncGenerator
import logging
import uuid
import json
import asyncio
from datetime import datetime

from app.frameworks.owl.agents.interfaces import (
    AgentConfig, AgentInputSchema, AgentOutputSchema, 
    AgentChainStep, AgentChainDefinition
)
from app.frameworks.owl.utils.decorators import AgentInput, AgentOutput
from app.frameworks.owl.utils.chain_transformer import ChainDataTransformer
from app.frameworks.owl.utils.message_adapter import AgentMessageAdapter, AgentChainMessageAdapter

from app.messaging.core.models import (
    Message, MessageType, MessageRole, TextMessage, 
    StatusMessage, ErrorMessage, DoneMessage
)
from app.messaging.services.message_service import MessageService
from app.messaging.services.stream_service import StreamService

logger = logging.getLogger(__name__)


class AgentChainExecutor:
    """Agent链执行器
    
    负责根据链定义协调多个Agent的执行，处理数据的传递和转换
    """
    
    def __init__(
        self, 
        message_service: Optional[MessageService] = None,
        stream_service: Optional[StreamService] = None
    ):
        """初始化链执行器
        
        Args:
            message_service: 消息服务
            stream_service: 流服务
        """
        self.transformer = ChainDataTransformer()
        self.message_service = message_service
        self.stream_service = stream_service
        self.agent_registry = {}  # 用于缓存已创建的Agent实例
    
    async def execute_chain(
        self,
        chain_config: Union[Dict[str, Any], AgentChainDefinition],
        input_message: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        stream_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Message, None]]:
        """执行Agent链
        
        Args:
            chain_config: 链配置
            input_message: 输入消息
            context: 上下文信息
            stream: 是否流式输出
            stream_id: 流ID
            user_id: 用户ID
            
        Returns:
            链执行结果或消息流
        """
        # 生成执行追踪ID
        trace_id = str(uuid.uuid4())
        
        # 处理链配置
        if isinstance(chain_config, dict):
            chain_def = AgentChainDefinition(**chain_config)
        else:
            chain_def = chain_config
        
        # 设置初始上下文
        if context is None:
            context = {}
        
        context.update({
            "trace_id": trace_id,
            "user_id": user_id,
            "chain_id": chain_def.id,
            "chain_name": chain_def.name,
            "start_time": datetime.now().isoformat(),
            "input_message": input_message
        })
        
        # 设置链上下文
        self.transformer.set_context(trace_id, context)
        
        # 创建结果对象
        result = {
            "execution_id": trace_id,
            "chain_id": chain_def.id or "",
            "chain_name": chain_def.name,
            "status": "running",
            "start_time": context["start_time"],
            "steps": [],
            "result": None
        }
        
        # 处理流式输出
        if stream:
            # 创建消息流
            if self.stream_service:
                return await self._execute_chain_stream(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context,
                    stream_id=stream_id
                )
            else:
                # 如果没有流服务，则使用同步方式并返回错误
                logger.warning("请求流式输出但流服务不可用，将使用同步执行")
        
        # 同步执行链
        try:
            # 根据执行模式选择执行方法
            if chain_def.mode == "parallel":
                result = await self._execute_parallel(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context
                )
            elif chain_def.mode == "conditional":
                result = await self._execute_conditional(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context
                )
            else:
                # 默认顺序执行
                result = await self._execute_sequential(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context
                )
            
            # 更新结果状态
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            
            # 清理上下文
            self.transformer.clear_context(trace_id)
            
            return result
            
        except Exception as e:
            logger.error(f"执行Agent链时出错: {str(e)}")
            
            # 更新错误状态
            result["status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = datetime.now().isoformat()
            
            # 清理上下文
            self.transformer.clear_context(trace_id)
            
            return result
    
    async def _execute_sequential(
        self,
        chain_def: AgentChainDefinition,
        input_message: str,
        trace_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """顺序执行链
        
        Args:
            chain_def: 链定义
            input_message: 输入消息
            trace_id: 追踪ID
            context: 上下文
            
        Returns:
            执行结果
        """
        result = {
            "execution_id": trace_id,
            "chain_id": chain_def.id or "",
            "chain_name": chain_def.name,
            "status": "running",
            "start_time": context["start_time"],
            "steps": [],
            "result": None
        }
        
        # 初始输入数据
        data = {
            "input": input_message,
            "context": context
        }
        
        # 上一步的输出
        prev_output = None
        
        # 顺序执行每个步骤
        for i, step in enumerate(chain_def.steps):
            step_data = {
                "agent_id": step.agent_id,
                "agent_name": step.agent_name,
                "position": step.position,
                "role": step.role,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "output": None,
                "error": None
            }
            
            try:
                # 获取Agent实例
                agent = await self._get_agent(step.agent_id, step.agent_name)
                
                if not agent:
                    raise ValueError(f"无法找到Agent: {step.agent_name} (ID: {step.agent_id})")
                
                # 转换输入
                agent_input = self.transformer.transform_to_agent_input(
                    data=data, 
                    step=step,
                    prev_output=prev_output,
                    trace_id=trace_id
                )
                
                # 执行Agent
                logger.info(f"执行Agent链步骤 {i+1}/{len(chain_def.steps)}: {step.agent_name}")
                
                if hasattr(agent, "process"):
                    output = await agent.process(agent_input)
                else:
                    # 尝试兼容不同的Agent接口
                    if hasattr(agent, "run_task"):
                        output_content, _, metadata = await agent.run_task(agent_input.query)
                        output = AgentOutputSchema(
                            content=output_content,
                            metadata=metadata or {}
                        )
                    elif hasattr(agent, "aquery"):
                        output_content = await agent.aquery(agent_input.query)
                        output = AgentOutputSchema(
                            content=output_content,
                            metadata={}
                        )
                    elif hasattr(agent, "query"):
                        output_content = agent.query(agent_input.query)
                        output = AgentOutputSchema(
                            content=output_content,
                            metadata={}
                        )
                    else:
                        raise ValueError(f"Agent {step.agent_name} 不支持任何已知的处理方法")
                
                # 转换输出
                transformed_output = self.transformer.transform_agent_output(
                    output=output,
                    step=step,
                    trace_id=trace_id
                )
                
                # 更新数据
                data.update(transformed_output.get("transformed", {}))
                
                # 保存步骤输出
                step_data["output"] = output
                step_data["status"] = "completed"
                step_data["end_time"] = datetime.now().isoformat()
                
                # 更新上一步输出
                prev_output = output
                
            except Exception as e:
                logger.error(f"执行Agent链步骤 {step.agent_name} 时出错: {str(e)}")
                
                # 更新步骤状态
                step_data["status"] = "failed"
                step_data["error"] = str(e)
                step_data["end_time"] = datetime.now().isoformat()
                
                # 添加步骤结果
                result["steps"].append(step_data)
                
                # 终止链执行
                result["status"] = "failed"
                result["error"] = f"步骤 {step.agent_name} 执行失败: {str(e)}"
                result["end_time"] = datetime.now().isoformat()
                
                return result
            
            # 添加步骤结果
            result["steps"].append(step_data)
        
        # 设置最终结果
        if prev_output:
            result["result"] = prev_output
        
        # 更新链状态
        result["status"] = "completed"
        result["end_time"] = datetime.now().isoformat()
        
        return result
    
    async def _execute_parallel(
        self,
        chain_def: AgentChainDefinition,
        input_message: str,
        trace_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """并行执行链
        
        Args:
            chain_def: 链定义
            input_message: 输入消息
            trace_id: 追踪ID
            context: 上下文
            
        Returns:
            执行结果
        """
        # 创建结果对象
        result = {
            "execution_id": trace_id,
            "chain_id": chain_def.id or "",
            "chain_name": chain_def.name,
            "status": "running",
            "start_time": context["start_time"],
            "steps": [],
            "result": None
        }
        
        # 初始输入数据
        data = {
            "input": input_message,
            "context": context
        }
        
        # 创建任务列表
        tasks = []
        step_data_list = []
        
        # 准备所有步骤
        for step in chain_def.steps:
            step_data = {
                "agent_id": step.agent_id,
                "agent_name": step.agent_name,
                "position": step.position,
                "role": step.role,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "output": None,
                "error": None
            }
            step_data_list.append(step_data)
            
            # 创建执行任务
            task = self._execute_step(
                step=step, 
                data=data, 
                trace_id=trace_id
            )
            tasks.append(task)
        
        # 并行执行所有任务
        try:
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            all_outputs = []
            for i, step_result in enumerate(step_results):
                step_data = step_data_list[i]
                
                if isinstance(step_result, Exception):
                    # 处理异常
                    logger.error(f"执行Agent {step_data['agent_name']} 时出错: {str(step_result)}")
                    step_data["status"] = "failed"
                    step_data["error"] = str(step_result)
                    step_data["end_time"] = datetime.now().isoformat()
                else:
                    # 处理成功结果
                    step_data["status"] = "completed"
                    step_data["output"] = step_result.get("output")
                    step_data["end_time"] = datetime.now().isoformat()
                    
                    # 收集输出
                    all_outputs.append(step_result.get("output"))
                
                # 添加到结果
                result["steps"].append(step_data)
            
            # 合并结果（简单实现，实际应根据业务需求定制）
            if all_outputs:
                combined_content = ""
                for i, output in enumerate(all_outputs):
                    if output and hasattr(output, 'content'):
                        combined_content += f"{chain_def.steps[i].agent_name}: {output.content}\n\n"
                
                # 创建合并输出
                result["result"] = AgentOutputSchema(
                    content=combined_content.strip(),
                    metadata={
                        "combined_from": len(all_outputs),
                        "source": "parallel_chain"
                    }
                )
            
            # 更新链状态
            result["status"] = "completed"
            result["end_time"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"执行并行Agent链时出错: {str(e)}")
            
            # 更新错误状态
            result["status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = datetime.now().isoformat()
            
            return result
    
    async def _execute_conditional(
        self,
        chain_def: AgentChainDefinition,
        input_message: str,
        trace_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """条件执行链
        
        Args:
            chain_def: 链定义
            input_message: 输入消息
            trace_id: 追踪ID
            context: 上下文
            
        Returns:
            执行结果
        """
        # 简化版条件执行，实际应该根据条件配置执行不同的路径
        # 这里简单实现为按顺序执行，但检查每个步骤的条件
        
        result = {
            "execution_id": trace_id,
            "chain_id": chain_def.id or "",
            "chain_name": chain_def.name,
            "status": "running",
            "start_time": context["start_time"],
            "steps": [],
            "result": None
        }
        
        # 初始输入数据
        data = {
            "input": input_message,
            "context": context
        }
        
        # 上一步的输出
        prev_output = None
        
        # 条件执行每个步骤
        for i, step in enumerate(chain_def.steps):
            step_data = {
                "agent_id": step.agent_id,
                "agent_name": step.agent_name,
                "position": step.position,
                "role": step.role,
                "status": "pending",
                "start_time": datetime.now().isoformat(),
                "output": None,
                "error": None
            }
            
            # 检查条件
            should_execute = True
            if step.condition:
                # 简单条件检查，实际应该解析表达式
                try:
                    condition_met = eval(
                        step.condition, 
                        {"__builtins__": {}}, 
                        {**data, "context": context}
                    )
                    should_execute = bool(condition_met)
                except Exception as e:
                    logger.error(f"评估条件时出错: {str(e)}")
                    step_data["status"] = "skipped"
                    step_data["error"] = f"条件评估错误: {str(e)}"
                    result["steps"].append(step_data)
                    continue
            
            if not should_execute:
                step_data["status"] = "skipped"
                step_data["end_time"] = datetime.now().isoformat()
                result["steps"].append(step_data)
                continue
            
            # 执行步骤
            try:
                step_data["status"] = "running"
                
                # 获取Agent实例
                agent = await self._get_agent(step.agent_id, step.agent_name)
                
                if not agent:
                    raise ValueError(f"无法找到Agent: {step.agent_name} (ID: {step.agent_id})")
                
                # 转换输入
                agent_input = self.transformer.transform_to_agent_input(
                    data=data, 
                    step=step,
                    prev_output=prev_output,
                    trace_id=trace_id
                )
                
                # 执行Agent
                logger.info(f"执行Agent链步骤 {i+1}/{len(chain_def.steps)}: {step.agent_name}")
                
                if hasattr(agent, "process"):
                    output = await agent.process(agent_input)
                else:
                    # 尝试兼容不同的Agent接口
                    if hasattr(agent, "run_task"):
                        output_content, _, metadata = await agent.run_task(agent_input.query)
                        output = AgentOutputSchema(
                            content=output_content,
                            metadata=metadata or {}
                        )
                    elif hasattr(agent, "aquery"):
                        output_content = await agent.aquery(agent_input.query)
                        output = AgentOutputSchema(
                            content=output_content,
                            metadata={}
                        )
                    elif hasattr(agent, "query"):
                        output_content = agent.query(agent_input.query)
                        output = AgentOutputSchema(
                            content=output_content,
                            metadata={}
                        )
                    else:
                        raise ValueError(f"Agent {step.agent_name} 不支持任何已知的处理方法")
                
                # 转换输出
                transformed_output = self.transformer.transform_agent_output(
                    output=output,
                    step=step,
                    trace_id=trace_id
                )
                
                # 更新数据
                data.update(transformed_output.get("transformed", {}))
                
                # 保存步骤输出
                step_data["output"] = output
                step_data["status"] = "completed"
                step_data["end_time"] = datetime.now().isoformat()
                
                # 更新上一步输出
                prev_output = output
                
            except Exception as e:
                logger.error(f"执行Agent链步骤 {step.agent_name} 时出错: {str(e)}")
                
                # 尝试使用后备处理
                if step.fallback:
                    try:
                        logger.info(f"尝试使用后备处理: {step.fallback}")
                        # 处理后备逻辑（简化实现）
                        step_data["status"] = "fallback"
                        step_data["error"] = str(e)
                        step_data["end_time"] = datetime.now().isoformat()
                    except Exception as fallback_error:
                        logger.error(f"后备处理失败: {str(fallback_error)}")
                        step_data["status"] = "failed"
                        step_data["error"] = f"{str(e)}; 后备处理失败: {str(fallback_error)}"
                        step_data["end_time"] = datetime.now().isoformat()
                else:
                    # 更新步骤状态
                    step_data["status"] = "failed"
                    step_data["error"] = str(e)
                    step_data["end_time"] = datetime.now().isoformat()
            
            # 添加步骤结果
            result["steps"].append(step_data)
        
        # 设置最终结果
        if prev_output:
            result["result"] = prev_output
        
        # 更新链状态
        result["status"] = "completed"
        result["end_time"] = datetime.now().isoformat()
        
        return result
    
    async def _execute_step(
        self, 
        step: AgentChainStep, 
        data: Dict[str, Any],
        trace_id: str
    ) -> Dict[str, Any]:
        """执行单个步骤
        
        Args:
            step: 步骤定义
            data: 输入数据
            trace_id: 追踪ID
            
        Returns:
            步骤执行结果
        """
        try:
            # 获取Agent实例
            agent = await self._get_agent(step.agent_id, step.agent_name)
            
            if not agent:
                raise ValueError(f"无法找到Agent: {step.agent_name} (ID: {step.agent_id})")
            
            # 转换输入
            agent_input = self.transformer.transform_to_agent_input(
                data=data, 
                step=step,
                trace_id=trace_id
            )
            
            # 执行Agent
            logger.info(f"执行Agent链步骤: {step.agent_name}")
            
            if hasattr(agent, "process"):
                output = await agent.process(agent_input)
            else:
                # 尝试兼容不同的Agent接口
                if hasattr(agent, "run_task"):
                    output_content, _, metadata = await agent.run_task(agent_input.query)
                    output = AgentOutputSchema(
                        content=output_content,
                        metadata=metadata or {}
                    )
                elif hasattr(agent, "aquery"):
                    output_content = await agent.aquery(agent_input.query)
                    output = AgentOutputSchema(
                        content=output_content,
                        metadata={}
                    )
                elif hasattr(agent, "query"):
                    output_content = agent.query(agent_input.query)
                    output = AgentOutputSchema(
                        content=output_content,
                        metadata={}
                    )
                else:
                    raise ValueError(f"Agent {step.agent_name} 不支持任何已知的处理方法")
            
            # 转换输出
            transformed_output = self.transformer.transform_agent_output(
                output=output,
                step=step,
                trace_id=trace_id
            )
            
            return {
                "status": "completed",
                "output": output,
                "transformed": transformed_output.get("transformed", {})
            }
            
        except Exception as e:
            logger.error(f"执行步骤 {step.agent_name} 时出错: {str(e)}")
            raise
    
    async def _execute_chain_stream(
        self,
        chain_def: AgentChainDefinition,
        input_message: str,
        trace_id: str,
        context: Dict[str, Any],
        stream_id: Optional[str] = None
    ) -> AsyncGenerator[Message, None]:
        """流式执行链
        
        Args:
            chain_def: 链定义
            input_message: 输入消息
            trace_id: 追踪ID
            context: 上下文
            stream_id: 流ID
            
        Returns:
            消息流
        """
        # 如果没有消息服务，无法提供流式响应
        if not self.message_service or not self.stream_service:
            # 创建错误消息
            async def error_generator():
                yield ErrorMessage(
                    content={"message": "消息服务或流服务不可用，无法提供流式响应"},
                    metadata={"source": "agent_chain_executor"}
                )
                yield DoneMessage()
                
            return error_generator()
        
        # 创建消息流
        stream = self.stream_service.create_chain_stream(
            stream_id=stream_id or trace_id,
            chain_id=chain_def.id,
            chunk_mode=False
        )
        
        # 开始流
        await stream.start_stream()
        
        # 创建执行任务
        task = asyncio.create_task(
            self._stream_chain_execution(
                stream=stream,
                chain_def=chain_def,
                input_message=input_message,
                trace_id=trace_id,
                context=context
            )
        )
        
        # 返回消息流
        return stream.get_message_stream()
    
    async def _stream_chain_execution(
        self,
        stream: Any,
        chain_def: AgentChainDefinition,
        input_message: str,
        trace_id: str,
        context: Dict[str, Any]
    ) -> None:
        """流式执行链处理
        
        Args:
            stream: 消息流
            chain_def: 链定义
            input_message: 输入消息
            trace_id: 追踪ID
            context: 上下文
        """
        try:
            # 执行链
            if chain_def.mode == "parallel":
                result = await self._execute_parallel(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context
                )
            elif chain_def.mode == "conditional":
                result = await self._execute_conditional(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context
                )
            else:
                # 默认顺序执行
                result = await self._execute_sequential(
                    chain_def=chain_def,
                    input_message=input_message,
                    trace_id=trace_id,
                    context=context
                )
            
            # 将结果添加到流
            if result["result"]:
                # 转换为消息
                messages = AgentChainMessageAdapter.chain_result_to_messages(
                    result, include_intermediate=False
                )
                
                # 添加到流
                for msg in messages:
                    await stream.add_message(msg)
            else:
                # 没有结果，添加错误消息
                await stream.add_error("Agent链执行完成，但没有生成结果")
        
        except Exception as e:
            logger.error(f"流式执行Agent链时出错: {str(e)}")
            await stream.add_error(f"执行Agent链时出错: {str(e)}")
        
        finally:
            # 结束流
            await stream.end_stream()
            
            # 清理上下文
            self.transformer.clear_context(trace_id)
    
    async def _get_agent(self, agent_id: int, agent_name: str) -> Any:
        """获取Agent实例
        
        Args:
            agent_id: Agent ID
            agent_name: Agent名称
            
        Returns:
            Agent实例
        """
        # 检查缓存
        cache_key = f"{agent_id}:{agent_name}"
        if cache_key in self.agent_registry:
            return self.agent_registry[cache_key]
        
        # 从工厂获取，实际实现应根据系统架构定制
        try:
            # 示例获取Agent的代码，实际需要替换
            from app.core.agent_manager import get_agent_by_id
            agent = await get_agent_by_id(agent_id)
            
            # 缓存Agent
            if agent:
                self.agent_registry[cache_key] = agent
                
            return agent
            
        except Exception as e:
            logger.error(f"获取Agent实例时出错: {str(e)}")
            return None
