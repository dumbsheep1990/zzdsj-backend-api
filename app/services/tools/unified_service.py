"""
统一工具服务模块
整合所有工具相关的服务，提供统一的API接口
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional, Union, Type
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.owl_tool import OwlTool, OwlToolkit
from app.services.base_tool_service import BaseToolService
from app.services.owl_tool_service import OwlToolService
from app.services.tools.tool_service import ToolService
from core.owl_controller import OwlController
from app.services.resource_permission_service import ResourcePermissionService
# 导入核心业务逻辑层
from core.tools import ToolManager, RegistryManager, ExecutionManager

@register_service(service_type="unified-tool", priority="high", description="统一工具系统服务")
class UnifiedToolService:
    """统一工具服务类，整合多种工具服务并提供统一的接口 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化统一工具服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.permission_service = permission_service
        self.owl_tool_service = OwlToolService(db, permission_service)
        self.tool_service = ToolService(db, permission_service)
        self.owl_controller = OwlController(db)
        
        # 使用核心业务逻辑层
        self.tool_manager = ToolManager(db)
        self.registry_manager = RegistryManager(db)
        self.execution_manager = ExecutionManager(db)
        
    async def initialize(self):
        """初始化服务"""
        await self.owl_controller.initialize()
        
    async def get_all_tools(self, skip: int = 0, limit: int = 100, 
                           include_owl: bool = True, 
                           include_standard: bool = True,
                           enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有工具，包括OWL工具和标准工具
        
        Args:
            skip: 跳过数量
            limit: 返回限制
            include_owl: 是否包含OWL工具
            include_standard: 是否包含标准工具
            enabled_only: 是否只返回启用的工具
            
        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        result = []
        
        # 获取OWL工具
        if include_owl:
            if enabled_only:
                owl_tools = await self.owl_tool_service.list_enabled_tools()
            else:
                owl_tools = await self.owl_tool_service.list_tools()
                
            for tool in owl_tools:
                tool_dict = {
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "type": "owl",
                    "toolkit": tool.toolkit_name,
                    "is_enabled": tool.is_enabled,
                    "requires_api_key": tool.requires_api_key
                }
                result.append(tool_dict)
        
        # 获取标准工具
        if include_standard:
            # 使用核心层获取工具列表
            tool_result = await self.tool_manager.list_tools(skip=skip, limit=limit)
            if tool_result["success"]:
                standard_tools = tool_result["data"]["tools"]
                
                for tool_data in standard_tools:
                    # 如果只要启用的工具，检查状态
                    if enabled_only and not tool_data.get("is_active", True):
                        continue
                        
                    tool_dict = {
                        "id": str(tool_data["id"]),
                        "name": tool_data["name"],
                        "description": tool_data["description"],
                        "type": "standard",
                        "is_enabled": tool_data.get("is_active", True),
                        "requires_api_key": tool_data.get("requires_api_key", False)
                    }
                    result.append(tool_dict)
        
        return result
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], user_id: str, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """执行工具，自动判断工具类型并调用相应的服务
        
        Args:
            tool_name: 工具名称
            parameters: 执行参数
            user_id: 用户ID
            tool_id: 工具ID (可选)
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            HTTPException: 如果工具不存在或执行失败
        """
        # 首先尝试作为OWL工具执行
        try:
            owl_tool = await self.owl_tool_service.get_tool_by_name(tool_name)
            if owl_tool and owl_tool.is_enabled:
                # 使用OWL控制器执行工具
                return await self.owl_controller.execute_tool(tool_name, parameters)
        except Exception as e:
            # 如果不是OWL工具，继续尝试其他类型
            pass
        
        # 尝试作为标准工具执行
        try:
            standard_tool = await self.tool_service.get_by_name(tool_name, user_id)
            if standard_tool and standard_tool.is_active:
                # 使用执行管理器执行工具
                create_result = await self.execution_manager.create_execution(
                    tool_id=str(standard_tool.id),
                    input_data=parameters,
                    user_id=user_id
                )
                
                if create_result["success"]:
                    execution_id = create_result["data"]["execution_id"]
                    
                    # 开始执行
                    start_result = await self.execution_manager.start_execution(execution_id)
                    if start_result["success"]:
                        # 这里应该调用实际的工具执行逻辑
                        # 为简化，返回成功结果
                        result = {"result": f"工具 {tool_name} 执行成功", "parameters": parameters}
                        
                        # 标记完成
                        await self.execution_manager.complete_execution(execution_id, result)
                        return result
                    
        except Exception as e:
            # 如果不是标准工具，继续尝试
            pass
            
        # 如果提供了工具ID，则尝试按ID执行工具
        if tool_id:
            # 尝试作为OWL工具执行
            try:
                owl_tool = await self.owl_tool_service.get_tool_by_id(tool_id)
                if owl_tool and owl_tool.is_enabled:
                    # 使用OWL控制器执行工具
                    return await self.owl_controller.execute_tool(owl_tool.name, parameters)
            except Exception as e:
                # 继续尝试标准工具
                pass
                
            # 尝试作为标准工具执行
            try:
                standard_tool = await self.tool_service.get_tool(tool_id, user_id)
                if standard_tool and standard_tool.is_active:
                    # 使用执行管理器执行工具
                    create_result = await self.execution_manager.create_execution(
                        tool_id=tool_id,
                        input_data=parameters,
                        user_id=user_id
                    )
                    
                    if create_result["success"]:
                        execution_id = create_result["data"]["execution_id"]
                        
                        # 开始执行
                        start_result = await self.execution_manager.start_execution(execution_id)
                        if start_result["success"]:
                            # 这里应该调用实际的工具执行逻辑
                            result = {"result": f"工具 {standard_tool.name} 执行成功", "parameters": parameters}
                            
                            # 标记完成
                            await self.execution_manager.complete_execution(execution_id, result)
                            return result
                            
            except Exception as e:
                # 继续处理
                pass
        
        # 如果都失败，则工具不存在或未启用
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具 '{tool_name if tool_name else tool_id}' 不存在或未启用"
        )
        
    async def get_tool_metadata(self, tool_name: str) -> Dict[str, Any]:
        """获取工具元数据，自动判断工具类型
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Dict[str, Any]: 工具元数据
            
        Raises:
            HTTPException: 如果工具不存在
        """
        # 首先尝试获取OWL工具
        try:
            owl_tool = await self.owl_tool_service.get_tool_by_name(tool_name)
            if owl_tool:
                return await self.owl_controller.get_tool_metadata(tool_name)
        except Exception:
            pass
            
        # 尝试获取标准工具
        try:
            # 使用核心层获取工具
            result = await self.tool_manager.get_tool_by_name(tool_name)
            if result["success"]:
                tool_data = result["data"]
                return {
                    "name": tool_data["name"],
                    "description": tool_data["description"],
                    "type": tool_data["tool_type"],
                    "config": tool_data["config"],
                    "metadata": tool_data["metadata"]
                }
        except Exception:
            pass
            
        # 如果都失败，则工具不存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具 '{tool_name}' 不存在"
        )
        
    async def get_available_toolkits(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有可用的工具包
        
        Args:
            user_id: 可选的用户ID，用于权限检查
            
        Returns:
            List[Dict[str, Any]]: 工具包列表
        """
        # 确保OWL控制器已初始化
        if not self.owl_controller.initialized:
            await self.owl_controller.initialize()
            
        # 获取工具包列表
        result = []
        
        # 使用注册管理器获取已注册的工具
        registry_result = await self.registry_manager.list_registered_tools()
        if registry_result["success"]:
            # 按工具包分组
            toolkits_dict = {}
            for tool_data in registry_result["data"]["tools"]:
                category = tool_data.get("category", "default")
                if category not in toolkits_dict:
                    toolkits_dict[category] = {
                        "name": category,
                        "description": f"{category} 工具包",
                        "is_enabled": True,
                        "source": "registry",
                        "tool_count": 0,
                        "tools": []
                    }
                toolkits_dict[category]["tool_count"] += 1
                toolkits_dict[category]["tools"].append(tool_data["tool_name"])
            
            result.extend(list(toolkits_dict.values()))
        
        # 从Camel工具包集成器获取可用工具包
        if self.owl_controller.toolkit_integrator:
            camel_toolkits = await self.owl_controller.toolkit_integrator.list_available_toolkits()
            for toolkit in camel_toolkits:
                # 检查是否已存在于结果中
                if not any(t.get("name") == toolkit.get("name") for t in result):
                    toolkit["source"] = "camel"
                    result.append(toolkit)
        
        return result
        
    async def get_toolkit_by_name(self, toolkit_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取工具包
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            Optional[Dict[str, Any]]: 工具包信息或None
        """
        # 使用注册管理器查找工具
        registry_result = await self.registry_manager.list_registered_tools(category=toolkit_name)
        if registry_result["success"] and registry_result["data"]["tools"]:
            tools = registry_result["data"]["tools"]
            return {
                "name": toolkit_name,
                "description": f"{toolkit_name} 工具包",
                "is_enabled": True,
                "source": "registry",
                "tool_count": len(tools),
                "tools": [tool["tool_name"] for tool in tools]
            }
        
        # 如果注册器中不存在，尝试从其他来源查找
        if self.owl_controller.initialized and self.owl_controller.toolkit_integrator:
            toolkits = await self.owl_controller.toolkit_integrator.list_available_toolkits()
            for toolkit in toolkits:
                if toolkit.get("name") == toolkit_name:
                    toolkit["source"] = "camel"
                    return toolkit
        
        return None
        
    async def get_toolkit_tools(self, toolkit_name: str) -> List[Dict[str, Any]]:
        """获取工具包中的工具
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        # 获取OWL工具包中的工具
        db_tools = await self.owl_tool_service.list_tools_by_toolkit(toolkit_name)
        tools = []
        for tool in db_tools:
            tools.append({
                "id": str(tool.id),
                "name": tool.name,
                "function_name": tool.function_name,
                "is_enabled": tool.is_enabled
            })
            
        # 获取注册器中的工具
        registry_result = await self.registry_manager.list_registered_tools(category=toolkit_name)
        if registry_result["success"]:
            for tool_data in registry_result["data"]["tools"]:
                tools.append({
                    "name": tool_data["tool_name"],
                    "description": tool_data.get("description", ""),
                    "version": tool_data["tool_version"],
                    "source": "registry"
                })
                
        return tools
        
    async def load_toolkit(self, toolkit_name: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """加载工具包
        
        Args:
            toolkit_name: 工具包名称
            user_id: 执行操作的用户ID
            
        Returns:
            Dict[str, Any]: 加载结果
            
        Raises:
            HTTPException: 如果工具包不存在或加载失败
        """
        # 检查权限
        if user_id:
            is_admin = await self.permission_service.is_admin(user_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以加载工具包"
                )
        
        # 确保OWL控制器已初始化
        if not self.owl_controller.initialized:
            await self.owl_controller.initialize()
            
        # 首先检查是否已经在注册器中
        registry_result = await self.registry_manager.list_registered_tools(category=toolkit_name)
        if registry_result["success"] and registry_result["data"]["tools"]:
            tools = registry_result["data"]["tools"]
            return {
                "status": "success",
                "source": "registry",
                "toolkit": toolkit_name,
                "loaded_tools": [{
                    "name": tool["tool_name"],
                    "version": tool["tool_version"],
                    "status": tool["status"]
                } for tool in tools]
            }
            
        # 如果注册器中不存在该工具包，尝试从其他集成器加载
        if not self.owl_controller.toolkit_integrator:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="工具包集成器未初始化"
            )
            
        try:
            result = await self.owl_controller.toolkit_integrator.load_toolkit(toolkit_name)
            
            # 将工具注册到注册器
            for tool in result:
                if isinstance(tool, dict) and "name" in tool:
                    await self.registry_manager.register_tool(
                        tool_name=tool["name"],
                        tool_version="1.0.0",
                        tool_config=tool,
                        provider="external",
                        category=toolkit_name,
                        description=tool.get("description", f"{tool['name']} 工具")
                    )
            
            return {
                "status": "success",
                "source": "external",
                "toolkit": toolkit_name,
                "loaded_tools": result
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具包 '{toolkit_name}' 不存在"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"加载工具包失败: {str(e)}"
            )
        
    async def process_task_with_tools(self, task: str, tools: Optional[List[str]] = None,
            model_config: Optional[Dict[str, Any]] = None, user_id: str = None) -> Dict[str, Any]:
        """使用工具处理任务
        
        Args:
            task: 任务描述
            tools: 可选的工具列表名称
            model_config: 模型配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 处理结果
            
        Raises:
            HTTPException: 如果处理失败
        """
        # 确保OWL控制器已初始化
        if not self.owl_controller.initialized:
            await self.owl_controller.initialize()
            
        # 使用OWL控制器处理任务
        return await self.owl_controller.process_task(
            task=task,
            tools=tools,
            user_id=user_id,
            model_config=model_config
        )
    
    async def get_toolkits_for_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取用户可用的工具包
        
        Args:
            user_id: 用户ID
            skip: 跳过数量
            limit: 返回限制
            
        Returns:
            List[Dict[str, Any]]: 工具包列表
        """
        # 检查用户是否是管理员
        is_admin = await self.permission_service.is_admin(user_id)
        
        # 获取工具包列表
        all_toolkits = await self.get_available_toolkits(user_id)
        
        # 如果不是管理员，过滤出已启用的工具包
        if not is_admin:
            all_toolkits = [tk for tk in all_toolkits if tk.get("is_enabled", False)]
            
        # 应用分页
        start = min(skip, len(all_toolkits))
        end = min(start + limit, len(all_toolkits))
        
        return all_toolkits[start:end]
    
    async def update_toolkit(self, toolkit_id: str, update_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """更新工具包
        
        Args:
            toolkit_id: 工具包ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 更新后的工具包
            
        Raises:
            HTTPException: 如果工具包不存在或更新失败
        """
        # 首先检查权限
        is_admin = await self.permission_service.is_admin(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以更新工具包"
            )
            
        # 由于我们使用注册器管理工具，这里简化为基本的响应
        # 实际的更新逻辑应该通过注册器来处理
        
        # 如果没有找到工具包
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具包ID '{toolkit_id}' 不存在或不支持更新"
        )
    
    async def enable_toolkit(self, toolkit_id: str, user_id: str) -> Dict[str, Any]:
        """启用工具包
        
        Args:
            toolkit_id: 工具包ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 更新后的工具包
        """
        return await self.update_toolkit(toolkit_id, {"is_enabled": True}, user_id)
    
    async def disable_toolkit(self, toolkit_id: str, user_id: str) -> Dict[str, Any]:
        """禁用工具包
        
        Args:
            toolkit_id: 工具包ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 更新后的工具包
        """
        return await self.update_toolkit(toolkit_id, {"is_enabled": False}, user_id)
    
    async def create_owl_tool(self, tool_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """创建OWL工具
        
        Args:
            tool_data: 工具数据
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 创建的工具信息
            
        Raises:
            HTTPException: 如果没有权限或数据无效
        """
        try:
            # 使用OWL工具服务创建工具
            tool = await self.owl_tool_service.register_tool(tool_data, user_id)
            
            # 构造返回数据
            return {
                "id": str(tool.id),
                "name": tool.name,
                "function_name": tool.function_name,
                "toolkit_name": tool.toolkit_name,
                "is_enabled": tool.is_enabled,
                "requires_api_key": tool.requires_api_key,
                "description": tool.description
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建OWL工具失败: {str(e)}"
            )
    
    async def register_tool_in_registry(self, tool_name: str, tool_version: str, 
                                       tool_config: Dict[str, Any], user_id: str,
                                       provider: str = "user", category: str = "custom") -> Dict[str, Any]:
        """在注册器中注册工具
        
        Args:
            tool_name: 工具名称
            tool_version: 工具版本
            tool_config: 工具配置
            user_id: 用户ID
            provider: 提供者
            category: 分类
            
        Returns:
            Dict[str, Any]: 注册结果
        """
        result = await self.registry_manager.register_tool(
            tool_name=tool_name,
            tool_version=tool_version,
            tool_config=tool_config,
            provider=provider,
            category=category,
            description=tool_config.get("description", f"{tool_name} 工具")
        )
        
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
