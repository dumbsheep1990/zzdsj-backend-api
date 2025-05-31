"""
工具管理器 - 核心业务逻辑
提供智能体工具的核心管理功能
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.tool_repository import ToolRepository
from app.repositories.tool_execution_repository import ToolExecutionRepository

logger = logging.getLogger(__name__)


class ToolManager:
    """工具管理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化工具管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.tool_repository = ToolRepository()
        self.execution_repository = ToolExecutionRepository()
        self._registered_tools = {}  # 注册的工具函数
        
    # ============ 工具注册管理方法 ============
    
    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """注册工具函数
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            parameters: 工具参数定义
            metadata: 工具元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "工具名称不能为空",
                    "error_code": "INVALID_NAME"
                }
            
            if not callable(func):
                return {
                    "success": False,
                    "error": "工具必须是可调用函数",
                    "error_code": "INVALID_FUNCTION"
                }
            
            # 检查工具是否已注册
            if name in self._registered_tools:
                return {
                    "success": False,
                    "error": f"工具 {name} 已经注册",
                    "error_code": "TOOL_EXISTS"
                }
            
            # 注册工具
            tool_info = {
                "name": name,
                "function": func,
                "description": description,
                "parameters": parameters or {},
                "metadata": metadata or {},
                "registered_at": datetime.utcnow()
            }
            
            self._registered_tools[name] = tool_info
            
            logger.info(f"工具注册成功: {name}")
            
            return {
                "success": True,
                "data": {
                    "name": name,
                    "description": description,
                    "parameters": parameters or {},
                    "registered_at": tool_info["registered_at"]
                }
            }
            
        except Exception as e:
            logger.error(f"注册工具失败: {str(e)}")
            return {
                "success": False,
                "error": f"注册工具失败: {str(e)}",
                "error_code": "REGISTER_FAILED"
            }
    
    def unregister_tool(self, name: str) -> Dict[str, Any]:
        """取消注册工具
        
        Args:
            name: 工具名称
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            if name not in self._registered_tools:
                return {
                    "success": False,
                    "error": f"工具 {name} 未注册",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            del self._registered_tools[name]
            
            logger.info(f"工具取消注册成功: {name}")
            
            return {
                "success": True,
                "data": {"unregistered_tool": name}
            }
            
        except Exception as e:
            logger.error(f"取消注册工具失败: {str(e)}")
            return {
                "success": False,
                "error": f"取消注册工具失败: {str(e)}",
                "error_code": "UNREGISTER_FAILED"
            }
    
    def get_registered_tools(self) -> Dict[str, Any]:
        """获取已注册的工具列表
        
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            tool_list = []
            for name, tool_info in self._registered_tools.items():
                tool_data = {
                    "name": name,
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"],
                    "metadata": tool_info["metadata"],
                    "registered_at": tool_info["registered_at"]
                }
                tool_list.append(tool_data)
            
            return {
                "success": True,
                "data": {
                    "tools": tool_list,
                    "total": len(tool_list)
                }
            }
            
        except Exception as e:
            logger.error(f"获取注册工具列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取注册工具列表失败: {str(e)}",
                "error_code": "GET_TOOLS_FAILED"
            }
    
    # ============ 工具定义管理方法 ============
    
    async def create_tool_definition(
        self,
        name: str,
        description: str = "",
        tool_type: str = "function",
        config: Dict[str, Any] = None,
        parameters: Dict[str, Any] = None,
        is_active: bool = True,
        user_id: str = None
    ) -> Dict[str, Any]:
        """创建工具定义
        
        Args:
            name: 工具名称
            description: 工具描述
            tool_type: 工具类型
            config: 工具配置
            parameters: 工具参数
            is_active: 是否激活
            user_id: 创建者ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证输入
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "工具名称不能为空",
                    "error_code": "INVALID_NAME"
                }
            
            # 检查名称是否已存在
            existing_tool = await self.tool_repository.get_by_name(name.strip(), self.db)
            if existing_tool:
                return {
                    "success": False,
                    "error": "工具名称已存在",
                    "error_code": "NAME_EXISTS"
                }
            
            # 准备工具定义数据
            tool_data = {
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "description": description.strip() if description else "",
                "tool_type": tool_type,
                "config": config or {},
                "parameters": parameters or {},
                "is_active": is_active,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # 创建工具定义
            tool = await self.tool_repository.create(tool_data, self.db)
            
            logger.info(f"工具定义创建成功: {tool.id} - {tool.name}")
            
            return {
                "success": True,
                "data": {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "config": tool.config,
                    "parameters": tool.parameters,
                    "is_active": tool.is_active,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建工具定义失败: {str(e)}")
            return {
                "success": False,
                "error": f"创建工具定义失败: {str(e)}",
                "error_code": "CREATE_FAILED"
            }
    
    async def get_tool_definition(self, tool_id: str) -> Dict[str, Any]:
        """获取工具定义详情
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            tool = await self.tool_repository.get_by_id(tool_id, self.db)
            if not tool:
                return {
                    "success": False,
                    "error": "工具定义不存在",
                    "error_code": "TOOL_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "config": tool.config,
                    "parameters": tool.parameters,
                    "is_active": tool.is_active,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具定义失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具定义失败: {str(e)}",
                "error_code": "GET_FAILED"
            }
    
    async def list_tool_definitions(
        self,
        tool_type: str = None,
        is_active: bool = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取工具定义列表
        
        Args:
            tool_type: 工具类型过滤
            is_active: 活跃状态过滤
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if tool_type:
                filters["tool_type"] = tool_type
            if is_active is not None:
                filters["is_active"] = is_active
            
            # 获取工具定义列表
            tools = await self.tool_repository.list_with_filters(filters, skip, limit, self.db)
            
            # 转换为标准格式
            tool_list = []
            for tool in tools:
                tool_data = {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "is_active": tool.is_active,
                    "created_at": tool.created_at,
                    "updated_at": tool.updated_at
                }
                tool_list.append(tool_data)
            
            return {
                "success": True,
                "data": {
                    "tools": tool_list,
                    "total": len(tool_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具定义列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具定义列表失败: {str(e)}",
                "error_code": "LIST_FAILED"
            }
    
    # ============ 工具执行方法 ============
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        agent_id: str = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """执行工具
        
        Args:
            tool_name: 工具名称
            parameters: 执行参数
            context: 执行上下文
            agent_id: 智能体ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # 检查工具是否注册
            if tool_name not in self._registered_tools:
                return {
                    "success": False,
                    "error": f"工具 {tool_name} 未注册",
                    "error_code": "TOOL_NOT_REGISTERED",
                    "execution_id": execution_id
                }
            
            tool_info = self._registered_tools[tool_name]
            
            # 记录执行开始
            execution_data = {
                "id": execution_id,
                "tool_name": tool_name,
                "parameters": parameters or {},
                "context": context or {},
                "agent_id": agent_id,
                "user_id": user_id,
                "status": "running",
                "started_at": start_time,
                "result": {},
                "error_message": None
            }
            
            await self.execution_repository.create(execution_data, self.db)
            
            # 执行工具函数
            try:
                if parameters:
                    result = await tool_info["function"](**parameters)
                else:
                    result = await tool_info["function"]()
                
                # 记录执行成功
                end_time = datetime.utcnow()
                update_data = {
                    "status": "completed",
                    "result": result if isinstance(result, dict) else {"output": result},
                    "completed_at": end_time,
                    "duration": (end_time - start_time).total_seconds()
                }
                
                await self.execution_repository.update(execution_id, update_data, self.db)
                
                logger.info(f"工具执行成功: {tool_name} - {execution_id}")
                
                return {
                    "success": True,
                    "data": {
                        "execution_id": execution_id,
                        "tool_name": tool_name,
                        "result": update_data["result"],
                        "duration": update_data["duration"],
                        "status": "completed"
                    }
                }
                
            except Exception as exec_error:
                # 记录执行失败
                end_time = datetime.utcnow()
                error_data = {
                    "status": "failed",
                    "error_message": str(exec_error),
                    "completed_at": end_time,
                    "duration": (end_time - start_time).total_seconds()
                }
                
                await self.execution_repository.update(execution_id, error_data, self.db)
                
                logger.error(f"工具执行失败: {tool_name} - {str(exec_error)}")
                
                return {
                    "success": False,
                    "error": f"工具执行失败: {str(exec_error)}",
                    "error_code": "EXECUTION_FAILED",
                    "execution_id": execution_id,
                    "duration": error_data["duration"]
                }
            
        except Exception as e:
            logger.error(f"工具执行系统错误: {str(e)}")
            return {
                "success": False,
                "error": f"工具执行系统错误: {str(e)}",
                "error_code": "SYSTEM_ERROR",
                "execution_id": execution_id
            }
    
    async def get_execution_history(
        self,
        tool_name: str = None,
        agent_id: str = None,
        user_id: str = None,
        status: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取工具执行历史
        
        Args:
            tool_name: 工具名称过滤
            agent_id: 智能体ID过滤
            user_id: 用户ID过滤
            status: 状态过滤
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if tool_name:
                filters["tool_name"] = tool_name
            if agent_id:
                filters["agent_id"] = agent_id
            if user_id:
                filters["user_id"] = user_id
            if status:
                filters["status"] = status
            
            # 获取执行历史
            executions = await self.execution_repository.list_with_filters(
                filters, skip, limit, self.db
            )
            
            # 转换为标准格式
            execution_list = []
            for execution in executions:
                execution_data = {
                    "id": execution.id,
                    "tool_name": execution.tool_name,
                    "status": execution.status,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "duration": execution.duration,
                    "agent_id": execution.agent_id,
                    "user_id": execution.user_id
                }
                
                # 添加结果或错误信息（简化版）
                if execution.status == "completed":
                    execution_data["result_summary"] = str(execution.result)[:100] + "..." if len(str(execution.result)) > 100 else str(execution.result)
                elif execution.status == "failed":
                    execution_data["error_message"] = execution.error_message
                
                execution_list.append(execution_data)
            
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
            logger.error(f"获取工具执行历史失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具执行历史失败: {str(e)}",
                "error_code": "GET_HISTORY_FAILED"
            }
    
    async def get_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """获取工具执行详情
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            execution = await self.execution_repository.get_by_id(execution_id, self.db)
            if not execution:
                return {
                    "success": False,
                    "error": "执行记录不存在",
                    "error_code": "EXECUTION_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": execution.id,
                    "tool_name": execution.tool_name,
                    "parameters": execution.parameters,
                    "context": execution.context,
                    "status": execution.status,
                    "result": execution.result,
                    "error_message": execution.error_message,
                    "started_at": execution.started_at,
                    "completed_at": execution.completed_at,
                    "duration": execution.duration,
                    "agent_id": execution.agent_id,
                    "user_id": execution.user_id
                }
            }
            
        except Exception as e:
            logger.error(f"获取工具执行详情失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取工具执行详情失败: {str(e)}",
                "error_code": "GET_DETAILS_FAILED"
            }
    
    # ============ 工具验证方法 ============
    
    def validate_tool_parameters(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证工具参数
        
        Args:
            tool_name: 工具名称
            parameters: 参数
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 检查工具是否注册
            if tool_name not in self._registered_tools:
                return {
                    "valid": False,
                    "error": f"工具 {tool_name} 未注册",
                    "error_code": "TOOL_NOT_REGISTERED"
                }
            
            tool_info = self._registered_tools[tool_name]
            tool_parameters = tool_info.get("parameters", {})
            
            # 如果没有定义参数要求，则认为验证通过
            if not tool_parameters:
                return {
                    "valid": True,
                    "message": "参数验证通过（无参数要求）"
                }
            
            # 检查必需参数
            required_params = tool_parameters.get("required", [])
            missing_params = []
            
            for param in required_params:
                if param not in parameters:
                    missing_params.append(param)
            
            if missing_params:
                return {
                    "valid": False,
                    "error": f"缺少必需参数: {', '.join(missing_params)}",
                    "error_code": "MISSING_PARAMETERS"
                }
            
            # 检查参数类型（简单实现）
            properties = tool_parameters.get("properties", {})
            type_errors = []
            
            for param_name, param_value in parameters.items():
                if param_name in properties:
                    expected_type = properties[param_name].get("type")
                    if expected_type:
                        if expected_type == "string" and not isinstance(param_value, str):
                            type_errors.append(f"{param_name} 应为字符串类型")
                        elif expected_type == "integer" and not isinstance(param_value, int):
                            type_errors.append(f"{param_name} 应为整数类型")
                        elif expected_type == "number" and not isinstance(param_value, (int, float)):
                            type_errors.append(f"{param_name} 应为数字类型")
                        elif expected_type == "boolean" and not isinstance(param_value, bool):
                            type_errors.append(f"{param_name} 应为布尔类型")
            
            if type_errors:
                return {
                    "valid": False,
                    "error": f"参数类型错误: {'; '.join(type_errors)}",
                    "error_code": "INVALID_PARAMETER_TYPES"
                }
            
            return {
                "valid": True,
                "message": "参数验证通过"
            }
            
        except Exception as e:
            logger.error(f"验证工具参数失败: {str(e)}")
            return {
                "valid": False,
                "error": f"验证工具参数失败: {str(e)}",
                "error_code": "VALIDATION_ERROR"
            } 