"""
统一工具服务模块
整合所有工具相关的服务，提供统一的API接口
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional, Union, Type
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.owl_tool import OwlTool, OwlToolkit
from app.services.base_tool_service import BaseToolService
from app.services.owl_tool_service import OwlToolService
from app.services.tool_service import ToolService
from app.core.owl_controller import OwlController
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="unified-tool", priority="high", description="统一工具系统服务")
class UnifiedToolService:
    """统一工具服务类，整合多种工具服务并提供统一的接口"""
    
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
        
        # 初始化工具包仓库
        self.toolkit_repository = OwlToolkitRepository()
        
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
            filters = {"is_enabled": True} if enabled_only else None
            standard_tools = await self.tool_service.list_tools(skip, limit, filters)
            
            for tool in standard_tools:
                tool_dict = {
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "type": "standard",
                    "is_enabled": tool.is_enabled,
                    "requires_api_key": getattr(tool, "requires_api_key", False)
                }
                result.append(tool_dict)
        
        return result
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], user_id: str, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """执行工具，自动判断工具类型并调用相应的服务
        
        Args:
            tool_name: 工具名称
            parameters: 执行参数
            user_id: 用户ID
            
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
            standard_tool = await self.tool_service.get_tool_by_name(tool_name)
            if standard_tool and standard_tool.is_enabled:
                # 执行标准工具
                return await self.tool_service.execute_tool(tool_name, parameters, user_id)
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
                standard_tool = await self.tool_service.get_tool_by_id(tool_id)
                if standard_tool and standard_tool.is_enabled:
                    return await self.tool_service.execute_tool(str(standard_tool.id), parameters, user_id)
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
            standard_tool = await self.tool_service.get_tool_by_name(tool_name)
            if standard_tool:
                return self.tool_service.get_tool_metadata(standard_tool)
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
        
        # 从数据库获取已注册的工具包
        db_toolkits = await self.toolkit_repository.get_multi(self.db)
        for toolkit in db_toolkits:
            result.append({
                "id": str(toolkit.id),
                "name": toolkit.name,
                "description": toolkit.description,
                "is_enabled": toolkit.is_enabled,
                "source": "database",
                "tool_count": await self._count_tools_in_toolkit(toolkit.name)
            })
        
        # 从Camel工具包集成器获取可用工具包
        if self.owl_controller.toolkit_integrator:
            camel_toolkits = await self.owl_controller.toolkit_integrator.list_available_toolkits()
            for toolkit in camel_toolkits:
                # 检查是否已存在于结果中
                if not any(t.get("name") == toolkit.get("name") for t in result):
                    toolkit["source"] = "camel"
                    result.append(toolkit)
        
        return result
        
    async def _count_tools_in_toolkit(self, toolkit_name: str) -> int:
        """统计工具包中的工具数量
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            int: 工具数量
        """
        tools = await self.owl_tool_service.list_tools_by_toolkit(toolkit_name)
        return len(tools)
        
    async def get_toolkit_by_name(self, toolkit_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取工具包
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            Optional[Dict[str, Any]]: 工具包信息或None
        """
        # 先从数据库查找
        db_toolkit = await self.toolkit_repository.get_by_name(toolkit_name, self.db)
        if db_toolkit:
            tool_count = await self._count_tools_in_toolkit(toolkit_name)
            return {
                "id": str(db_toolkit.id),
                "name": db_toolkit.name,
                "description": db_toolkit.description,
                "is_enabled": db_toolkit.is_enabled,
                "source": "database",
                "tool_count": tool_count,
                "config": db_toolkit.config
            }
        
        # 如果数据库中不存在，尝试从其他来源查找
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
        # 获取数据库中的工具
        db_tools = await self.owl_tool_service.list_tools_by_toolkit(toolkit_name)
        tools = []
        for tool in db_tools:
            tools.append({
                "id": str(tool.id),
                "name": tool.name,
                "function_name": tool.function_name,
                "is_enabled": tool.is_enabled
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
            
        # 首先检查数据库中是否存在该工具包
        db_toolkit = await self.toolkit_repository.get_by_name(toolkit_name, self.db)
        
        # 如果数据库中存在该工具包，则启用它
        if db_toolkit:
            if not db_toolkit.is_enabled:
                db_toolkit = await self.owl_tool_service.enable_toolkit(str(db_toolkit.id), user_id)
            
            # 获取工具包中的工具
            tools = await self.owl_tool_service.list_tools_by_toolkit(toolkit_name)
            
            return {
                "status": "success",
                "source": "database",
                "toolkit": toolkit_name,
                "toolkit_id": str(db_toolkit.id),
                "loaded_tools": [{
                    "id": str(tool.id),
                    "name": tool.name,
                    "function_name": tool.function_name,
                    "is_enabled": tool.is_enabled
                } for tool in tools]
            }
            
        # 如果数据库中不存在该工具包，尝试从其他集成器加载
        if not self.owl_controller.toolkit_integrator:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="工具包集成器未初始化"
            )
            
        try:
            result = await self.owl_controller.toolkit_integrator.load_toolkit(toolkit_name)
            
            # 创建数据库中的工具包记录
            toolkit_data = {
                "name": toolkit_name,
                "description": f"{toolkit_name} 工具包 (从外部源加载)",
                "is_enabled": True,
                "config": {"source": "external"}
            }
            
            # 保存工具包到数据库
            db_toolkit = await self.owl_tool_service.create_toolkit(toolkit_data, user_id)
            
            return {
                "status": "success",
                "source": "external",
                "toolkit": toolkit_name,
                "toolkit_id": str(db_toolkit.id),
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
            
        # 尝试从数据库获取工具包
        try:
            owl_toolkit = await self.toolkit_repository.get(self.db, id=toolkit_id)
            if owl_toolkit:
                # 更新工具包
                for key, value in update_data.items():
                    if hasattr(owl_toolkit, key):
                        setattr(owl_toolkit, key, value)
                        
                # 保存更新
                await self.toolkit_repository.update(self.db, owl_toolkit)
                
                # 返回更新后的工具包
                return {
                    "id": str(owl_toolkit.id),
                    "name": owl_toolkit.name,
                    "description": owl_toolkit.description,
                    "is_enabled": owl_toolkit.is_enabled,
                    "source": "database",
                    "updated_at": owl_toolkit.updated_at.isoformat() if hasattr(owl_toolkit, "updated_at") else None
                }
        except Exception as e:
            # 捕获任何错误，转为HTTP异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新工具包时出错: {str(e)}"
            )
            
        # 如果没有找到工具包
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具包ID '{toolkit_id}' 不存在"
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
    
        result = []
        for tool in db_tools:
            tool_info = {
                "id": str(tool.id),
                "name": tool.name,
                "description": tool.description,
                "function_name": tool.function_name,
                "is_enabled": tool.is_enabled,
                "requires_api_key": tool.requires_api_key,
                "source": "database"
            }
            result.append(tool_info)
        
        return result
        
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
                "description": tool.description,
                "toolkit_name": tool.toolkit_name,
                "function_name": tool.function_name,
                "parameters_schema": tool.parameters_schema,
                "is_enabled": tool.is_enabled,
                "requires_api_key": tool.requires_api_key,
                "source": "database"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建OWL工具失败: {str(e)}"
            )
    
    async def get_owl_tool(self, tool_id: str, user_id: str) -> Dict[str, Any]:
        """获取OWL工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 工具信息
            
        Raises:
            HTTPException: 如果工具不存在
        """
        tool = await self.owl_tool_service.get_tool(tool_id, user_id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具ID '{tool_id}' 不存在"
            )
            
        return {
            "id": str(tool.id),
            "name": tool.name,
            "description": tool.description,
            "toolkit_name": tool.toolkit_name,
            "function_name": tool.function_name,
            "parameters_schema": tool.parameters_schema,
            "is_enabled": tool.is_enabled,
            "requires_api_key": tool.requires_api_key,
            "source": "database"
        }
        
    async def process_task_with_tools(self, task: str, tools: Optional[List[str]], 
            model_config: Optional[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
        """使用工具执行任务
        
        Args:
            task: 任务描述
            tools: 可用工具名称列表
            model_config: 模型配置
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 任务结果
            
        Raises:
            HTTPException: 如果执行失败
        """
        try:
            # 确保OWL控制器已初始化
            if not self.owl_controller.initialized:
                await self.owl_controller.initialize()
                
            # 执行任务
            result = await self.owl_controller.process_task(
                task=task,
                tools=tools,
                user_id=user_id,
                model_config=model_config
            )
            
            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"执行任务失败: {str(e)}"
            )
