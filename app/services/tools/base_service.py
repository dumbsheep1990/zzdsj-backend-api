"""
基础工具服务模块
为所有工具服务提供通用的基础功能
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from typing import List, Dict, Any, Optional, Type
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

# 导入核心业务逻辑层
from core.tools import ToolManager
from app.services.resource_permission_service import ResourcePermissionService
from app.repositories.tool_repository import ToolRepository

class BaseToolService:
    """基础工具服务类，为所有工具服务提供通用功能 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session,
                 permission_service: Optional[ResourcePermissionService] = None):
        """初始化基础工具服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务(可选)
        """
        self.db = db
        # 使用核心业务逻辑层
        self.tool_manager = ToolManager(db)
        self.permission_service = permission_service
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否具有管理员权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否具有管理员权限
        """
        if not self.permission_service:
            return False
            
        return await self.permission_service.is_admin(user_id)
    
    async def create_tool(self, tool_data: Dict[str, Any], user_id: str) -> Any:
        """创建工具（基础实现）
        
        Args:
            tool_data: 工具数据
            user_id: 用户ID
            
        Returns:
            Any: 创建的工具实例
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 为系统工具检查管理员权限
        is_system = tool_data.get("is_system", False)
        if is_system:
            is_admin = await self._check_admin_permission(user_id)
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有管理员可以创建系统工具"
                )
        
        # 使用核心层创建工具
        result = await self.tool_manager.create_tool(
            name=tool_data.get("name"),
            description=tool_data.get("description"),
            tool_type=tool_data.get("tool_type", "standard"),
            config=tool_data.get("config", {}),
            category=tool_data.get("category"),
            tags=tool_data.get("tags"),
            is_active=tool_data.get("is_active", True),
            metadata={
                **tool_data.get("metadata", {}),
                "creator_id": user_id,
                "is_system": is_system
            }
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result["data"]
    
    async def get_tool(self, tool_id: str, user_id: str) -> Optional[Any]:
        """获取工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 获取的工具实例或None
        """
        result = await self.tool_manager.get_tool(tool_id)
        if result["success"]:
            return result["data"]
        return None
    
    async def list_tools(self, skip: int = 0, limit: int = 100, 
                         filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """列出工具
        
        Args:
            skip: 跳过数量
            limit: 限制数量
            filters: 过滤条件
            
        Returns:
            List[Any]: 工具列表
        """
        # 将filters转换为核心层支持的参数
        kwargs = {"skip": skip, "limit": limit}
        
        if filters:
            if "category" in filters:
                kwargs["category"] = filters["category"]
            if "tool_type" in filters:
                kwargs["tool_type"] = filters["tool_type"]
            if "is_active" in filters:
                kwargs["is_active"] = filters["is_active"]
        
        result = await self.tool_manager.list_tools(**kwargs)
        if result["success"]:
            return result["data"]["tools"]
        return []
    
    async def update_tool(self, 
                          tool_id: str, 
                          update_data: Dict[str, Any], 
                          user_id: str) -> Optional[Any]:
        """更新工具
        
        Args:
            tool_id: 工具ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 更新后的工具实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 获取工具以检查权限
        tool_result = await self.tool_manager.get_tool(tool_id)
        if not tool_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具 ID '{tool_id}' 不存在"
            )
        
        tool_data = tool_result["data"]
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        metadata = tool_data.get("metadata", {})
        is_creator = metadata.get("creator_id") == user_id
        
        if not (is_admin or is_creator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员或创建者可以更新此工具"
            )
        
        # 使用核心层更新工具
        result = await self.tool_manager.update_tool(tool_id, update_data)
        if result["success"]:
            return result["data"]
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
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
        # 获取工具以检查权限
        tool_result = await self.tool_manager.get_tool(tool_id)
        if not tool_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具 ID '{tool_id}' 不存在"
            )
        
        tool_data = tool_result["data"]
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        metadata = tool_data.get("metadata", {})
        is_creator = metadata.get("creator_id") == user_id
        
        if not (is_admin or is_creator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员或创建者可以删除此工具"
            )
        
        # 使用核心层删除工具
        result = await self.tool_manager.delete_tool(tool_id)
        return result.get("success", False)
    
    async def enable_tool(self, tool_id: str, user_id: str) -> Optional[Any]:
        """启用工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 更新后的工具实例或None
        """
        update_data = {"is_active": True}
        return await self.update_tool(tool_id, update_data, user_id)
    
    async def disable_tool(self, tool_id: str, user_id: str) -> Optional[Any]:
        """禁用工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 更新后的工具实例或None
        """
        update_data = {"is_active": False}
        return await self.update_tool(tool_id, update_data, user_id)
