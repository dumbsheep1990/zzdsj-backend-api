"""
框架配置服务模块
处理AI框架配置管理相关的业务逻辑
"""

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.framework_config import FrameworkConfig
from app.repositories.framework_config_repository import FrameworkConfigRepository
from app.services.resource_permission_service import ResourcePermissionService

class FrameworkConfigService:
    """框架配置服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化框架配置服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = FrameworkConfigRepository()
        self.permission_service = permission_service
    
    async def create_framework_config(self, framework_config_data: Dict[str, Any], user_id: str) -> FrameworkConfig:
        """创建框架配置
        
        Args:
            framework_config_data: 框架配置数据
            user_id: 用户ID
            
        Returns:
            FrameworkConfig: 创建的框架配置实例
            
        Raises:
            HTTPException: 如果没有权限或框架名称已存在
        """
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以创建框架配置"
            )
        
        # 检查框架名称是否已存在
        existing_config = await self.repository.get_by_name(
            framework_config_data.get("framework_name"), self.db
        )
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"框架名称 '{framework_config_data.get('framework_name')}' 已存在"
            )
        
        # 创建框架配置
        framework_config = await self.repository.create(framework_config_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "framework_config", framework_config.id, user_id
        )
        
        return framework_config
    
    async def get_framework_config(self, config_id: str, user_id: str) -> Optional[FrameworkConfig]:
        """获取框架配置
        
        Args:
            config_id: 框架配置ID
            user_id: 用户ID
            
        Returns:
            Optional[FrameworkConfig]: 获取的框架配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取框架配置
        framework_config = await self.repository.get_by_id(config_id, self.db)
        if not framework_config:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "framework_config", config_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此框架配置"
            )
        
        return framework_config
    
    async def list_framework_configs(self, user_id: str, skip: int = 0, limit: int = 100) -> List[FrameworkConfig]:
        """获取框架配置列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[FrameworkConfig]: 框架配置列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有配置
        if is_admin:
            return await self.repository.list_all(skip, limit, self.db)
        
        # 非管理员只能查看已启用的配置
        return await self.repository.list_enabled(self.db)
    
    async def list_enabled_framework_configs(self) -> List[FrameworkConfig]:
        """获取所有启用的框架配置列表
        
        Returns:
            List[FrameworkConfig]: 启用的框架配置列表
        """
        return await self.repository.list_enabled(self.db)
    
    async def list_framework_configs_by_capability(self, capability: str, enabled_only: bool = True) -> List[FrameworkConfig]:
        """获取具有特定能力的框架配置列表
        
        Args:
            capability: 框架能力
            enabled_only: 是否只返回已启用的框架
            
        Returns:
            List[FrameworkConfig]: 框架配置列表
        """
        return await self.repository.list_by_capability(capability, enabled_only, self.db)
    
    async def update_framework_config(self, config_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[FrameworkConfig]:
        """更新框架配置
        
        Args:
            config_id: 框架配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[FrameworkConfig]: 更新后的框架配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或框架不存在
        """
        # 获取框架配置
        framework_config = await self.repository.get_by_id(config_id, self.db)
        if not framework_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="框架配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "framework_config", config_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此框架配置"
            )
        
        # 更新框架配置
        return await self.repository.update(config_id, update_data, self.db)
    
    async def enable_framework_config(self, config_id: str, user_id: str) -> Optional[FrameworkConfig]:
        """启用框架配置
        
        Args:
            config_id: 框架配置ID
            user_id: 用户ID
            
        Returns:
            Optional[FrameworkConfig]: 更新后的框架配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或框架不存在
        """
        # 获取框架配置
        framework_config = await self.repository.get_by_id(config_id, self.db)
        if not framework_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="框架配置不存在"
            )
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以启用框架配置"
            )
        
        # 启用框架配置
        return await self.repository.enable(config_id, self.db)
    
    async def disable_framework_config(self, config_id: str, user_id: str) -> Optional[FrameworkConfig]:
        """禁用框架配置
        
        Args:
            config_id: 框架配置ID
            user_id: 用户ID
            
        Returns:
            Optional[FrameworkConfig]: 更新后的框架配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或框架不存在
        """
        # 获取框架配置
        framework_config = await self.repository.get_by_id(config_id, self.db)
        if not framework_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="框架配置不存在"
            )
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以禁用框架配置"
            )
        
        # 禁用框架配置
        return await self.repository.disable(config_id, self.db)
    
    async def delete_framework_config(self, config_id: str, user_id: str) -> bool:
        """删除框架配置
        
        Args:
            config_id: 框架配置ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或框架不存在
        """
        # 获取框架配置
        framework_config = await self.repository.get_by_id(config_id, self.db)
        if not framework_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="框架配置不存在"
            )
        
        # 检查权限
        is_admin = await self._check_admin_permission(user_id)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除框架配置"
            )
        
        # 删除框架配置
        return await self.repository.delete(config_id, self.db)
    
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
