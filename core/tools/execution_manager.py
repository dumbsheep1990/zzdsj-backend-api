"""
工具执行管理器
处理工具执行、调度和监控的核心业务逻辑
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime, timedelta
from enum import Enum

from app.repositories.tool_execution_repository import ToolExecutionRepository
from .tool_manager import ToolManager

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionManager:
    """工具执行管理器"""
    
    def __init__(self, db: Session):
        """初始化执行管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.execution_repository = ToolExecutionRepository(db)
        self.tool_manager = ToolManager(db)
    
    async def create_execution(self,
                              tool_id: str,
                              input_data: Dict[str, Any],
                              user_id: Optional[str] = None,
                              context: Optional[Dict[str, Any]] = None,
                              timeout: Optional[int] = None,
                              priority: int = 0) -> Dict[str, Any]:
        """创建工具执行任务
        
        Args:
            tool_id: 工具ID
            input_data: 输入数据
            user_id: 用户ID
            context: 执行上下文
            timeout: 超时时间（秒）
            priority: 优先级
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证工具是否存在且可用
            tool_result = await self.tool_manager.get_tool(tool_id)
            if not tool_result["success"]:
                return tool_result
            
            tool = tool_result["data"]
            if not tool["is_active"]:
                return {
                    "success": False,
                    "error": "工具未激活",
                    "error_code": "TOOL_NOT_ACTIVE"
                }
            
            # 生成执行ID
            execution_id = str(uuid.uuid4())
            
            # 准备执行数据
            execution_data = {
                "execution_id": execution_id,
                "tool_id": tool_id,
                "input_data": input_data,
                "user_id": user_id,
                "context": context or {},
                "status": ExecutionStatus.PENDING.value,
                "priority": priority,
                "timeout": timeout,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 如果设置了超时，计算过期时间
            if timeout:
                execution_data["expires_at"] = datetime.now() + timedelta(seconds=timeout)
            
            # 创建执行记录
            execution = self.execution_repository.create(execution_data)
            
            logger.info(f"已创建工具执行任务: {execution_id} (工具: {tool['name']})")
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution.execution_id,
                    "tool_id": execution.tool_id,
                    "input_data": execution.input_data,
                    "user_id": execution.user_id,
                    "context": execution.context,
                    "status": execution.status,
                    "priority": execution.priority,
                    "timeout": execution.timeout,
                    "created_at": execution.created_at,
                    "updated_at": execution.updated_at,
                    "expires_at": execution.expires_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建工具执行任务时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建执行任务失败: {str(e)}",
                "error_code": "CREATE_EXECUTION_FAILED"
            }
    
    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """获取执行任务详情
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            execution = self.execution_repository.get_by_id(execution_id)
            if not execution:
                return {
                    "success": False,
                    "error": "执行任务不存在",
                    "error_code": "EXECUTION_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution.execution_id,
                    "tool_id": execution.tool_id,
                    "input_data": execution.input_data,
                    "output_data": execution.output_data,
                    "user_id": execution.user_id,
                    "context": execution.context,
                    "status": execution.status,
                    "priority": execution.priority,
                    "timeout": execution.timeout,
                    "error_message": execution.error_message,
                    "created_at": execution.created_at,
                    "updated_at": execution.updated_at,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "expires_at": execution.expires_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取执行任务时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取执行任务失败: {str(e)}",
                "error_code": "GET_EXECUTION_FAILED"
            }
    
    async def start_execution(self, execution_id: str) -> Dict[str, Any]:
        """开始执行任务
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取执行任务
            execution_result = await self.get_execution(execution_id)
            if not execution_result["success"]:
                return execution_result
            
            execution_data = execution_result["data"]
            
            # 检查状态
            if execution_data["status"] != ExecutionStatus.PENDING.value:
                return {
                    "success": False,
                    "error": f"执行任务状态不正确: {execution_data['status']}",
                    "error_code": "INVALID_EXECUTION_STATUS"
                }
            
            # 检查是否已过期
            if execution_data.get("expires_at"):
                expires_at = execution_data["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_at:
                    # 标记为超时
                    await self.update_execution_status(
                        execution_id, 
                        ExecutionStatus.TIMEOUT.value,
                        error_message="执行任务已超时"
                    )
                    return {
                        "success": False,
                        "error": "执行任务已超时",
                        "error_code": "EXECUTION_TIMEOUT"
                    }
            
            # 更新状态为运行中
            update_result = await self.update_execution_status(
                execution_id, 
                ExecutionStatus.RUNNING.value
            )
            
            if not update_result["success"]:
                return update_result
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution_id,
                    "status": ExecutionStatus.RUNNING.value,
                    "started_at": datetime.now()
                }
            }
            
        except Exception as e:
            logger.error(f"开始执行任务时出错: {str(e)}")
            return {
                "success": False,
                "error": f"开始执行任务失败: {str(e)}",
                "error_code": "START_EXECUTION_FAILED"
            }
    
    async def complete_execution(self,
                                execution_id: str,
                                output_data: Dict[str, Any],
                                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """完成执行任务
        
        Args:
            execution_id: 执行ID
            output_data: 输出数据
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 准备更新数据
            update_data = {
                "status": ExecutionStatus.COMPLETED.value,
                "output_data": output_data,
                "completed_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            if metadata:
                update_data["metadata"] = metadata
            
            # 更新执行记录
            execution = self.execution_repository.update(execution_id, update_data)
            if not execution:
                return {
                    "success": False,
                    "error": "更新执行任务失败",
                    "error_code": "UPDATE_EXECUTION_FAILED"
                }
            
            logger.info(f"执行任务已完成: {execution_id}")
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution_id,
                    "status": ExecutionStatus.COMPLETED.value,
                    "output_data": output_data,
                    "completed_at": execution.completed_at
                }
            }
            
        except Exception as e:
            logger.error(f"完成执行任务时出错: {str(e)}")
            return {
                "success": False,
                "error": f"完成执行任务失败: {str(e)}",
                "error_code": "COMPLETE_EXECUTION_FAILED"
            }
    
    async def fail_execution(self,
                            execution_id: str,
                            error_message: str,
                            error_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """标记执行任务失败
        
        Args:
            execution_id: 执行ID
            error_message: 错误消息
            error_details: 错误详情
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 准备更新数据
            update_data = {
                "status": ExecutionStatus.FAILED.value,
                "error_message": error_message,
                "completed_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            if error_details:
                update_data["error_details"] = error_details
            
            # 更新执行记录
            execution = self.execution_repository.update(execution_id, update_data)
            if not execution:
                return {
                    "success": False,
                    "error": "更新执行任务失败",
                    "error_code": "UPDATE_EXECUTION_FAILED"
                }
            
            logger.warning(f"执行任务失败: {execution_id} - {error_message}")
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution_id,
                    "status": ExecutionStatus.FAILED.value,
                    "error_message": error_message,
                    "completed_at": execution.completed_at
                }
            }
            
        except Exception as e:
            logger.error(f"标记执行任务失败时出错: {str(e)}")
            return {
                "success": False,
                "error": f"标记执行任务失败: {str(e)}",
                "error_code": "FAIL_EXECUTION_FAILED"
            }
    
    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """取消执行任务
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 获取执行任务
            execution_result = await self.get_execution(execution_id)
            if not execution_result["success"]:
                return execution_result
            
            execution_data = execution_result["data"]
            
            # 检查是否可以取消
            if execution_data["status"] in [
                ExecutionStatus.COMPLETED.value,
                ExecutionStatus.FAILED.value,
                ExecutionStatus.CANCELLED.value,
                ExecutionStatus.TIMEOUT.value
            ]:
                return {
                    "success": False,
                    "error": f"执行任务无法取消，当前状态: {execution_data['status']}",
                    "error_code": "CANNOT_CANCEL_EXECUTION"
                }
            
            # 更新状态为已取消
            update_result = await self.update_execution_status(
                execution_id,
                ExecutionStatus.CANCELLED.value
            )
            
            if not update_result["success"]:
                return update_result
            
            logger.info(f"执行任务已取消: {execution_id}")
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution_id,
                    "status": ExecutionStatus.CANCELLED.value,
                    "cancelled_at": datetime.now()
                }
            }
            
        except Exception as e:
            logger.error(f"取消执行任务时出错: {str(e)}")
            return {
                "success": False,
                "error": f"取消执行任务失败: {str(e)}",
                "error_code": "CANCEL_EXECUTION_FAILED"
            }
    
    async def update_execution_status(self,
                                     execution_id: str,
                                     status: str,
                                     error_message: Optional[str] = None) -> Dict[str, Any]:
        """更新执行状态
        
        Args:
            execution_id: 执行ID
            status: 新状态
            error_message: 错误消息（可选）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 准备更新数据
            update_data = {
                "status": status,
                "updated_at": datetime.now()
            }
            
            # 根据状态设置相应的时间字段
            if status == ExecutionStatus.RUNNING.value:
                update_data["started_at"] = datetime.now()
            elif status in [
                ExecutionStatus.COMPLETED.value,
                ExecutionStatus.FAILED.value,
                ExecutionStatus.CANCELLED.value,
                ExecutionStatus.TIMEOUT.value
            ]:
                update_data["completed_at"] = datetime.now()
            
            if error_message:
                update_data["error_message"] = error_message
            
            # 更新执行记录
            execution = self.execution_repository.update(execution_id, update_data)
            if not execution:
                return {
                    "success": False,
                    "error": "更新执行状态失败",
                    "error_code": "UPDATE_STATUS_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "execution_id": execution_id,
                    "status": status,
                    "updated_at": execution.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新执行状态时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新执行状态失败: {str(e)}",
                "error_code": "UPDATE_EXECUTION_STATUS_FAILED"
            }
    
    async def list_executions(self,
                             skip: int = 0,
                             limit: int = 100,
                             tool_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             status: Optional[str] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取执行任务列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            tool_id: 工具ID过滤
            user_id: 用户ID过滤
            status: 状态过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if tool_id:
                filters["tool_id"] = tool_id
            if user_id:
                filters["user_id"] = user_id
            if status:
                filters["status"] = status
            if start_date:
                filters["start_date"] = start_date
            if end_date:
                filters["end_date"] = end_date
            
            # 获取执行列表
            executions = self.execution_repository.list_with_filters(
                skip=skip, limit=limit, **filters
            )
            
            # 格式化执行列表
            execution_list = []
            for execution in executions:
                execution_list.append({
                    "execution_id": execution.execution_id,
                    "tool_id": execution.tool_id,
                    "input_data": execution.input_data,
                    "output_data": execution.output_data,
                    "user_id": execution.user_id,
                    "context": execution.context,
                    "status": execution.status,
                    "priority": execution.priority,
                    "timeout": execution.timeout,
                    "error_message": execution.error_message,
                    "created_at": execution.created_at,
                    "updated_at": execution.updated_at,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "expires_at": execution.expires_at
                })
            
            return {
                "success": True,
                "data": {
                    "executions": execution_list,
                    "total": len(execution_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取执行任务列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取执行任务列表失败: {str(e)}",
                "error_code": "LIST_EXECUTIONS_FAILED"
            }
    
    async def get_execution_statistics(self,
                                      tool_id: Optional[str] = None,
                                      user_id: Optional[str] = None,
                                      start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取执行统计信息
        
        Args:
            tool_id: 工具ID过滤
            user_id: 用户ID过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if tool_id:
                filters["tool_id"] = tool_id
            if user_id:
                filters["user_id"] = user_id
            if start_date:
                filters["start_date"] = start_date
            if end_date:
                filters["end_date"] = end_date
            
            # 获取统计数据
            stats = self.execution_repository.get_execution_statistics(**filters)
            
            return {
                "success": True,
                "data": stats
            }
            
        except Exception as e:
            logger.error(f"获取执行统计信息时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取执行统计信息失败: {str(e)}",
                "error_code": "GET_EXECUTION_STATISTICS_FAILED"
            }
    
    async def cleanup_expired_executions(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """清理过期的执行记录
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # 清理过期的已完成执行记录
            cleanup_count = self.execution_repository.cleanup_old_executions(cutoff_time)
            
            logger.info(f"已清理 {cleanup_count} 条过期执行记录")
            
            return {
                "success": True,
                "data": {
                    "cleaned_count": cleanup_count,
                    "cutoff_time": cutoff_time
                }
            }
            
        except Exception as e:
            logger.error(f"清理过期执行记录时出错: {str(e)}")
            return {
                "success": False,
                "error": f"清理过期执行记录失败: {str(e)}",
                "error_code": "CLEANUP_EXECUTIONS_FAILED"
            } 