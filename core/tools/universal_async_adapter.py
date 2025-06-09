"""
通用工具异步适配器
为现有工具提供异步并发能力，无需修改原有工具代码
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Callable, Union, Type
from functools import wraps
from dataclasses import dataclass, field

from llama_index.core.tools import BaseTool, FunctionTool
from core.tools.async_execution_engine import (
    AsyncExecutionEngine,
    ExecutionConfig,
    TaskType,
    TaskResult,
    AggregatedResult,
    get_global_engine
)

logger = logging.getLogger(__name__)


@dataclass
class AsyncTaskDefinition:
    """异步任务定义"""
    task_func: Callable          # 任务函数
    task_name: str               # 任务名称
    task_type: TaskType          # 任务类型
    parameters: Dict[str, Any] = field(default_factory=dict)  # 任务参数
    timeout: Optional[int] = None  # 超时时间
    retry_count: int = 3         # 重试次数


class UniversalAsyncAdapter:
    """通用工具异步适配器"""
    
    def __init__(
        self,
        execution_config: Optional[ExecutionConfig] = None,
        enable_global_engine: bool = True
    ):
        """初始化异步适配器"""
        self.execution_config = execution_config
        self.enable_global_engine = enable_global_engine
        self.engine: Optional[AsyncExecutionEngine] = None
        self._initialized = False
    
    async def initialize(self):
        """初始化异步执行引擎"""
        if self._initialized:
            return
        
        try:
            if self.enable_global_engine:
                self.engine = await get_global_engine()
            else:
                self.engine = AsyncExecutionEngine(self.execution_config or ExecutionConfig())
                await self.engine.initialize()
            
            self._initialized = True
            logger.info("通用异步适配器初始化完成")
            
        except Exception as e:
            logger.error(f"通用异步适配器初始化失败: {str(e)}")
            raise
    
    async def run_concurrent_tasks(
        self,
        task_definitions: List[AsyncTaskDefinition],
        aggregator: Optional[Callable] = None,
        max_results: Optional[int] = None
    ) -> AggregatedResult:
        """
        并发运行多个任务
        
        Args:
            task_definitions: 任务定义列表
            aggregator: 结果聚合函数
            max_results: 最大结果数
            
        Returns:
            聚合执行结果
        """
        await self.initialize()
        
        try:
            logger.info(f"开始并发执行 {len(task_definitions)} 个任务")
            
            # 创建任务函数列表
            tasks = []
            for task_def in task_definitions:
                # 包装任务函数，添加参数
                wrapped_task = self._wrap_task_with_params(task_def)
                tasks.append(wrapped_task)
            
            # 确定任务类型（取最常见的类型）
            task_types = [t.task_type for t in task_definitions]
            most_common_type = max(set(task_types), key=task_types.count)
            
            # 执行并发任务
            result = await self.engine.execute_concurrent_tasks(
                tasks=tasks,
                task_type=most_common_type,
                aggregator=aggregator,
                max_results=max_results
            )
            
            logger.info(
                f"并发任务执行完成: 成功 {result.success_count}, "
                f"失败 {result.failure_count}, 耗时 {result.total_execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"并发任务执行失败: {str(e)}")
            raise
    
    def _wrap_task_with_params(self, task_def: AsyncTaskDefinition) -> Callable:
        """包装任务函数，添加参数"""
        async def wrapped_task():
            try:
                # 如果是异步函数
                if asyncio.iscoroutinefunction(task_def.task_func):
                    return await task_def.task_func(**task_def.parameters)
                # 如果是同步函数
                else:
                    return task_def.task_func(**task_def.parameters)
            except Exception as e:
                logger.error(f"任务 {task_def.task_name} 执行失败: {str(e)}")
                raise
        
        wrapped_task.__name__ = task_def.task_name
        return wrapped_task
    
    def create_multi_input_tool(
        self,
        base_tool: Union[BaseTool, Callable],
        input_variations: List[Dict[str, Any]],
        tool_name: str = "multi_input_tool",
        task_type: TaskType = TaskType.IO_BOUND,
        aggregator: Optional[Callable] = None
    ) -> Callable:
        """
        创建多输入并发工具
        
        Args:
            base_tool: 基础工具或函数
            input_variations: 输入参数变化列表
            tool_name: 工具名称
            task_type: 任务类型
            aggregator: 结果聚合函数
            
        Returns:
            并发执行的工具函数
        """
        async def multi_input_tool(**base_params) -> Any:
            """多输入并发工具函数"""
            await self.initialize()
            
            # 创建任务定义
            task_definitions = []
            for i, variation in enumerate(input_variations):
                # 合并基础参数和变化参数
                merged_params = {**base_params, **variation}
                
                # 确定调用函数
                if isinstance(base_tool, BaseTool):
                    task_func = base_tool._run if hasattr(base_tool, '_run') else base_tool.run
                else:
                    task_func = base_tool
                
                task_def = AsyncTaskDefinition(
                    task_func=task_func,
                    task_name=f"{tool_name}_{i}",
                    task_type=task_type,
                    parameters=merged_params
                )
                task_definitions.append(task_def)
            
            # 执行并发任务
            result = await self.run_concurrent_tasks(
                task_definitions, aggregator
            )
            
            return result.aggregated_data if result.aggregated_data is not None else result.task_results
        
        return multi_input_tool
    
    def create_parallel_search_tool(
        self,
        search_tools: List[Union[BaseTool, Callable]],
        search_queries: List[str],
        tool_name: str = "parallel_search",
        aggregator: Optional[Callable] = None
    ) -> Callable:
        """
        创建并行搜索工具
        
        Args:
            search_tools: 搜索工具列表
            search_queries: 搜索查询列表  
            tool_name: 工具名称
            aggregator: 结果聚合函数
            
        Returns:
            并行搜索工具函数
        """
        async def parallel_search_tool(**base_params) -> Any:
            """并行搜索工具函数"""
            await self.initialize()
            
            task_definitions = []
            
            # 为每个工具和每个查询创建任务
            for i, tool in enumerate(search_tools):
                for j, query in enumerate(search_queries):
                    # 合并参数
                    search_params = {**base_params, "query": query}
                    
                    # 确定调用函数
                    if isinstance(tool, BaseTool):
                        task_func = tool._run if hasattr(tool, '_run') else tool.run
                    else:
                        task_func = tool
                    
                    task_def = AsyncTaskDefinition(
                        task_func=task_func,
                        task_name=f"{tool_name}_tool{i}_query{j}",
                        task_type=TaskType.IO_BOUND,
                        parameters=search_params
                    )
                    task_definitions.append(task_def)
            
            # 执行并发搜索
            result = await self.run_concurrent_tasks(
                task_definitions, aggregator
            )
            
            return result.aggregated_data if result.aggregated_data is not None else result.task_results
        
        return parallel_search_tool


def async_tool_decorator(
    task_type: TaskType = TaskType.IO_BOUND,
    execution_config: Optional[ExecutionConfig] = None,
    enable_concurrent_inputs: bool = False
):
    """
    异步工具装饰器
    为现有工具函数添加异步并发能力
    
    Args:
        task_type: 任务类型
        execution_config: 执行配置
        enable_concurrent_inputs: 是否启用并发输入处理
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 创建适配器
            adapter = UniversalAsyncAdapter(execution_config)
            await adapter.initialize()
            
            # 如果启用并发输入处理且有多个输入
            if enable_concurrent_inputs and len(args) > 1:
                # 为每个输入创建任务
                task_definitions = []
                for i, arg in enumerate(args):
                    task_def = AsyncTaskDefinition(
                        task_func=func,
                        task_name=f"{func.__name__}_{i}",
                        task_type=task_type,
                        parameters={"input": arg, **kwargs}
                    )
                    task_definitions.append(task_def)
                
                # 执行并发任务
                result = await adapter.run_concurrent_tasks(task_definitions)
                return result.aggregated_data if result.aggregated_data else result.task_results
            else:
                # 单个任务执行
                task_def = AsyncTaskDefinition(
                    task_func=func,
                    task_name=func.__name__,
                    task_type=task_type,
                    parameters={"args": args, "kwargs": kwargs}
                )
                
                result = await adapter.run_concurrent_tasks([task_def])
                return result.task_results[0].result if result.task_results else None
        
        return async_wrapper
    return decorator


def create_concurrent_tool_wrapper(
    tools: List[Union[BaseTool, Callable]],
    tool_name: str = "concurrent_tool",
    aggregator: Optional[Callable] = None
) -> Callable:
    """
    创建并发工具包装器
    
    Args:
        tools: 工具列表
        tool_name: 工具名称
        aggregator: 结果聚合函数
        
    Returns:
        并发执行的工具函数
    """
    async def concurrent_tool_wrapper(query: str, **params) -> Any:
        """并发工具包装器函数"""
        adapter = UniversalAsyncAdapter()
        await adapter.initialize()
        
        # 为每个工具创建任务
        task_definitions = []
        for i, tool in enumerate(tools):
            # 确定调用函数
            if isinstance(tool, BaseTool):
                task_func = tool._run if hasattr(tool, '_run') else tool.run
            else:
                task_func = tool
            
            task_def = AsyncTaskDefinition(
                task_func=task_func,
                task_name=f"{tool_name}_{i}",
                task_type=TaskType.IO_BOUND,
                parameters={"query": query, **params}
            )
            task_definitions.append(task_def)
        
        # 执行并发任务
        result = await adapter.run_concurrent_tasks(task_definitions, aggregator)
        
        return result.aggregated_data if result.aggregated_data is not None else result.task_results
    
    return concurrent_tool_wrapper


# 一些常用的聚合函数
class CommonAggregators:
    """常用聚合函数集合"""
    
    @staticmethod
    def merge_text_results(results: List[Any]) -> str:
        """合并文本结果"""
        text_results = []
        for i, result in enumerate(results):
            if isinstance(result, str):
                text_results.append(f"结果 {i+1}:\n{result}")
            else:
                text_results.append(f"结果 {i+1}:\n{str(result)}")
        
        return "\n\n".join(text_results)
    
    @staticmethod
    def merge_list_results(results: List[Any]) -> List[Any]:
        """合并列表结果"""
        merged = []
        for result in results:
            if isinstance(result, list):
                merged.extend(result)
            else:
                merged.append(result)
        return merged
    
    @staticmethod
    def merge_dict_results(results: List[Any]) -> Dict[str, Any]:
        """合并字典结果"""
        merged = {}
        for i, result in enumerate(results):
            if isinstance(result, dict):
                for key, value in result.items():
                    if key in merged:
                        if isinstance(merged[key], list):
                            merged[key].append(value)
                        else:
                            merged[key] = [merged[key], value]
                    else:
                        merged[key] = value
            else:
                merged[f"result_{i}"] = result
        return merged
    
    @staticmethod  
    def select_best_result(results: List[Any]) -> Any:
        """选择最佳结果（基于长度或评分）"""
        if not results:
            return None
        
        # 如果结果有评分属性，选择评分最高的
        scored_results = [r for r in results if hasattr(r, 'score') or hasattr(r, 'relevance_score')]
        if scored_results:
            return max(scored_results, key=lambda x: getattr(x, 'score', 0) or getattr(x, 'relevance_score', 0))
        
        # 否则选择长度最长的文本结果
        text_results = [r for r in results if isinstance(r, str)]
        if text_results:
            return max(text_results, key=len)
        
        # 默认返回第一个结果
        return results[0]


# 全局适配器实例
_global_adapter: Optional[UniversalAsyncAdapter] = None


async def get_global_adapter() -> UniversalAsyncAdapter:
    """获取全局异步适配器"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = UniversalAsyncAdapter(enable_global_engine=True)
        await _global_adapter.initialize()
    return _global_adapter 