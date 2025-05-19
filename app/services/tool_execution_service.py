"""
工具执行服务模块
处理工具调用和执行记录相关的业务逻辑
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.tool_execution import ToolExecution
from app.repositories.tool_execution_repository import ToolExecutionRepository
from app.services.tool_service import ToolService
from app.services.resource_permission_service import ResourcePermissionService

class ToolExecutionService:
    """工具执行服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 tool_service: ToolService = Depends(),
                 permission_service: ResourcePermissionService = Depends()):
        """初始化工具执行服务
        
        Args:
            db: 数据库会话
            tool_service: 工具服务
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = ToolExecutionRepository()
        self.tool_service = tool_service
        self.permission_service = permission_service
    
    async def execute_tool(self, tool_id: str, input_params: Dict[str, Any], 
                        user_id: str, agent_run_id: Optional[str] = None) -> Dict[str, Any]:
        """执行工具
        
        Args:
            tool_id: 工具ID
            input_params: 输入参数
            user_id: 用户ID
            agent_run_id: 智能体运行ID (可选)
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 获取工具
        tool = await self.tool_service.get_tool(tool_id, user_id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool_id, user_id, "use"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限使用此工具"
            )
        
        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution_data = {
            "id": execution_id,
            "tool_id": tool_id,
            "input_params": input_params,
            "user_id": user_id,
            "agent_run_id": agent_run_id,
            "status": "running"
        }
        
        await self.repository.create(execution_data, self.db)
        
        # 执行工具
        start_time = time.time()
        try:
            # 这里需要根据工具的实现类型进行实际调用
            # 例如: 内置工具、Shell命令、API调用、Python函数等
            result = await self._invoke_tool(tool, input_params)
            
            execution_time = int((time.time() - start_time) * 1000)  # 毫秒
            
            # 更新执行记录
            await self.repository.mark_complete(
                execution_id, result, execution_time, self.db
            )
            
            return {
                "execution_id": execution_id,
                "status": "success",
                "result": result,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)  # 毫秒
            
            # 更新执行记录
            await self.repository.mark_failed(
                execution_id, str(e), execution_time, self.db
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"工具执行失败: {str(e)}"
            )
    
    async def _invoke_tool(self, tool: Any, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """实际调用工具
        
        Args:
            tool: 工具实例
            input_params: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 这里是工具执行的核心逻辑，需要根据工具类型进行分发
        # 以下是简化示例
        
        impl_type = tool.implementation_type
        
        if impl_type == "python_function":
            # 使用Python函数执行
            return await self._execute_python_function(tool, input_params)
            
        elif impl_type == "http_api":
            # 调用HTTP API
            return await self._execute_http_api(tool, input_params)
            
        elif impl_type == "shell_command":
            # 执行Shell命令
            return await self._execute_shell_command(tool, input_params)
            
        elif impl_type == "llamaindex_tool":
            # 使用LlamaIndex工具
            return await self._execute_llamaindex_tool(tool, input_params)
            
        else:
            raise ValueError(f"不支持的工具实现类型: {impl_type}")
    
    async def _execute_python_function(self, tool: Any, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Python函数
        
        Args:
            tool: 工具实例
            input_params: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 这里应该实现动态导入和执行Python函数的逻辑
        # 简化示例
        return {"result": "Python函数执行成功", "details": "具体实现需要动态导入和执行"}
    
    async def _execute_http_api(self, tool: Any, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """调用HTTP API
        
        Args:
            tool: 工具实例
            input_params: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 这里应该实现HTTP请求的逻辑
        # 简化示例
        return {"result": "HTTP API调用成功", "details": "具体实现需要发送HTTP请求"}
    
    async def _execute_shell_command(self, tool: Any, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Shell命令
        
        Args:
            tool: 工具实例
            input_params: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 这里应该实现Shell命令执行的逻辑
        # 简化示例
        return {"result": "Shell命令执行成功", "details": "具体实现需要执行系统命令"}
    
    async def _execute_llamaindex_tool(self, tool: Any, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """使用LlamaIndex工具
        
        Args:
            tool: 工具实例
            input_params: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 这里应该实现LlamaIndex工具调用的逻辑
        # 简化示例
        return {"result": "LlamaIndex工具调用成功", "details": "具体实现需要调用LlamaIndex库"}
    
    async def get_execution(self, execution_id: str, user_id: str) -> Optional[ToolExecution]:
        """获取工具执行记录
        
        Args:
            execution_id: 执行记录ID
            user_id: 用户ID
            
        Returns:
            Optional[ToolExecution]: 获取的执行记录实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取执行记录
        execution = await self.repository.get_by_id(execution_id, self.db)
        if not execution:
            return None
        
        # 检查权限
        if execution.user_id != user_id and not await self._check_admin_permission(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此执行记录"
            )
        
        return execution
    
    async def list_executions_by_tool(self, tool_id: str, user_id: str, skip: int = 0, limit: int = 100) -> List[ToolExecution]:
        """获取指定工具的执行记录列表
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[ToolExecution]: 执行记录列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此工具的执行记录"
            )
        
        # 获取执行记录列表
        return await self.repository.list_by_tool_id(tool_id, skip, limit, self.db)
    
    async def list_executions_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[ToolExecution]:
        """获取指定用户的执行记录列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[ToolExecution]: 执行记录列表
        """
        # 获取执行记录列表
        return await self.repository.list_by_user_id(user_id, skip, limit, self.db)
    
    async def list_executions_by_agent_run(self, agent_run_id: str, user_id: str) -> List[ToolExecution]:
        """获取指定智能体运行的执行记录列表
        
        Args:
            agent_run_id: 智能体运行ID
            user_id: 用户ID
            
        Returns:
            List[ToolExecution]: 执行记录列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取执行记录列表
        executions = await self.repository.list_by_agent_run_id(agent_run_id, self.db)
        
        # 检查权限
        if not executions:
            return []
        
        # 检查当前用户是否为记录的创建者或管理员
        sample_execution = executions[0]
        if sample_execution.user_id != user_id and not await self._check_admin_permission(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此智能体运行的执行记录"
            )
        
        return executions
    
    async def delete_execution(self, execution_id: str, user_id: str) -> bool:
        """删除工具执行记录
        
        Args:
            execution_id: 执行记录ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或执行记录不存在
        """
        # 获取执行记录
        execution = await self.repository.get_by_id(execution_id, self.db)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="执行记录不存在"
            )
        
        # 检查权限
        if execution.user_id != user_id and not await self._check_admin_permission(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此执行记录"
            )
        
        # 删除执行记录
        return await self.repository.delete(execution_id, self.db)
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        user = await user_service.get_by_id(user_id)
        return user and user.role == "admin"
