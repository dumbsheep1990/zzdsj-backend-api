"""
MCP服务集成服务模块
处理MCP服务连接、资源访问和认证相关的业务逻辑
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.mcp_integration import MCPIntegration
from app.repositories.mcp_integration_repository import MCPIntegrationRepository
from app.services.resource_permission_service import ResourcePermissionService

@register_service(service_type="mcp", priority="high", description="MCP服务集成服务")
class MCPIntegrationService:
    """MCP服务集成服务类"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化MCP服务集成服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        self.repository = MCPIntegrationRepository()
        self.permission_service = permission_service
    
    async def create_integration(self, integration_data: Dict[str, Any], user_id: str) -> MCPIntegration:
        """创建MCP服务集成配置
        
        Args:
            integration_data: 集成配置数据
            user_id: 用户ID
            
        Returns:
            MCPIntegration: 创建的集成配置实例
            
        Raises:
            HTTPException: 如果服务器名称已存在或没有权限
        """
        # 检查服务器名称是否已存在
        existing_integration = await self.repository.get_by_server_name(
            integration_data.get("server_name"), self.db
        )
        if existing_integration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"服务器名称 '{integration_data.get('server_name')}' 已存在"
            )
        
        # 创建集成配置
        integration = await self.repository.create(integration_data, self.db)
        
        # 为创建者分配所有者权限
        await self.permission_service.ensure_owner_permission(
            "mcp_integration", integration.id, user_id
        )
        
        return integration
    
    async def get_integration(self, integration_id: str, user_id: str) -> Optional[MCPIntegration]:
        """获取MCP服务集成配置
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 获取的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此MCP服务集成配置"
            )
        
        return integration
    
    async def get_integration_with_credentials(self, integration_id: str, user_id: str) -> Optional[MCPIntegration]:
        """获取MCP服务集成配置（包含认证凭据）
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 获取的集成配置实例或None，包含完整认证信息
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限（需要管理员权限）
        is_admin = await self._check_admin_permission(user_id)
        has_admin_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "admin"
        )
        
        if not (is_admin or has_admin_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限才能访问完整的认证信息"
            )
            
        # 获取集成配置
        return await self.repository.get_by_id(integration_id, self.db)
    
    async def get_by_server_name(self, server_name: str, user_id: str) -> Optional[MCPIntegration]:
        """通过服务器名称获取MCP服务集成配置
        
        Args:
            server_name: 服务器名称
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 获取的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 获取集成配置
        integration = await self.repository.get_by_server_name(server_name, self.db)
        if not integration:
            return None
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration.id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此MCP服务集成配置"
            )
        
        return integration
    
    async def list_integrations(self, user_id: str, skip: int = 0, limit: int = 100) -> List[MCPIntegration]:
        """获取MCP服务集成配置列表，所有结果会隐藏敏感信息
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[MCPIntegration]: 集成配置列表
        """
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有集成配置
        if is_admin:
            integrations = await self.repository.list_all(skip, limit, self.db)
            return [self._hide_sensitive_info(i) for i in integrations]
        
        # 获取用户有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        mcp_permissions = [p for p in user_permissions if p.resource_type == "mcp_integration"]
        
        if not mcp_permissions:
            return []
        
        # 获取有权限的集成配置
        integration_ids = [p.resource_id for p in mcp_permissions]
        integrations = []
        for integration_id in integration_ids:
            integration = await self.repository.get_by_id(integration_id, self.db)
            if integration:
                integrations.append(self._hide_sensitive_info(integration))
        
        return integrations
    
    async def list_active_integrations(self, user_id: str) -> List[MCPIntegration]:
        """获取所有活跃的MCP服务集成配置列表，所有结果会隐藏敏感信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[MCPIntegration]: 活跃的集成配置列表
        """
        # 获取活跃的集成配置
        active_integrations = await self.repository.list_active(self.db)
        
        # 过滤没有权限的配置
        result = []
        for integration in active_integrations:
            has_permission = await self.permission_service.check_permission(
                "mcp_integration", integration.id, user_id, "read"
            ) or await self._check_admin_permission(user_id)
            
            if has_permission:
                result.append(self._hide_sensitive_info(integration))
        
        return result
    
    async def update_integration(self, integration_id: str, update_data: Dict[str, Any], user_id: str) -> Optional[MCPIntegration]:
        """更新MCP服务集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此MCP服务集成配置"
            )
        
        # 屏蔽敏感字段（如果不是管理员）
        is_admin = await self._check_admin_permission(user_id)
        has_admin_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "admin"
        )
        
        if not (is_admin or has_admin_permission):
            if "auth_credentials" in update_data:
                update_data.pop("auth_credentials")
        
        # 更新集成配置
        updated = await self.repository.update(integration_id, update_data, self.db)
        return self._hide_sensitive_info(updated) if updated else None
    
    async def activate(self, integration_id: str, user_id: str) -> Optional[MCPIntegration]:
        """激活MCP服务
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限激活此MCP服务"
            )
        
        # 激活MCP服务
        activated = await self.repository.activate(integration_id, self.db)
        return self._hide_sensitive_info(activated) if activated else None
    
    async def deactivate(self, integration_id: str, user_id: str) -> Optional[MCPIntegration]:
        """停用MCP服务
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限停用此MCP服务"
            )
        
        # 停用MCP服务
        deactivated = await self.repository.deactivate(integration_id, self.db)
        return self._hide_sensitive_info(deactivated) if deactivated else None
    
    async def update_auth_credentials(self, integration_id: str, auth_type: str, 
                                   credentials: Dict[str, Any], user_id: str) -> Optional[MCPIntegration]:
        """更新认证凭据
        
        Args:
            integration_id: 集成配置ID
            auth_type: 认证类型
            credentials: 认证凭据
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限（需要管理员权限）
        is_admin = await self._check_admin_permission(user_id)
        has_admin_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "admin"
        )
        
        if not (is_admin or has_admin_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限才能更新认证凭据"
            )
        
        # 更新认证凭据
        updated = await self.repository.update_auth_credentials(integration_id, auth_type, credentials, self.db)
        return self._hide_sensitive_info(updated) if updated else None
    
    async def update_resource_configs(self, integration_id: str, new_configs: Dict[str, Any], user_id: str) -> Optional[MCPIntegration]:
        """更新资源配置
        
        Args:
            integration_id: 集成配置ID
            new_configs: 新的资源配置
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此MCP服务的资源配置"
            )
        
        # 更新资源配置
        updated = await self.repository.update_resource_configs(integration_id, new_configs, self.db)
        return self._hide_sensitive_info(updated) if updated else None
    
    async def add_capability(self, integration_id: str, capability: str, user_id: str) -> Optional[MCPIntegration]:
        """添加服务器能力
        
        Args:
            integration_id: 集成配置ID
            capability: 能力名称
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此MCP服务的能力"
            )
        
        # 添加服务器能力
        updated = await self.repository.add_capability(integration_id, capability, self.db)
        return self._hide_sensitive_info(updated) if updated else None
    
    async def remove_capability(self, integration_id: str, capability: str, user_id: str) -> Optional[MCPIntegration]:
        """移除服务器能力
        
        Args:
            integration_id: 集成配置ID
            capability: 能力名称
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None，返回时会隐藏敏感信息
            
        Raises:
            HTTPException: 如果没有权限或集成配置不存在
        """
        # 获取集成配置
        integration = await self.repository.get_by_id(integration_id, self.db)
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "edit"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此MCP服务的能力"
            )
        
        # 移除服务器能力
        updated = await self.repository.remove_capability(integration_id, capability, self.db)
        return self._hide_sensitive_info(updated) if updated else None
    
    async def delete_integration(self, integration_id: str, user_id: str) -> bool:
        """删除MCP服务集成配置
        
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
                detail="MCP服务集成配置不存在"
            )
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此MCP服务集成配置"
            )
        
        # 删除集成配置
        return await self.repository.delete(integration_id, self.db)
    
    def _hide_sensitive_info(self, integration: MCPIntegration) -> MCPIntegration:
        """隐藏敏感信息
        
        Args:
            integration: MCP服务集成配置实例
            
        Returns:
            MCPIntegration: 隐藏敏感信息后的配置实例
        """
        # 创建一个副本
        if integration is None:
            return None
            
        # 直接清空认证凭据字段
        integration.auth_credentials = "********" if integration.auth_credentials else None
        return integration
    
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
