"""
LlamaIndex集成服务模块
处理LlamaIndex集成配置和管理相关的业务逻辑
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.llamaindex_integration import LlamaIndexIntegration
# 导入核心业务逻辑层
from core.integrations import LlamaIndexIntegrationManager
from app.services.resource_permission_service import ResourcePermissionService
from app.repositories.llamaindex_integration_repository import LlamaIndexIntegrationRepository

@register_service(service_type="llamaindex", priority="medium", description="LlamaIndex集成服务")
class LlamaIndexIntegrationService:
    """LlamaIndex集成服务类 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化LlamaIndex集成服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        # 使用核心业务逻辑层
        self.llamaindex_manager = LlamaIndexIntegrationManager(db)
        self.permission_service = permission_service
    
    async def create_integration(self, integration_data: Dict[str, Any], user_id: str) -> LlamaIndexIntegration:
        """创建LlamaIndex集成配置
        
        Args:
            integration_data: 集成配置数据
            user_id: 用户ID
            
        Returns:
            LlamaIndexIntegration: 创建的集成配置实例
            
        Raises:
            HTTPException: 如果集成名称已存在或没有权限
        """
        # 使用核心层创建集成配置
        result = await self.llamaindex_manager.create_integration(
            name=integration_data.get("name"),
            service_type=integration_data.get("service_type"),
            config=integration_data.get("config", {}),
            description=integration_data.get("description"),
            is_active=integration_data.get("is_active", True),
            metadata=integration_data.get("metadata")
        )
        
        if not result["success"]:
            if result.get("error_code") == "INTEGRATION_NAME_EXISTS":
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
            "llamaindex_integration", result["data"]["id"], user_id
        )
        
        # 转换为LlamaIndexIntegration对象以保持兼容性
        return LlamaIndexIntegration(**result["data"])
    
    async def get_integration(self, integration_id: str, user_id: str) -> Optional[LlamaIndexIntegration]:
        """获取集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此LlamaIndex集成配置"
            )
        
        # 使用核心层获取集成配置
        result = await self.llamaindex_manager.get_integration(integration_id)
        if not result["success"]:
            return None
        
        # 转换为LlamaIndexIntegration对象以保持兼容性
        return LlamaIndexIntegration(**result["data"])
    
    async def get_by_name(self, name: str, user_id: str) -> Optional[LlamaIndexIntegration]:
        """通过名称获取集成配置
        
        Args:
            name: 集成名称
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 获取的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 使用核心层获取集成配置
        result = await self.llamaindex_manager.get_integration_by_name(name)
        if not result["success"]:
            return None
        
        integration_data = result["data"]
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_data["id"], user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此LlamaIndex集成配置"
            )
        
        # 转换为LlamaIndexIntegration对象以保持兼容性
        return LlamaIndexIntegration(**integration_data)
    
    async def list_integrations(self, user_id: str, skip: int = 0, limit: int = 100) -> List[LlamaIndexIntegration]:
        """获取集成配置列表
        
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
            result = await self.llamaindex_manager.list_integrations(skip=skip, limit=limit)
            if result["success"]:
                return [LlamaIndexIntegration(**integration_data) for integration_data in result["data"]["integrations"]]
            return []
        
        # 获取用户有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        llamaindex_permissions = [p for p in user_permissions if p.resource_type == "llamaindex_integration"]
        
        if not llamaindex_permissions:
            return []
        
        # 获取有权限的集成配置
        integration_ids = [p.resource_id for p in llamaindex_permissions]
        integrations = []
        for integration_id in integration_ids:
            result = await self.llamaindex_manager.get_integration(integration_id)
            if result["success"]:
                integrations.append(LlamaIndexIntegration(**result["data"]))
        
        return integrations
    
    async def list_by_service_type(self, service_type: str, user_id: str) -> List[LlamaIndexIntegration]:
        """根据服务类型获取集成配置列表
        
        Args:
            service_type: 服务类型
            user_id: 用户ID
            
        Returns:
            List[LlamaIndexIntegration]: 集成配置列表
        """
        # 使用核心层获取指定服务类型的集成配置
        result = await self.llamaindex_manager.list_integrations(service_type=service_type)
        if not result["success"]:
            return []
        
        all_integrations = result["data"]["integrations"]
        
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有集成配置
        if is_admin:
            return [LlamaIndexIntegration(**integration_data) for integration_data in all_integrations]
        
        # 普通用户只能查看有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        llamaindex_permissions = [p for p in user_permissions if p.resource_type == "llamaindex_integration"]
        accessible_ids = [p.resource_id for p in llamaindex_permissions]
        
        accessible_integrations = [
            integration_data for integration_data in all_integrations
            if integration_data["id"] in accessible_ids
        ]
        
        return [LlamaIndexIntegration(**integration_data) for integration_data in accessible_integrations]
    
    async def update_integration(
        self, 
        integration_id: str, 
        update_data: Dict[str, Any], 
        user_id: str
    ) -> Optional[LlamaIndexIntegration]:
        """更新集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或更新失败
        """
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "write"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限修改此LlamaIndex集成配置"
            )
        
        # 使用核心层更新集成配置
        result = await self.llamaindex_manager.update_integration(integration_id, update_data)
        
        if not result["success"]:
            if result.get("error_code") == "INTEGRATION_NAME_EXISTS":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"]
                )
        
        # 转换为LlamaIndexIntegration对象以保持兼容性
        return LlamaIndexIntegration(**result["data"])
    
    async def delete_integration(self, integration_id: str, user_id: str) -> bool:
        """删除集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功删除
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "llamaindex_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此LlamaIndex集成配置"
            )
        
        # 使用核心层删除集成配置
        result = await self.llamaindex_manager.delete_integration(integration_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return True
    
    # ============ 私有辅助方法 ============
    
    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否为管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否为管理员
        """
        # 这里可以实现管理员权限检查逻辑
        # 目前返回False，具体实现需要根据权限系统
        return False
