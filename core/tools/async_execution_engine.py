"""
异步执行引擎
提供统一的异步并发执行能力，支持多任务并发、结果汇总和重排
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from enum import Enum
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举"""
    IO_BOUND = "io_bound"          # IO密集型任务
    CPU_BOUND = "cpu_bound"        # CPU密集型任务
    MIXED = "mixed"                # 混合型任务


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"            # 等待执行
    RUNNING = "running"            # 正在执行
    COMPLETED = "completed"        # 执行完成
    FAILED = "failed"              # 执行失败
    TIMEOUT = "timeout"            # 执行超时
    CANCELLED = "cancelled"        # 已取消


@dataclass
class ExecutionConfig:
    """执行配置"""
    max_concurrent_tasks: int = 10         # 最大并发任务数
    timeout_seconds: int = 30              # 任务超时时间
    retry_attempts: int = 3                # 重试次数
    retry_delay: float = 1.0               # 重试延迟
    enable_connection_pool: bool = True     # 启用连接池
    pool_size: int = 100                   # 连接池大小
    enable_rate_limiting: bool = True       # 启用速率限制
    rate_limit_per_second: int = 10        # 每秒请求数限制
    enable_result_dedup: bool = True        # 启用结果去重
    enable_result_ranking: bool = True      # 启用结果重排


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResult:
    """聚合结果"""
    task_results: List[TaskResult]
    aggregated_data: Any
    total_execution_time: float
    success_count: int
    failure_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class AsyncExecutionEngine:
    """异步执行引擎"""
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """初始化异步执行引擎"""
        self.config = config or ExecutionConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        self._rate_limiter = asyncio.Semaphore(self.config.rate_limit_per_second)
        self._task_semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)
        self._task_counter = 0
        self._active_tasks: Dict[str, asyncio.Task] = {}
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
    
    async def initialize(self):
        """初始化资源"""
        try:
            # 初始化HTTP会话
            if self.config.enable_connection_pool:
                connector = aiohttp.TCPConnector(
                    limit=self.config.pool_size,
                    limit_per_host=20,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
                timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'ZZDSJ-AsyncEngine/1.0'
                    }
                )
            
            # 初始化线程池
            self.thread_pool = ThreadPoolExecutor(
                max_workers=min(32, (self.config.max_concurrent_tasks or 4) + 4)
            )
            
            logger.info("异步执行引擎初始化完成")
            
        except Exception as e:
            logger.error(f"异步执行引擎初始化失败: {str(e)}")
            raise
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 取消所有活跃任务
            for task in self._active_tasks.values():
                if not task.done():
                    task.cancel()
            
            # 等待任务完成
            if self._active_tasks:
                await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
            
            # 关闭HTTP会话
            if self.session and not self.session.closed:
                await self.session.close()
            
            # 关闭线程池
            if self.thread_pool:
                self.thread_pool.shutdown(wait=True)
            
            logger.info("异步执行引擎资源清理完成")
            
        except Exception as e:
            logger.error(f"异步执行引擎清理失败: {str(e)}")
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        self._task_counter += 1
        return f"task_{self._task_counter}_{int(time.time() * 1000)}"
    
    async def execute_concurrent_tasks(
        self,
        tasks: List[Callable],
        task_type: TaskType = TaskType.IO_BOUND,
        aggregator: Optional[Callable] = None,
        **kwargs
    ) -> AggregatedResult:
        """
        并发执行多个任务
        
        Args:
            tasks: 任务列表
            task_type: 任务类型
            aggregator: 结果聚合函数
            **kwargs: 额外参数
            
        Returns:
            聚合结果
        """
        start_time = time.time()
        task_results = []
        
        try:
            # 创建并发任务
            concurrent_tasks = []
            for i, task in enumerate(tasks):
                task_id = f"{self._generate_task_id()}_{i}"
                concurrent_task = self._execute_single_task(
                    task_id=task_id,
                    task_func=task,
                    task_type=task_type,
                    **kwargs
                )
                concurrent_tasks.append(concurrent_task)
                self._active_tasks[task_id] = asyncio.create_task(concurrent_task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # 处理结果
            for result in results:
                if isinstance(result, TaskResult):
                    task_results.append(result)
                elif isinstance(result, Exception):
                    # 处理异常结果
                    error_result = TaskResult(
                        task_id=self._generate_task_id(),
                        status=TaskStatus.FAILED,
                        error=str(result)
                    )
                    task_results.append(error_result)
            
            # 聚合结果
            aggregated_data = None
            if aggregator and task_results:
                try:
                    successful_results = [
                        r.result for r in task_results 
                        if r.status == TaskStatus.COMPLETED and r.result is not None
                    ]
                    if successful_results:
                        aggregated_data = await self._run_aggregator(aggregator, successful_results)
                except Exception as e:
                    logger.error(f"结果聚合失败: {str(e)}")
            
            # 统计结果
            success_count = len([r for r in task_results if r.status == TaskStatus.COMPLETED])
            failure_count = len(task_results) - success_count
            total_time = time.time() - start_time
            
            return AggregatedResult(
                task_results=task_results,
                aggregated_data=aggregated_data,
                total_execution_time=total_time,
                success_count=success_count,
                failure_count=failure_count,
                metadata={
                    "total_tasks": len(tasks),
                    "task_type": task_type.value,
                    "config": self.config.__dict__
                }
            )
            
        except Exception as e:
            logger.error(f"并发任务执行失败: {str(e)}")
            raise
        finally:
            # 清理活跃任务记录
            for task_id in list(self._active_tasks.keys()):
                if task_id in self._active_tasks and self._active_tasks[task_id].done():
                    del self._active_tasks[task_id]
    
    async def _execute_single_task(
        self,
        task_id: str,
        task_func: Callable,
        task_type: TaskType,
        **kwargs
    ) -> TaskResult:
        """执行单个任务"""
        start_time = time.time()
        retry_count = 0
        
        async with self._task_semaphore:  # 控制并发数
            while retry_count <= self.config.retry_attempts:
                try:
                    # 速率限制
                    if self.config.enable_rate_limiting:
                        async with self._rate_limiter:
                            pass
                    
                    # 根据任务类型执行
                    if task_type == TaskType.IO_BOUND:
                        result = await self._execute_io_task(task_func, **kwargs)
                    elif task_type == TaskType.CPU_BOUND:
                        result = await self._execute_cpu_task(task_func, **kwargs)
                    else:  # MIXED
                        result = await self._execute_mixed_task(task_func, **kwargs)
                    
                    execution_time = time.time() - start_time
                    
                    return TaskResult(
                        task_id=task_id,
                        status=TaskStatus.COMPLETED,
                        result=result,
                        execution_time=execution_time,
                        retry_count=retry_count
                    )
                    
                except asyncio.TimeoutError:
                    retry_count += 1
                    if retry_count > self.config.retry_attempts:
                        return TaskResult(
                            task_id=task_id,
                            status=TaskStatus.TIMEOUT,
                            error="任务执行超时",
                            execution_time=time.time() - start_time,
                            retry_count=retry_count
                        )
                    await asyncio.sleep(self.config.retry_delay * retry_count)
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count > self.config.retry_attempts:
                        return TaskResult(
                            task_id=task_id,
                            status=TaskStatus.FAILED,
                            error=str(e),
                            execution_time=time.time() - start_time,
                            retry_count=retry_count
                        )
                    await asyncio.sleep(self.config.retry_delay * retry_count)
    
    async def _execute_io_task(self, task_func: Callable, **kwargs) -> Any:
        """执行IO密集型任务"""
        if asyncio.iscoroutinefunction(task_func):
            return await task_func(**kwargs)
        else:
            # 将同步函数包装为异步
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: task_func(**kwargs))
    
    async def _execute_cpu_task(self, task_func: Callable, **kwargs) -> Any:
        """执行CPU密集型任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, lambda: task_func(**kwargs))
    
    async def _execute_mixed_task(self, task_func: Callable, **kwargs) -> Any:
        """执行混合型任务"""
        if asyncio.iscoroutinefunction(task_func):
            return await task_func(**kwargs)
        else:
            return await self._execute_cpu_task(task_func, **kwargs)
    
    async def _run_aggregator(self, aggregator: Callable, results: List[Any]) -> Any:
        """运行结果聚合器"""
        if asyncio.iscoroutinefunction(aggregator):
            return await aggregator(results)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: aggregator(results))


class ResultAggregator:
    """结果聚合器"""
    
    @staticmethod
    def merge_and_rank(
        results: List[Any],
        ranking_func: Optional[Callable] = None,
        dedup_func: Optional[Callable] = None,
        max_results: int = 50
    ) -> List[Any]:
        """合并并重排结果"""
        try:
            merged_results = []
            
            # 展平结果列表
            for result in results:
                if isinstance(result, list):
                    merged_results.extend(result)
                else:
                    merged_results.append(result)
            
            # 去重
            if dedup_func:
                merged_results = dedup_func(merged_results)
            else:
                # 默认去重逻辑
                seen = set()
                unique_results = []
                for item in merged_results:
                    item_key = str(item) if not hasattr(item, 'url') else getattr(item, 'url')
                    if item_key not in seen:
                        seen.add(item_key)
                        unique_results.append(item)
                merged_results = unique_results
            
            # 重排
            if ranking_func:
                merged_results.sort(key=ranking_func, reverse=True)
            
            # 限制结果数量
            return merged_results[:max_results]
            
        except Exception as e:
            logger.error(f"结果合并和重排失败: {str(e)}")
            return results[:max_results] if results else []


# 全局异步执行引擎实例
_global_engine: Optional[AsyncExecutionEngine] = None


async def get_global_engine() -> AsyncExecutionEngine:
    """获取全局异步执行引擎"""
    global _global_engine
    if _global_engine is None:
        _global_engine = AsyncExecutionEngine()
        await _global_engine.initialize()
    return _global_engine


async def cleanup_global_engine():
    """清理全局异步执行引擎"""
    global _global_engine
    if _global_engine:
        await _global_engine.cleanup()
        _global_engine = None 