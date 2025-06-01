"""
OWL框架工具服务模块
处理OWL框架工具和工具包相关的业务逻辑，继承自基础工具服务
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.owl_tool import OwlTool, OwlToolkit
from app.repositories.owl_tool_repository import OwlToolRepository, OwlToolkitRepository
from app.services.resource_permission_service import ResourcePermissionService
from app.services.base_tool_service import BaseToolService

class OwlToolService(BaseToolService):
    """OWL框架工具服务类，继承自基础工具服务"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化OWL框架工具服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        # 初始化工具仓库
        self.tool_repository = OwlToolRepository()
        self.toolkit_repository = OwlToolkitRepository()
        
        # 调用父类初始化方法
        super().__init__(db, self.tool_repository, permission_service)
    
    # ==================== 工具管理 ====================
    
    async def register_tool(self, tool_data: Dict[str, Any], user_id: str) -> OwlTool:
        """注册OWL工具，重写基类方法
        
        Args:
            tool_data: 工具数据
            user_id: 用户ID
            
        Returns:
            OwlTool: 创建的工具实例
            
        Raises:
            HTTPException: 如果工具名称已存在或没有权限
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以注册工具"
            )
        
        # 检查工具名称是否已存在
        existing_tool = await self.tool_repository.get_by_name(
            tool_data.get("name"), self.db
        )
        if existing_tool:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工具名称 '{tool_data.get('name')}' 已存在"
            )
        
        # 检查工具包是否存在
        toolkit_name = tool_data.get("toolkit_name")
        existing_toolkit = await self.toolkit_repository.get_by_name(toolkit_name, self.db)
        if not existing_toolkit:
            # 自动创建工具包
            toolkit_data = {
                "name": toolkit_name,
                "description": f"{toolkit_name} 工具包",
                "is_enabled": True,
                "config": {}
            }
            await self.toolkit_repository.create(toolkit_data, self.db)
        
        # 使用基类方法创建工具
        return await super().create_tool(tool_data, user_id)
    
    async def get_tool(self, tool_id: str, user_id: str) -> Optional[OwlTool]:
        """获取OWL工具，调用基类方法
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[OwlTool]: 获取的工具实例或None
        """
        # 使用基类方法获取工具
        return await super().get_tool(tool_id, user_id)
    
    async def get_tool_by_name(self, name: str, user_id: Optional[str] = None) -> Optional[OwlTool]:
        """通过名称获取OWL工具，扩展基类方法
        
        Args:
            name: 工具名称
            user_id: 用户ID（可选）
            
        Returns:
            Optional[OwlTool]: 获取的工具实例或None
        """
        return await self.tool_repository.get_by_name(name, self.db)
    
    async def list_tools(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[OwlTool]:
        """获取OWL工具列表，调用基类方法
        
        Args:
            skip: 跳过数量
            limit: 返回限制
            filters: 过滤条件
            
        Returns:
            List[OwlTool]: 工具列表
        """
        return await super().list_tools(skip, limit, filters)
    
    async def list_tools_by_toolkit(self, toolkit_name: str) -> List[OwlTool]:
        """获取指定工具包的工具列表
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            List[OwlTool]: 工具列表
        """
        # 获取工具列表
        return await self.tool_repository.list_by_toolkit(toolkit_name, self.db)
    
    async def list_enabled_tools(self) -> List[OwlTool]:
        """获取已启用的OWL工具列表，利用基类的list_tools方法
        
        Returns:
            List[OwlTool]: 已启用的工具列表
        """
        filters = {"is_enabled": True}
        return await super().list_tools(filters=filters)
    
    async def update_tool(self, tool_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[OwlTool]:
        """更新OWL工具，提供特定的权限检查
        
        Args:
            tool_id: 工具ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[OwlTool]: 更新后的工具实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以更新OWL工具"
            )
            
        # 调用父类方法更新工具
        return await super().update_tool(tool_id, update_data, user_id)
    
    async def enable_tool(self, tool_id: str, user_id: str) -> Optional[OwlTool]:
        """启用OWL工具，调用基类方法
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[OwlTool]: 更新后的工具实例或None
        """
        return await super().enable_tool(tool_id, user_id)
    
    async def disable_tool(self, tool_id: str, user_id: str) -> Optional[OwlTool]:
        """禁用OWL工具，调用基类方法
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            Optional[OwlTool]: 更新后的工具实例或None
        """
        return await super().disable_tool(tool_id, user_id)
    
    async def configure_tool_api_key(self, tool_id: str, api_key_config: Dict[str, Any], user_id: str) -> Optional[OwlTool]:
        """配置OWL工具API密钥
        
        Args:
            tool_id: 工具ID
            api_key_config: API密钥配置
            user_id: 用户ID
            
        Returns:
            Optional[OwlTool]: 更新后的工具实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 获取工具
        tool = await self.tool_repository.get_by_id(tool_id, self.db)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具不存在"
            )
        
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以配置OWL工具API密钥"
            )
        
        # 更新API密钥配置
        update_data = {
            "requires_api_key": True,
            "api_key_config": api_key_config
        }
        
        return await self.tool_repository.update(tool_id, update_data, self.db)
    
    async def delete_tool(self, tool_id: str, user_id: str) -> bool:
        """删除OWL工具，提供特定的权限检查
        
        Args:
            tool_id: 工具ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或工具不存在
        """
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除OWL工具"
            )
        
        # 调用父类方法删除工具
        return await super().delete_tool(tool_id, user_id)
    
    # ==================== 工具包管理 ====================
    
    async def register_toolkit(self, toolkit_data: Dict[str, Any], user_id: str) -> OwlToolkit:
        """注册工具包
        
        Args:
            toolkit_data: 工具包数据
            user_id: 用户ID
            
        Returns:
            OwlToolkit: 创建的工具包实例
            
        Raises:
            HTTPException: 如果工具包名称已存在或没有权限
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以注册工具包"
            )
        
        # 检查工具包名称是否已存在
        existing_toolkit = await self.toolkit_repository.get_by_name(
            toolkit_data.get("name"), self.db
        )
        if existing_toolkit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工具包名称 '{toolkit_data.get('name')}' 已存在"
            )
        
        # 创建工具包
        return await self.toolkit_repository.create(toolkit_data, self.db)
    
    async def get_toolkit(self, toolkit_id: str) -> Optional[OwlToolkit]:
        """获取工具包
        
        Args:
            toolkit_id: 工具包ID
            
        Returns:
            Optional[OwlToolkit]: 获取的工具包实例或None
        """
        # 获取工具包
        toolkit = await self.toolkit_repository.get_by_id(toolkit_id, self.db)
        return toolkit
    
    async def get_toolkit_by_name(self, name: str) -> Optional[OwlToolkit]:
        """通过名称获取工具包
        
        Args:
            name: 工具包名称
            
        Returns:
            Optional[OwlToolkit]: 获取的工具包实例或None
        """
        # 获取工具包
        toolkit = await self.toolkit_repository.get_by_name(name, self.db)
        return toolkit
    
    async def list_toolkits(self, skip: int = 0, limit: int = 100) -> List[OwlToolkit]:
        """获取工具包列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[OwlToolkit]: 工具包列表
        """
        # 获取工具包列表
        return await self.toolkit_repository.list_all(skip, limit, self.db)
    
    async def list_enabled_toolkits(self) -> List[OwlToolkit]:
        """获取已启用的工具包列表
        
        Returns:
            List[OwlToolkit]: 已启用的工具包列表
        """
        # 获取已启用的工具包列表
        return await self.toolkit_repository.list_enabled(self.db)
    
    async def update_toolkit(self, toolkit_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[OwlToolkit]:
        """更新工具包
        
        Args:
            toolkit_id: 工具包ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[OwlToolkit]: 更新后的工具包实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具包不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以更新工具包"
            )
        
        # 获取工具包
        toolkit = await self.toolkit_repository.get_by_id(toolkit_id, self.db)
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在"
            )
        
        # 更新工具包
        return await self.toolkit_repository.update(toolkit_id, update_data, self.db)
    
    async def enable_toolkit(self, toolkit_id: str, user_id: str) -> Optional[OwlToolkit]:
        """启用工具包
        
        Args:
            toolkit_id: 工具包ID
            user_id: 用户ID
            
        Returns:
            Optional[OwlToolkit]: 更新后的工具包实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具包不存在
        """
        # 更新工具包
        return await self.update_toolkit(toolkit_id, {"is_enabled": True}, user_id)
    
    async def disable_toolkit(self, toolkit_id: str, user_id: str) -> Optional[OwlToolkit]:
        """禁用工具包
        
        Args:
            toolkit_id: 工具包ID
            user_id: 用户ID
            
        Returns:
            Optional[OwlToolkit]: 更新后的工具包实例或None
            
        Raises:
            HTTPException: 如果没有权限或工具包不存在
        """
        # 更新工具包
        return await self.update_toolkit(toolkit_id, {"is_enabled": False}, user_id)
    
    async def delete_toolkit(self, toolkit_id: str, user_id: str) -> bool:
        """删除工具包
        
        Args:
            toolkit_id: 工具包ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或工具包不存在
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除工具包"
            )
        
        # 获取工具包
        toolkit = await self.toolkit_repository.get_by_id(toolkit_id, self.db)
        if not toolkit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工具包不存在"
            )
        
        # 删除工具包关联的所有工具
        tools = await self.tool_repository.list_by_toolkit(toolkit.name, self.db)
        for tool in tools:
            await self.tool_repository.delete(tool.id, self.db)
        
        # 删除工具包
        return await self.toolkit_repository.delete(toolkit_id, self.db)
    
    # ==================== 辅助方法 ====================
    
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
