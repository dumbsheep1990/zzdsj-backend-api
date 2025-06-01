"""
MCP服务集成服务模块
处理MCP服务连接、资源访问和认证相关的业务逻辑
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

from app.utils.service_decorators import register_service

from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.mcp_integration import MCPIntegration
# 导入核心业务逻辑层
from core.integrations import MCPIntegrationManager
from app.services.resource_permission_service import ResourcePermissionService
from app.repositories.mcp_integration_repository import MCPIntegrationRepository

@register_service(service_type="mcp", priority="high", description="MCP服务集成服务")
class MCPIntegrationService:
    """MCP服务集成服务类 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, 
                 db: Session = Depends(get_db), 
                 permission_service: ResourcePermissionService = Depends()):
        """初始化MCP服务集成服务
        
        Args:
            db: 数据库会话
            permission_service: 资源权限服务
        """
        self.db = db
        # 使用核心业务逻辑层
        self.mcp_manager = MCPIntegrationManager(db)
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
        # 使用核心层创建集成配置
        result = await self.mcp_manager.create_integration(
            server_name=integration_data.get("server_name"),
            server_type=integration_data.get("server_type"),
            connection_config=integration_data.get("connection_config", {}),
            auth_config=integration_data.get("auth_config"),
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
            "mcp_integration", result["data"]["id"], user_id
        )
        
        # 转换为MCPIntegration对象以保持兼容性
        return MCPIntegration(**result["data"])
    
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
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此MCP服务集成配置"
            )
        
        # 使用核心层获取集成配置
        result = await self.mcp_manager.get_integration(integration_id)
        if not result["success"]:
            return None
        
        # 转换为MCPIntegration对象以保持兼容性
        return MCPIntegration(**result["data"])
    
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
        
        # 使用核心层获取包含完整认证信息的集成配置
        result = await self.mcp_manager.get_integration_with_credentials(integration_id)
        if not result["success"]:
            return None
        
        # 转换为MCPIntegration对象以保持兼容性
        return MCPIntegration(**result["data"])
    
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
        # 使用核心层获取集成配置
        result = await self.mcp_manager.get_integration_by_server_name(server_name)
        if not result["success"]:
            return None
        
        integration_data = result["data"]
        
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_data["id"], user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此MCP服务集成配置"
            )
        
        # 转换为MCPIntegration对象以保持兼容性
        return MCPIntegration(**integration_data)
    
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
            result = await self.mcp_manager.list_integrations(skip=skip, limit=limit)
            if result["success"]:
                return [MCPIntegration(**integration_data) for integration_data in result["data"]["integrations"]]
            return []
        
        # 获取用户有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        mcp_permissions = [p for p in user_permissions if p.resource_type == "mcp_integration"]
        
        if not mcp_permissions:
            return []
        
        # 获取有权限的集成配置
        integration_ids = [p.resource_id for p in mcp_permissions]
        integrations = []
        for integration_id in integration_ids:
            result = await self.mcp_manager.get_integration(integration_id)
            if result["success"]:
                integrations.append(MCPIntegration(**result["data"]))
        
        return integrations
    
    async def list_active_integrations(self, user_id: str) -> List[MCPIntegration]:
        """获取所有活跃的MCP服务集成配置列表，所有结果会隐藏敏感信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[MCPIntegration]: 活跃的集成配置列表
        """
        # 使用核心层获取活跃的集成配置
        result = await self.mcp_manager.list_integrations(is_active=True)
        if not result["success"]:
            return []
        
        all_integrations = result["data"]["integrations"]
        
        # 检查是否为管理员
        is_admin = await self._check_admin_permission(user_id)
        
        # 管理员可以查看所有活跃集成配置
        if is_admin:
            return [MCPIntegration(**integration_data) for integration_data in all_integrations]
        
        # 普通用户只能查看有权限的集成配置
        user_permissions = await self.permission_service.list_user_permissions(user_id)
        mcp_permissions = [p for p in user_permissions if p.resource_type == "mcp_integration"]
        accessible_ids = [p.resource_id for p in mcp_permissions]
        
        accessible_integrations = [
            integration_data for integration_data in all_integrations
            if integration_data["id"] in accessible_ids
        ]
        
        return [MCPIntegration(**integration_data) for integration_data in accessible_integrations]
    
    async def update_integration(
        self, 
        integration_id: str, 
        update_data: Dict[str, Any], 
        user_id: str
    ) -> Optional[MCPIntegration]:
        """更新MCP服务集成配置
        
        Args:
            integration_id: 集成配置ID
            update_data: 更新数据
            user_id: 用户ID
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置实例或None
            
        Raises:
            HTTPException: 如果没有权限或更新失败
        """
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "write"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限修改此MCP服务集成配置"
            )
        
        # 使用核心层更新集成配置
        result = await self.mcp_manager.update_integration(integration_id, update_data)
        
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
        
        # 转换为MCPIntegration对象以保持兼容性
        return MCPIntegration(**result["data"])
    
    async def delete_integration(self, integration_id: str, user_id: str) -> bool:
        """删除MCP服务集成配置
        
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
            "mcp_integration", integration_id, user_id, "admin"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此MCP服务集成配置"
            )
        
        # 使用核心层删除集成配置
        result = await self.mcp_manager.delete_integration(integration_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return True
    
    async def test_connection(self, integration_id: str, user_id: str) -> Dict[str, Any]:
        """测试MCP服务连接
        
        Args:
            integration_id: 集成配置ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 连接测试结果
            
        Raises:
            HTTPException: 如果没有权限
        """
        # 检查权限
        has_permission = await self.permission_service.check_permission(
            "mcp_integration", integration_id, user_id, "read"
        ) or await self._check_admin_permission(user_id)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限测试此MCP服务连接"
            )
        
        # 使用核心层测试连接
        result = await self.mcp_manager.test_connection(integration_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result["data"]
    
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
