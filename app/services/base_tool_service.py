"""
基础工具服务模块
为所有工具服务提供通用的基础功能
"""

from typing import List, Dict, Any, Optional, Type
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.base_repository import BaseRepository
from app.services.resource_permission_service import ResourcePermissionService

class BaseToolService:
    """基础工具服务类，为所有工具服务提供通用功能"""
    
    def __init__(self, 
                 db: Session,
                 repository: BaseRepository,
                 permission_service: Optional[ResourcePermissionService] = None):
        """初始化基础工具服务
        
        Args:
            db: 数据库会话
            repository: 工具仓库实例
            permission_service: 资源权限服务(可选)
        """
        self.db = db
        self.repository = repository
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
            
        return await self.permission_service.is_admin(user_id, self.db)
    
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
        
        # 设置创建者ID
        tool_data["creator_id"] = user_id
        
        # 创建工具
        return await self.repository.create(tool_data, self.db)
    
    async def get_tool(self, tool_id: str, user_id: str) -> Optional[Any]:
        """获取工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 获取的工具实例或None
        """
        return await self.repository.get_by_id(tool_id, self.db)
    
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
        return await self.repository.get_multi(
            self.db, skip=skip, limit=limit, filters=filters
        )
    
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
        # 获取工具
        tool = await self.repository.get_by_id(tool_id, self.db)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具 ID '{tool_id}' 不存在"
            )
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        is_creator = str(tool.creator_id) == user_id if hasattr(tool, "creator_id") else False
        
        if not (is_admin or is_creator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员或创建者可以更新此工具"
            )
        
        # 更新工具
        return await self.repository.update(tool_id, update_data, self.db)
    
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
        tool = await self.repository.get_by_id(tool_id, self.db)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工具 ID '{tool_id}' 不存在"
            )
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        is_creator = str(tool.creator_id) == user_id if hasattr(tool, "creator_id") else False
        
        if not (is_admin or is_creator):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员或创建者可以删除此工具"
            )
        
        # 删除工具
        return await self.repository.delete(tool_id, self.db)
    
    async def enable_tool(self, tool_id: str, user_id: str) -> Optional[Any]:
        """启用工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 更新后的工具实例或None
        """
        update_data = {"is_enabled": True}
        return await self.update_tool(tool_id, update_data, user_id)
    
    async def disable_tool(self, tool_id: str, user_id: str) -> Optional[Any]:
        """禁用工具
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[Any]: 更新后的工具实例或None
        """
        update_data = {"is_enabled": False}
        return await self.update_tool(tool_id, update_data, user_id)
