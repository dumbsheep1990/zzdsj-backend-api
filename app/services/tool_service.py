"""
工具服务模块
处理工具定义、配置和管理相关的业务逻辑
"""

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.tool import Tool
from app.repositories.tool_repository import ToolRepository
from app.services.resource_permission_service import ResourcePermissionService

class ToolService:
    """工具服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化工具服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = ToolRepository()
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
        # 检查工具名称是否已存在
        existing_tool = await self.repository.get_by_name(
            tool_data.get("name"), self.db
        )
        if existing_tool:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"工具名称 '{tool_data.get('name')}' 已存在"
            )
        
        # 创建工具
        tool = await self.repository.create(tool_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "tool", tool.id, user_id
        )
        
        return tool
    
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
        # 获取工具
        tool = await self.repository.get_by_id(tool_id, self.db)
        if not tool:
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
        
        return tool
    
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
        # 获取工具
        tool = await self.repository.get_by_name(tool_name, self.db)
        if not tool:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "tool", tool.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此工具"
            )
        
        return tool
    
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
            return await self.repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的工具
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        tool_permissions = [p for p in user_permissions if p.resource_type == "tool"]
        
        if not tool_permissions:
            return []
        
        # 获取有权限的工具
        tool_ids = [p.resource_id for p in tool_permissions]
        tools = []
        for tool_id in tool_ids:
            tool = await self.repository.get_by_id(tool_id, self.db)
            if tool:
                tools.append(tool)
        
        return tools
    
    async def list_tools_by_category(self, category: str, user_id: str) -> List[Tool]:
        """获取指定类别的工具列表
        
        Args:
            category: 工具类别
            user_id: 用户ID
            
        Returns:
            List[Tool]: 工具列表
        """
        # 获取指定类别的工具
        all_tools = await self.repository.list_by_category(category, self.db)
        
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        if is_admin:
            return all_tools
        
        # 过滤用户有权限的工具
        result = []
        for tool in all_tools:
            has_permission = await self.permission_service.check_permission(
                "tool", tool.id, user_id, "read"
            )
            
            if has_permission:
                result.append(tool)
        
        return result
    
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
        # 获取工具
        tool = await self.repository.get_by_id(tool_id, self.db)
        if not tool:
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
        return await self.repository.delete(tool_id, self.db)
    
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
