"""
LightRAG框架集成服务模块
处理LightRAG框架文档处理、图谱和查询引擎管理相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.lightrag_integration import LightRAGIntegration
from app.repositories.lightrag_integration_repository import LightRAGIntegrationRepository
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="lightrag", priority="high", description="LightRAG轻量级检索增强生成服务")
class LightRAGIntegrationService:
    """LightRAG框架集成服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化LightRAG框架集成服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = LightRAGIntegrationRepository()
        self.permission_service = permission_service
    
    async def create_integration(self, integration_data: Dict[str, Any], user_id: str) -> LightRAGIntegration:
        """创建LightRAG框架集成配置
        
        Args:
            integration_data: 集成配置数据
            user_id: 用户ID
            
        Returns:
            LightRAGIntegration: 创建的集成配置实例
            
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
            "lightrag_integration", integration.id, user_id
        )
        
        return integration
    
    async def get_integration(self, integration_id: str, user_id: str) -> Optional[LightRAGIntegration]:
        """获取LightRAG框架集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此LightRAG集成配置"
            )
        
        return integration
    
    async def get_by_index_name(self, index_name: str, user_id: str) -> Optional[LightRAGIntegration]:
        """通过索引名称获取LightRAG框架集成配置
        
        Args:
            index_name: 索引名称
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_index_name(index_name, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此LightRAG集成配置"
            )
        
        return integration
    
    async def list_integrations(self, user_id: str, skip: int = 0, limit: int = 100) -> List[LightRAGIntegration]:
        """获取LightRAG框架集成配置列表
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[LightRAGIntegration]: 集成配置列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有集成配置
        if is_admin:
            return await self.repository.list_all(skip, limit, self.db)
        
        # 获取用户有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        lightrag_permissions = [p for p in user_permissions if p.resource_type == "lightrag_integration"]
        
        if not lightrag_permissions:
            return []
        
        # 获取有权限的集成配置
        integration_ids = [p.resource_id for p in lightrag_permissions]
        integrations = []
        for integration_id in integration_ids:
            integration = await self.repository.get_by_id(integration_id, self.db)
            if integration:
                integrations.append(integration)
        
        return integrations
    
    async def update_integration(self, integration_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[LightRAGIntegration]:
        """更新LightRAG框架集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LightRAG集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LightRAG集成配置"
            )
        
        # 屏蔽API密钥字段（如果存在）
        if "api_key" in update_data and not update_data["api_key"]:
            update_data.pop("api_key")
        
        # 更新集成配置
        return await self.repository.update(integration_id, update_data, self.db)
    
    async def update_document_processor_config(self, integration_id: str, new_config: Dict[str, Any], user_id: str) -> Optional[LightRAGIntegration]:
        """更新文档处理器配置
        
        Args:
            integration_id: 集成配置ID
            new_config: 新的文档处理器配置
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LightRAG集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LightRAG集成配置的文档处理器配置"
            )
        
        # 更新文档处理器配置
        return await self.repository.update_document_processor_config(integration_id, new_config, self.db)
    
    async def update_graph_config(self, integration_id: str, new_config: Dict[str, Any], user_id: str) -> Optional[LightRAGIntegration]:
        """更新图谱配置
        
        Args:
            integration_id: 集成配置ID
            new_config: 新的图谱配置
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LightRAG集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LightRAG集成配置的图谱配置"
            )
        
        # 更新图谱配置
        return await self.repository.update_graph_config(integration_id, new_config, self.db)
    
    async def update_query_engine_config(self, integration_id: str, new_config: Dict[str, Any], user_id: str) -> Optional[LightRAGIntegration]:
        """更新查询引擎配置
        
        Args:
            integration_id: 集成配置ID
            new_config: 新的查询引擎配置
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LightRAG集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LightRAG集成配置的查询引擎配置"
            )
        
        # 更新查询引擎配置
        return await self.repository.update_query_engine_config(integration_id, new_config, self.db)
    
    async def set_api_key(self, integration_id: str, api_key: str, user_id: str) -> Optional[LightRAGIntegration]:
        """设置API密钥
        
        Args:
            integration_id: 集成配置ID
            api_key: API密钥
            user_id: 用户ID
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LightRAG集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此LightRAG集成配置的API密钥"
            )
        
        # 更新API密钥
        return await self.repository.set_api_key(integration_id, api_key, self.db)
    
    async def delete_integration(self, integration_id: str, user_id: str) -> bool:
        """删除LightRAG框架集成配置
        
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
                detail="LightRAG集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "lightrag_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此LightRAG集成配置"
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
