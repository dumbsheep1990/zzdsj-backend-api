"""
执行协调器
管理工具执行的调度、监控和优化
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

from ..abstractions import ToolExecutionContext, ToolResult, ToolStatus


class ExecutionPriority(int, Enum):
    """执行优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class ExecutionRequest:
    """执行请求"""
    execution_id: str
    tool_name: str
    params: Dict[str, Any]
    context: ToolExecutionContext
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    timeout: Optional[int] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()


class ExecutionCoordinator:
    """执行协调器 - 管理工具执行的调度和监控"""
    
    def __init__(self, max_concurrent_executions: int = 50):
        self._logger = logging.getLogger(__name__)
        
        # 配置
        self.max_concurrent_executions = max_concurrent_executions
        
        # 执行队列和状态
        self._pending_queue: List[ExecutionRequest] = []
        self._running_executions: Dict[str, asyncio.Task] = {}
        self._completed_executions: Dict[str, ToolResult] = {}
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(max_concurrent_executions)
        
        # 统计信息
        self._stats = {
            "total_requests": 0,
            "completed_executions": 0,
            "failed_executions": 0,
            "current_queue_size": 0,
            "current_running_count": 0
        }
        
        # 后台清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """启动执行协调器"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._logger.info("Execution coordinator started")
    
    async def stop(self):
        """停止执行协调器"""
        if not self._running:
            return
        
        self._running = False
        
        # 取消所有正在执行的任务
        for execution_id, task in list(self._running_executions.items()):
            task.cancel()
        
        # 停止清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        self._logger.info("Execution coordinator stopped")
    
    async def submit_execution(self, 
                             tool_name: str,
                             params: Dict[str, Any],
                             context: Optional[ToolExecutionContext] = None,
                             priority: ExecutionPriority = ExecutionPriority.NORMAL,
                             timeout: Optional[int] = None) -> str:
        """提交工具执行请求"""
        
        # 创建执行上下文
        if not context:
            context = ToolExecutionContext()
        
        # 创建执行请求
        request = ExecutionRequest(
            execution_id=context.execution_id,
            tool_name=tool_name,
            params=params,
            context=context,
            priority=priority,
            timeout=timeout
        )
        
        # 添加到队列
        self._pending_queue.append(request)
        self._stats["total_requests"] += 1
        self._stats["current_queue_size"] = len(self._pending_queue)
        
        self._logger.info(f"Submitted execution request {request.execution_id} for tool {tool_name}")
        
        return request.execution_id
    
    def get_execution_result(self, execution_id: str) -> Optional[ToolResult]:
        """获取执行结果"""
        return self._completed_executions.get(execution_id)
    
    def get_execution_status(self, execution_id: str) -> Optional[ToolStatus]:
        """获取执行状态"""
        # 检查是否在运行中
        if execution_id in self._running_executions:
            return ToolStatus.RUNNING
        
        # 检查是否已完成
        result = self._completed_executions.get(execution_id)
        if result:
            return result.status
        
        # 检查是否在队列中
        for request in self._pending_queue:
            if request.execution_id == execution_id:
                return ToolStatus.PENDING
        
        return None
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """获取协调器统计信息"""
        return {
            **self._stats,
            "max_concurrent_executions": self.max_concurrent_executions,
            "is_running": self._running
        }
    
    async def _cleanup_loop(self):
        """清理循环 - 定期清理过期的执行结果"""
        while self._running:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                # 简单的清理逻辑
                cutoff_time = datetime.now() - timedelta(hours=1)
                expired = []
                for execution_id, result in self._completed_executions.items():
                    if result.completed_at and result.completed_at < cutoff_time:
                        expired.append(execution_id)
                
                for execution_id in expired:
                    del self._completed_executions[execution_id]
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Cleanup loop error: {e}") 