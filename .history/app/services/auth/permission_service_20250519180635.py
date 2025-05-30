"""
资源权限服务模块
处理资源权限管理和访问控制相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.resource_permission import ResourcePermission
from app.repositories.resource_permission_repository import ResourcePermissionRepository
from app.services.user_service import UserService

@register_service(service_type="resource-permission", priority="high", description="资源权限管理服务")
class ResourcePermissionService:
    """资源权限服务类"""
    
    def __init__(self, db: Session = Depends(get_db), user_service: UserService = Depends()):
        """初始化资源权限服务
        
        Args:
            db: 数据库会话
            user_service: 用户服务
        """
        self.db = db
        self.repository = ResourcePermissionRepository()
        self.user_service = user_service
    
    async def create_permission(self, resource_type: str, resource_id: str, 
                             user_id: str, permission_level: str) -> ResourcePermission:
        """创建资源权限
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            user_id: 用户ID
            permission_level: 权限级别
            
        Returns:
            ResourcePermission: 创建的资源权限实例
        """
        permission_data = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "permission_level": permission_level
        }
        
        return await self.repository.create(permission_data, self.db)
    
    async def get_permission(self, resource_type: str, resource_id: str, user_id: str) -> Optional[ResourcePermission]:
        """获取资源权限
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            user_id: 用户ID
            
        Returns:
            Optional[ResourcePermission]: 查找到的资源权限或None
        """
        return await self.repository.get_permission(resource_type, resource_id, user_id, self.db)
    
    async def check_permission(self, resource_type: str, resource_id: str, 
                            user_id: str, required_level: str) -> bool:
        """检查用户是否具有对资源的特定权限级别
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            user_id: 用户ID
            required_level: 所需权限级别
            
        Returns:
            bool: 是否具有所需权限
        """
        # 获取用户信息，检查是否为管理员
        user = await self.user_service.get_by_id(user_id)
        if user and user.role == "admin":
            return True  # 管理员拥有所有权限
        
        # 检查特定权限记录
        permission = await self.repository.get_permission(resource_type, resource_id, user_id, self.db)
        if not permission:
            return False
        
        # 权限级别比较
        # 假设权限级别从低到高为: 'read', 'edit', 'admin'
        permission_levels = {
            'read': 1,
            'edit': 2,
            'admin': 3
        }
        
        return permission_levels.get(permission.permission_level, 0) >= permission_levels.get(required_level, 0)
    
    async def list_user_permissions(self, user_id: str) -> List[ResourcePermission]:
        """获取用户的所有权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[ResourcePermission]: 用户权限列表
        """
        return await self.repository.list_by_user(user_id, self.db)
    
    async def list_resource_permissions(self, resource_type: str, resource_id: str) -> List[ResourcePermission]:
        """获取资源的所有权限
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            
        Returns:
            List[ResourcePermission]: 资源权限列表
        """
        return await self.repository.list_by_resource(resource_type, resource_id, self.db)
    
    async def update_permission(self, resource_type: str, resource_id: str, 
                             user_id: str, permission_level: str) -> Optional[ResourcePermission]:
        """更新资源权限
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            user_id: 用户ID
            permission_level: 新的权限级别
            
        Returns:
            Optional[ResourcePermission]: 更新后的资源权限或None
        """
        permission = await self.repository.get_permission(resource_type, resource_id, user_id, self.db)
        if not permission:
            return await self.create_permission(resource_type, resource_id, user_id, permission_level)
        
        update_data = {"permission_level": permission_level}
        return await self.repository.update(permission.id, update_data, self.db)
    
    async def delete_permission(self, resource_type: str, resource_id: str, user_id: str) -> bool:
        """删除资源权限
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
        """
        permission = await self.repository.get_permission(resource_type, resource_id, user_id, self.db)
        if not permission:
            return False
        
        return await self.repository.delete(permission.id, self.db)
    
    async def ensure_owner_permission(self, resource_type: str, resource_id: str, 
                                   user_id: str) -> ResourcePermission:
        """确保用户是资源的所有者
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            user_id: 用户ID
            
        Returns:
            ResourcePermission: 创建或获取的所有者权限实例
        """
        permission = await self.repository.get_permission(resource_type, resource_id, user_id, self.db)
        if not permission:
            return await self.create_permission(resource_type, resource_id, user_id, "admin")
        
        if permission.permission_level != "admin":
            permission.permission_level = "admin"
            self.db.commit()
            self.db.refresh(permission)
        
        return permission
    
    async def share_resource(self, resource_type: str, resource_id: str, 
                         owner_id: str, target_user_id: str, 
                         permission_level: str = "read") -> Optional[ResourcePermission]:
        """共享资源给其他用户
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            owner_id: 所有者用户ID
            target_user_id: 目标用户ID
            permission_level: 分配的权限级别
            
        Returns:
            Optional[ResourcePermission]: 创建的资源权限或None
            
        Raises:
            HTTPException: 如果当前用户不是该资源的所有者
        """
        # 验证当前用户是否为资源所有者
        owner_permission = await self.repository.get_permission(resource_type, resource_id, owner_id, self.db)
        if not owner_permission or owner_permission.permission_level != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有资源所有者可以共享资源"
            )
        
        # 创建目标用户的权限
        return await self.create_permission(resource_type, resource_id, target_user_id, permission_level)
