"""
工具服务模块
处理工具定义、配置和管理相关的业务逻辑
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.tool import Tool
# 导入核心业务逻辑层
from core.tools import ToolManager
from app.services.resource_permission_service import ResourcePermissionService
from app.repositories.tool_repository import ToolRepository

class ToolService:
    """工具服务类 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化工具服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        # 使用核心业务逻辑层
        self.tool_manager = ToolManager(db)
        self.permission_service = permission_service
    
    async def create_tool(self, tool_data: Dict[str, Any], user_id: str) -> Tool:
        """创建工具
        
        Args:
            tool_data: 工具数据
            user_id: 用户ID
            
        Returns:
            Tool: 创建的工具实例
            
        Raises:
            HTTPException: 如果工具名称已存在或没有权限
        """
        # 使用核心层创建工具
        result = await self.tool_manager.create_tool(
            name=tool_data.get("name"),
            description=tool_data.get("description"),
            tool_type=tool_data.get("tool_type"),
            config=tool_data.get("config", {}),
            category=tool_data.get("category"),
            tags=tool_data.get("tags"),
            is_active=tool_data.get("is_active", True),
            metadata=tool_data.get("metadata")
        )
        
        if not result["success"]:
            if result.get("error_code") == "TOOL_NAME_EXISTS":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "tool", result["data"]["id"], user_id
        )
        
        # 转换为Tool对象以保持兼容性
        return Tool(**result["data"])
    
    async def get_tool(self, tool_id: str, user_id: str) -> Optional[Tool]:
        """获取工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Tool]: 获取的工具实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 使用核心层获取工具
        result = await self.tool_manager.get_tool(tool_id)
        if not result["success"]:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此工具"
            )
        
        # 转换为Tool对象以保持兼容性
        return Tool(**result["data"])
    
    async def get_by_name(self, tool_name: str, user_id: str) -> Optional[Tool]:
        """通过名称获取工具
        
        Args:
            tool_name: 工具名称
            user_id: 用户ID
            
        Returns:
            Optional[Tool]: 获取的工具实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 使用核心层获取工具
        result = await self.tool_manager.get_tool_by_name(tool_name)
        if not result["success"]:
            return None
        
        tool_data = result["data"]
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool_data["id"], user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此工具"
            )
        
        # 转换为Tool对象以保持兼容性
        return Tool(**tool_data)
    
    async def list_tools(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Tool]:
        """获取工具列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Tool]: 工具列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有工具
        if is_admin:
            result = await self.tool_manager.list_tools(skip=skip, limit=limit)
            if result["success"]:
                return [Tool(**tool_data) for tool_data in result["data"]["tools"]]
            return []
        
        # 获取用户有权限的工具
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        tool_permissions = [p for p in user_permissions if p.resource_type == "tool"]
        
        if not tool_permissions:
            return []
        
        # 获取有权限的工具
        tool_ids = [p.resource_id for p in tool_permissions]
        tools = []
        for tool_id in tool_ids:
            result = await self.tool_manager.get_tool(tool_id)
            if result["success"]:
                tools.append(Tool(**result["data"]))
        
        return tools
    
    async def list_tools_by_category(self, category: str, user_id: str) -> List[Tool]:
        """获取指定类别的工具列表
        
        Args:
            category: 工具类别
            user_id: 用户ID
            
        Returns:
            List[Tool]: 工具列表
        """
        # 使用核心层获取指定类别的工具
        result = await self.tool_manager.list_tools(category=category)
        if not result["success"]:
            return []
        
        all_tools = result["data"]["tools"]
        
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        if is_admin:
            return [Tool(**tool_data) for tool_data in all_tools]
        
        # 过滤用户有权限的工具
        filtered_tools = []
        for tool_data in all_tools:
            has_permission = await self.permission_service.check_permission(
                "tool", tool_data["id"], user_id, "read"
            )
            
            if has_permission:
                filtered_tools.append(Tool(**tool_data))
        
        return filtered_tools
    
    async def update_tool(self, tool_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[Tool]:
        """更新工具
        
        Args:
            tool_id: 工具ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[Tool]: 更新后的工具实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 检查工具是否存在
        tool_result = await self.tool_manager.get_tool(tool_id)
        if not tool_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此工具"
            )
        
        # 使用核心层更新工具
        result = await self.tool_manager.update_tool(tool_id, update_data)
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        # 转换为Tool对象以保持兼容性
        return Tool(**result["data"])
    
    async def delete_tool(self, tool_id: str, user_id: str) -> bool:
        """删除工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 获取工具
        tool = await self.tool_manager.get_tool(tool_id)
        if not tool["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此工具"
            )
        
        # 删除工具
        return await self.tool_manager.delete_tool(tool_id)
    
    async def validate_tool_function_def(self, function_def: Dict[str, Any]) -> bool:
        """验证工具函数定义
        
        Args:
            function_def: 函数定义数据
            
        Returns:
            bool: 是否有效
            
        Raises:
            HTTPException: 如果函数定义无效
        """
        # 验证必要字段
        required_fields = ["name", "description", "parameters"]
        for field in required_fields:
            if field not in function_def:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"函数定义缺少必要字段: {field}"
                )
        
        # 验证参数
        parameters = function_def.get("parameters", {})
        if not isinstance(parameters, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parameters字段必须是对象"
            )
        
        # 验证参数属性
        if "properties" not in parameters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="参数必须包含properties字段"
            )
        
        return True
    
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
