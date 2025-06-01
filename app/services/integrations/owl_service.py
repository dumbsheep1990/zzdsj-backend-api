"""
OWL框架集成服务模块
处理OWL框架智能体社会协作系统相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.owl_integration import OwlIntegration
from app.repositories.owl_integration_repository import OwlIntegrationRepository
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="owl", priority="high", description="OWL智能体协作框架服务")
class OwlIntegrationService:
    """OWL框架集成服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化OWL框架集成服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = OwlIntegrationRepository()
        self.permission_service = permission_service
    
    async def create_integration(self, integration_data: Dict[str, Any], user_id: str) -> OwlIntegration:
        """创建OWL框架集成配置
        
        Args:
            integration_data: 集成配置数据
            user_id: 用户ID
            
        Returns:
            OwlIntegration: 创建的集成配置实例
            
        Raises:
            HTTPException: 如果社会名称已存在或没有权限
        """
        # 检查社会名称是否已存在
        if integration_data.get("society_name"):
            existing_integration = await self.repository.get_by_society_name(
                integration_data.get("society_name"), self.db
            )
            if existing_integration:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"社会名称 '{integration_data.get('society_name')}' 已存在"
                )
        
        # 创建集成配置
        integration = await self.repository.create(integration_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "owl_integration", integration.id, user_id
        )
        
        return integration
    
    async def get_integration(self, integration_id: str, user_id: str) -> Optional[OwlIntegration]:
        """获取OWL框架集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此OWL集成配置"
            )
        
        return integration
    
    async def get_by_society_name(self, society_name: str, user_id: str) -> Optional[OwlIntegration]:
        """通过社会名称获取OWL框架集成配置
        
        Args:
            society_name: 社会名称
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_society_name(society_name, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此OWL集成配置"
            )
        
        return integration
    
    async def list_integrations(self, user_id: str, skip: int = 0, limit: int = 100) -> List[OwlIntegration]:
        """获取OWL框架集成配置列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[OwlIntegration]: 集成配置列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有集成配置
        if is_admin:
            return await self.repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        owl_permissions = [p for p in user_permissions if p.resource_type == "owl_integration"]
        
        if not owl_permissions:
            return []
        
        # 获取有权限的集成配置
        integration_ids = [p.resource_id for p in owl_permissions]
        integrations = []
        for integration_id in integration_ids:
            integration = await self.repository.get_by_id(integration_id, self.db)
            if integration:
                integrations.append(integration)
        
        return integrations
    
    async def update_integration(self, integration_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[OwlIntegration]:
        """更新OWL框架集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OWL集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此OWL集成配置"
            )
        
        # 更新集成配置
        return await self.repository.update(integration_id, update_data, self.db)
    
    async def add_agent_config(self, integration_id: str, agent_config: Dict[str, Any], user_id: str) -> Optional[OwlIntegration]:
        """添加智能体配置
        
        Args:
            integration_id: 集成配置ID
            agent_config: 智能体配置
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OWL集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此OWL集成配置的智能体配置"
            )
        
        # 添加智能体配置
        return await self.repository.add_agent_config(integration_id, agent_config, self.db)
    
    async def remove_agent_config(self, integration_id: str, agent_name: str, user_id: str) -> Optional[OwlIntegration]:
        """移除智能体配置
        
        Args:
            integration_id: 集成配置ID
            agent_name: 智能体名称
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OWL集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此OWL集成配置的智能体配置"
            )
        
        # 移除智能体配置
        return await self.repository.remove_agent_config(integration_id, agent_name, self.db)
    
    async def update_toolkit_configs(self, integration_id: str, new_configs: Dict[str, Any], user_id: str) -> Optional[OwlIntegration]:
        """更新工具包配置
        
        Args:
            integration_id: 集成配置ID
            new_configs: 新的工具包配置
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OWL集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此OWL集成配置的工具包配置"
            )
        
        # 更新工具包配置
        return await self.repository.update_toolkit_configs(integration_id, new_configs, self.db)
    
    async def update_workflow_configs(self, integration_id: str, new_configs: Dict[str, Any], user_id: str) -> Optional[OwlIntegration]:
        """更新工作流配置
        
        Args:
            integration_id: 集成配置ID
            new_configs: 新的工作流配置
            user_id: 用户ID
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OWL集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此OWL集成配置的工作流配置"
            )
        
        # 更新工作流配置
        return await self.repository.update_workflow_configs(integration_id, new_configs, self.db)
    
    async def delete_integration(self, integration_id: str, user_id: str) -> bool:
        """删除OWL框架集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OWL集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "owl_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此OWL集成配置"
            )
        
        # 删除集成配置
        return await self.repository.delete(integration_id, self.db)
    
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
