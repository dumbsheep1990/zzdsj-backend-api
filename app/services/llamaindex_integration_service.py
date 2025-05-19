"""
LlamaIndex集成服务模块
处理LlamaIndex框架索引和存储上下文管理相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.llamaindex_integration import LlamaIndexIntegration
from app.repositories.llamaindex_integration_repository import LlamaIndexIntegrationRepository
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="llamaindex", priority="high", description="LlamaIndex框架集成服务")
class LlamaIndexIntegrationService:
    """LlamaIndex集成服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化LlamaIndex集成服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = LlamaIndexIntegrationRepository()
        self.permission_service = permission_service
    
    async def create_integration(self, integration_data: Dict[str, Any], user_id: str) -> LlamaIndexIntegration:
        """创建LlamaIndex集成配置
        
        Args:
            integration_data: 集成配置数据
            user_id: 用户ID
            
        Returns:
            LlamaIndexIntegration: 创建的集成配置实例
            
        Raises:
            HTTPException: 如果索引名称已存在或没有权限
        """
        # 检查索引名称是否已存在
        existing_integration = await self.repository.get_by_index_name(
            integration_data.get("index_name"), self.db
        )
        if existing_integration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"索引名称 '{integration_data.get('index_name')}' 已存在"
            )
        
        # 创建集成配置
        integration = await self.repository.create(integration_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "llamaindex_integration", integration.id, user_id
        )
        
        return integration
    
    async def get_integration(self, integration_id: str, user_id: str) -> Optional[LlamaIndexIntegration]:
        """获取LlamaIndex集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此LlamaIndex集成配置"
            )
        
        return integration
    
    async def get_by_index_name(self, index_name: str, user_id: str) -> Optional[LlamaIndexIntegration]:
        """通过索引名称获取LlamaIndex集成配置
        
        Args:
            index_name: 索引名称
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_index_name(index_name, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此LlamaIndex集成配置"
            )
        
        return integration
    
    async def list_integrations(self, user_id: str, skip: int = 0, limit: int = 100) -> List[LlamaIndexIntegration]:
        """获取LlamaIndex集成配置列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[LlamaIndexIntegration]: 集成配置列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有集成配置
        if is_admin:
            return await self.repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        llamaindex_permissions = [p for p in user_permissions if p.resource_type == "llamaindex_integration"]
        
        if not llamaindex_permissions:
            return []
        
        # 获取有权限的集成配置
        integration_ids = [p.resource_id for p in llamaindex_permissions]
        integrations = []
        for integration_id in integration_ids:
            integration = await self.repository.get_by_id(integration_id, self.db)
            if integration:
                integrations.append(integration)
        
        return integrations
    
    async def list_by_knowledge_base(self, knowledge_base_id: str, user_id: str) -> List[LlamaIndexIntegration]:
        """获取与指定知识库关联的LlamaIndex集成配置列表
        
        Args:
            knowledge_base_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            List[LlamaIndexIntegration]: 集成配置列表
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查知识库权限
        has_kb_permission = await self.permission_service.check_permission(
            "knowledge_base", knowledge_base_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_kb_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此知识库的LlamaIndex集成配置"
            )
        
        # 获取知识库关联的集成配置
        return await self.repository.list_by_knowledge_base(knowledge_base_id, self.db)
    
    async def update_integration(self, integration_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[LlamaIndexIntegration]:
        """更新LlamaIndex集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LlamaIndex集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LlamaIndex集成配置"
            )
        
        # 更新集成配置
        return await self.repository.update(integration_id, update_data, self.db)
    
    async def update_index_settings(self, integration_id: str, new_settings: Dict[str, Any], user_id: str) -> Optional[LlamaIndexIntegration]:
        """更新索引设置
        
        Args:
            integration_id: 集成配置ID
            new_settings: 新的索引设置
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LlamaIndex集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LlamaIndex集成配置的索引设置"
            )
        
        # 更新索引设置
        return await self.repository.update_index_settings(integration_id, new_settings, self.db)
    
    async def update_storage_context(self, integration_id: str, new_context: Dict[str, Any], user_id: str) -> Optional[LlamaIndexIntegration]:
        """更新存储上下文配置
        
        Args:
            integration_id: 集成配置ID
            new_context: 新的存储上下文配置
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LlamaIndex集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LlamaIndex集成配置的存储上下文"
            )
        
        # 更新存储上下文配置
        return await self.repository.update_storage_context(integration_id, new_context, self.db)
    
    async def delete_integration(self, integration_id: str, user_id: str) -> bool:
        """删除LlamaIndex集成配置
        
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
                detail="LlamaIndex集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此LlamaIndex集成配置"
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
