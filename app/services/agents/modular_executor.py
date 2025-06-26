from typing import Dict, Any, List, Optional, AsyncIterator
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
import uuid
from enum import Enum

from app.services.agents.orchestration_parser import ExecutableWorkflow, ExecutionStep, ExecutionStrategy

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """执行上下文"""
    session_id: str
    workflow: ExecutableWorkflow
    input_data: Dict[str, Any]
    global_state: Dict[str, Any]
    execution_trace: List[Dict[str, Any]]
    current_step_index: int = 0
    is_cancelled: bool = False


@dataclass
class StepExecutionResult:
    """步骤执行结果"""
    step_id: str
    status: ExecutionStatus
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None


class ModularAgentExecutor:
    """模块化智能体执行引擎"""
    
    def __init__(self):
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.module_handlers = {
            'information_retrieval': self._execute_information_retrieval,
            'content_processing': self._execute_content_processing,
            'data_analysis_reasoning': self._execute_data_analysis_reasoning,
            'output_generation': self._execute_output_generation
        }
    
    async def execute_workflow(
        self, 
        workflow: ExecutableWorkflow, 
        input_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        执行工作流
        
        Args:
            workflow: 可执行工作流
            input_data: 输入数据
            session_id: 会话ID
            
        Yields:
            执行进度和结果
        """
        session_id = session_id or str(uuid.uuid4())
        
        logger.info(f"开始执行工作流: {workflow.name} (会话: {session_id})")
        
        # 创建执行上下文
        context = ExecutionContext(
            session_id=session_id,
            workflow=workflow,
            input_data=input_data,
            global_state={"input": input_data},
            execution_trace=[]
        )
        
        self.active_executions[session_id] = context
        
        try:
            # 发送开始执行事件
            yield {
                "event": "execution_started",
                "session_id": session_id,
                "workflow_name": workflow.name,
                "total_steps": len(workflow.steps),
                "timestamp": datetime.now().isoformat()
            }
            
            # 根据执行模式选择执行策略
            if workflow.execution_mode == "sequential":
                async for event in self._execute_sequential(context):
                    yield event
            elif workflow.execution_mode == "parallel":
                async for event in self._execute_parallel(context):
                    yield event
            elif workflow.execution_mode == "conditional":
                async for event in self._execute_conditional(context):
                    yield event
            else:
                raise ValueError(f"不支持的执行模式: {workflow.execution_mode}")
            
            # 发送完成事件
            yield {
                "event": "execution_completed",
                "session_id": session_id,
                "status": "success",
                "output_data": context.global_state.get("final_output"),
                "execution_trace": context.execution_trace,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            
            yield {
                "event": "execution_failed",
                "session_id": session_id,
                "error": str(e),
                "execution_trace": context.execution_trace,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            # 清理执行上下文
            self.active_executions.pop(session_id, None)
    
    async def _execute_sequential(self, context: ExecutionContext) -> AsyncIterator[Dict[str, Any]]:
        """顺序执行工作流"""
        logger.debug(f"开始顺序执行工作流: {context.workflow.name}")
        
        for i, step in enumerate(context.workflow.steps):
            if context.is_cancelled:
                logger.info(f"工作流执行被取消: {context.session_id}")
                break
            
            context.current_step_index = i
            
            # 发送步骤开始事件
            yield {
                "event": "step_started",
                "session_id": context.session_id,
                "step_id": step.step_id,
                "step_name": step.module_name,
                "step_index": i,
                "timestamp": datetime.now().isoformat()
            }
            
            # 执行步骤
            result = await self._execute_step(step, context)
            
            # 更新执行追踪
            context.execution_trace.append({
                "step_id": step.step_id,
                "module_name": step.module_name,
                "status": result.status.value,
                "duration_ms": result.duration_ms,
                "timestamp": datetime.now().isoformat(),
                "details": result.metadata,
                "error": result.error
            })
            
            # 更新全局状态
            if result.status == ExecutionStatus.SUCCESS and result.output_data:
                context.global_state[f"step_{step.step_id}_output"] = result.output_data
                context.global_state["last_output"] = result.output_data
            
            # 发送步骤完成事件
            yield {
                "event": "step_completed",
                "session_id": context.session_id,
                "step_id": step.step_id,
                "status": result.status.value,
                "output_data": result.output_data,
                "error": result.error,
                "timestamp": datetime.now().isoformat()
            }
            
            # 如果步骤失败，根据配置决定是否继续
            if result.status == ExecutionStatus.FAILED:
                logger.error(f"步骤执行失败: {step.step_id}, 错误: {result.error}")
                # 默认策略：失败后停止执行
                break
        
        # 设置最终输出
        context.global_state["final_output"] = self._generate_final_output(context)
    
    async def _execute_parallel(self, context: ExecutionContext) -> AsyncIterator[Dict[str, Any]]:
        """并行执行工作流"""
        logger.debug(f"开始并行执行工作流: {context.workflow.name}")
        
        # 创建并行任务
        tasks = []
        for i, step in enumerate(context.workflow.steps):
            task = asyncio.create_task(self._execute_step_with_context(step, context, i))
            tasks.append(task)
        
        # 等待所有任务完成
        step_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(step_results):
            step = context.workflow.steps[i]
            
            if isinstance(result, Exception):
                step_result = StepExecutionResult(
                    step_id=step.step_id,
                    status=ExecutionStatus.FAILED,
                    error=str(result)
                )
            else:
                step_result = result
            
            # 更新执行追踪
            context.execution_trace.append({
                "step_id": step.step_id,
                "module_name": step.module_name,
                "status": step_result.status.value,
                "duration_ms": step_result.duration_ms,
                "timestamp": datetime.now().isoformat(),
                "details": step_result.metadata,
                "error": step_result.error
            })
            
            # 发送步骤完成事件
            yield {
                "event": "step_completed",
                "session_id": context.session_id,
                "step_id": step.step_id,
                "status": step_result.status.value,
                "output_data": step_result.output_data,
                "error": step_result.error,
                "timestamp": datetime.now().isoformat()
            }
        
        # 设置最终输出
        context.global_state["final_output"] = self._generate_final_output(context)
    
    async def _execute_conditional(self, context: ExecutionContext) -> AsyncIterator[Dict[str, Any]]:
        """条件执行工作流"""
        logger.debug(f"开始条件执行工作流: {context.workflow.name}")
        
        for i, step in enumerate(context.workflow.steps):
            if context.is_cancelled:
                break
            
            context.current_step_index = i
            
            # 检查执行条件
            should_execute = await self._evaluate_step_condition(step, context)
            
            if not should_execute:
                logger.debug(f"跳过步骤 {step.step_id}：条件不满足")
                
                # 记录跳过的步骤
                context.execution_trace.append({
                    "step_id": step.step_id,
                    "module_name": step.module_name,
                    "status": ExecutionStatus.SKIPPED.value,
                    "duration_ms": 0,
                    "timestamp": datetime.now().isoformat(),
                    "details": {"reason": "条件不满足"}
                })
                
                yield {
                    "event": "step_skipped",
                    "session_id": context.session_id,
                    "step_id": step.step_id,
                    "reason": "条件不满足",
                    "timestamp": datetime.now().isoformat()
                }
                continue
            
            # 执行步骤
            yield {
                "event": "step_started",
                "session_id": context.session_id,
                "step_id": step.step_id,
                "step_name": step.module_name,
                "step_index": i,
                "timestamp": datetime.now().isoformat()
            }
            
            result = await self._execute_step(step, context)
            
            # 更新执行追踪和状态
            context.execution_trace.append({
                "step_id": step.step_id,
                "module_name": step.module_name,
                "status": result.status.value,
                "duration_ms": result.duration_ms,
                "timestamp": datetime.now().isoformat(),
                "details": result.metadata,
                "error": result.error
            })
            
            if result.status == ExecutionStatus.SUCCESS and result.output_data:
                context.global_state[f"step_{step.step_id}_output"] = result.output_data
                context.global_state["last_output"] = result.output_data
            
            yield {
                "event": "step_completed",
                "session_id": context.session_id,
                "step_id": step.step_id,
                "status": result.status.value,
                "output_data": result.output_data,
                "error": result.error,
                "timestamp": datetime.now().isoformat()
            }
        
        # 设置最终输出
        context.global_state["final_output"] = self._generate_final_output(context)
    
    async def _execute_step_with_context(
        self, 
        step: ExecutionStep, 
        context: ExecutionContext, 
        step_index: int
    ) -> StepExecutionResult:
        """在上下文中执行单个步骤（用于并行执行）"""
        return await self._execute_step(step, context)
    
    async def _execute_step(self, step: ExecutionStep, context: ExecutionContext) -> StepExecutionResult:
        """执行单个步骤"""
        start_time = datetime.now()
        
        logger.debug(f"执行步骤: {step.step_id} ({step.module_name})")
        
        try:
            # 获取模块处理器
            handler = self.module_handlers.get(step.module_type)
            if not handler:
                raise ValueError(f"未找到模块处理器: {step.module_type}")
            
            # 执行模块
            output_data = await handler(step, context)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return StepExecutionResult(
                step_id=step.step_id,
                status=ExecutionStatus.SUCCESS,
                output_data=output_data,
                duration_ms=duration_ms,
                metadata={
                    "module_type": step.module_type,
                    "tools_used": step.tools,
                    "kb_queried": step.knowledge_bases,
                    "execution_strategy": step.execution_strategy.value
                }
            )
            
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"步骤执行失败: {step.step_id}, 错误: {str(e)}")
            
            return StepExecutionResult(
                step_id=step.step_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def _execute_information_retrieval(
        self, 
        step: ExecutionStep, 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行信息获取模块"""
        logger.debug(f"执行信息获取模块: {step.step_id}")
        
        # 模拟信息获取过程
        await asyncio.sleep(0.5)  # 模拟处理时间
        
        # 获取输入查询
        query = context.global_state.get("input", {}).get("query", "默认查询")
        
        # 模拟从知识库和工具获取信息
        retrieved_info = {
            "query": query,
            "sources": [],
            "knowledge_base_results": [],
            "tool_results": []
        }
        
        # 模拟知识库查询
        for kb in step.knowledge_bases:
            kb_result = {
                "knowledge_base": kb,
                "results": [
                    {"content": f"来自{kb}的相关信息", "score": 0.85},
                    {"content": f"来自{kb}的次要信息", "score": 0.72}
                ]
            }
            retrieved_info["knowledge_base_results"].append(kb_result)
        
        # 模拟工具调用
        for tool in step.tools:
            tool_result = {
                "tool": tool,
                "output": f"工具{tool}的执行结果",
                "success": True
            }
            retrieved_info["tool_results"].append(tool_result)
        
        return retrieved_info
    
    async def _execute_content_processing(
        self, 
        step: ExecutionStep, 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行内容处理模块"""
        logger.debug(f"执行内容处理模块: {step.step_id}")
        
        # 模拟内容处理过程
        await asyncio.sleep(0.3)
        
        # 获取上一步的输出或输入数据
        input_data = context.global_state.get("last_output") or context.global_state.get("input", {})
        
        processed_content = {
            "original_input": input_data,
            "processed_text": "经过处理的文本内容",
            "extracted_entities": ["实体1", "实体2", "实体3"],
            "sentiment": "positive",
            "key_topics": ["主题1", "主题2"],
            "processing_metadata": {
                "tools_applied": step.tools,
                "processing_time": datetime.now().isoformat()
            }
        }
        
        return processed_content
    
    async def _execute_data_analysis_reasoning(
        self, 
        step: ExecutionStep, 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行数据分析推理模块"""
        logger.debug(f"执行数据分析推理模块: {step.step_id}")
        
        # 模拟推理过程
        await asyncio.sleep(0.4)
        
        # 获取前面步骤的输出
        previous_outputs = [
            context.global_state.get(key) 
            for key in context.global_state.keys() 
            if key.startswith("step_") and key.endswith("_output")
        ]
        
        reasoning_result = {
            "analysis_type": "综合分析",
            "insights": [
                "洞察1：基于数据的关键发现",
                "洞察2：模式识别结果",
                "洞察3：趋势分析结论"
            ],
            "confidence_scores": {
                "insight_1": 0.92,
                "insight_2": 0.87,
                "insight_3": 0.79
            },
            "reasoning_chain": [
                "步骤1：数据收集和预处理",
                "步骤2：模式识别和分析",
                "步骤3：结论推导和验证"
            ],
            "used_data": len(previous_outputs)
        }
        
        return reasoning_result
    
    async def _execute_output_generation(
        self, 
        step: ExecutionStep, 
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行输出生成模块"""
        logger.debug(f"执行输出生成模块: {step.step_id}")
        
        # 模拟输出生成过程
        await asyncio.sleep(0.2)
        
        # 综合所有前面步骤的输出
        all_outputs = {
            key: value for key, value in context.global_state.items()
            if key.startswith("step_") and key.endswith("_output")
        }
        
        final_output = {
            "final_answer": f"基于{len(all_outputs)}个处理步骤的综合答案",
            "summary": "这是对所有分析结果的综合总结",
            "recommendations": [
                "建议1：基于分析结果的行动建议",
                "建议2：后续改进方向",
                "建议3：风险预防措施"
            ],
            "confidence": 0.88,
            "sources_used": self._extract_sources_from_outputs(all_outputs),
            "generation_metadata": {
                "steps_processed": len(all_outputs),
                "total_processing_time": self._calculate_total_time(context),
                "generation_timestamp": datetime.now().isoformat()
            }
        }
        
        return final_output
    
    async def _evaluate_step_condition(self, step: ExecutionStep, context: ExecutionContext) -> bool:
        """评估步骤执行条件"""
        if not step.conditions:
            return True
        
        # 简单的条件评估逻辑
        condition = step.conditions.get("condition", "")
        
        if "previous_success" in condition:
            # 检查前面的步骤是否成功
            return len([
                trace for trace in context.execution_trace 
                if trace["status"] == "success"
            ]) > 0
        
        if "has_data" in condition:
            # 检查是否有可用数据
            return bool(context.global_state.get("last_output"))
        
        # 默认执行
        return True
    
    def _generate_final_output(self, context: ExecutionContext) -> Dict[str, Any]:
        """生成最终输出"""
        successful_steps = [
            trace for trace in context.execution_trace 
            if trace["status"] == "success"
        ]
        
        return {
            "workflow_name": context.workflow.name,
            "execution_summary": {
                "total_steps": len(context.workflow.steps),
                "successful_steps": len(successful_steps),
                "execution_mode": context.workflow.execution_mode,
                "session_id": context.session_id
            },
            "final_result": context.global_state.get("last_output"),
            "processing_trace": context.execution_trace
        }
    
    def _extract_sources_from_outputs(self, outputs: Dict[str, Any]) -> List[str]:
        """从输出中提取数据源"""
        sources = []
        for output in outputs.values():
            if isinstance(output, dict):
                if "sources" in output:
                    sources.extend(output["sources"])
                if "knowledge_base_results" in output:
                    sources.extend([
                        kb["knowledge_base"] 
                        for kb in output["knowledge_base_results"]
                    ])
        return list(set(sources))
    
    def _calculate_total_time(self, context: ExecutionContext) -> int:
        """计算总处理时间"""
        total_duration = sum(
            trace.get("duration_ms", 0) 
            for trace in context.execution_trace
        )
        return total_duration
    
    async def cancel_execution(self, session_id: str) -> bool:
        """取消执行"""
        if session_id in self.active_executions:
            self.active_executions[session_id].is_cancelled = True
            logger.info(f"已请求取消执行: {session_id}")
            return True
        return False
    
    def get_execution_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        if session_id not in self.active_executions:
            return None
        
        context = self.active_executions[session_id]
        
        return {
            "session_id": session_id,
            "workflow_name": context.workflow.name,
            "current_step": context.current_step_index,
            "total_steps": len(context.workflow.steps),
            "execution_trace": context.execution_trace,
            "is_cancelled": context.is_cancelled,
            "status": "cancelled" if context.is_cancelled else "running"
        } 