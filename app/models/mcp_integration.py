"""
MCP服务集成模型模块
用于管理MCP服务器连接、认证和资源配置
"""

import uuid
from sqlalchemy import Column, String, JSON, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.utils.database import Base
from typing import Dict, Any, List, Optional

class MCPIntegration(Base):
    """MCP服务集成模型"""
    __tablename__ = 'mcp_integrations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    server_name = Column(String(100), unique=True, nullable=False)  # 服务器名称
    endpoint_url = Column(Text, nullable=False)  # 端点URL
    auth_type = Column(String(50), default='none')  # 认证类型
    auth_credentials = Column(JSON)  # 认证凭据(加密存储)
    resource_configs = Column(JSON)  # 资源配置
    server_capabilities = Column(JSON, default=[])  # 服务器能力
    status = Column(String(50), default='inactive')  # 状态
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "server_name": self.server_name,
            "endpoint_url": self.endpoint_url,
            "auth_type": self.auth_type,
            "auth_credentials": self.auth_credentials,  # 注意：在实际返回中应该隐藏或加密凭据
            "resource_configs": self.resource_configs,
            "server_capabilities": self.server_capabilities,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """转换为安全的字典表示（不包含敏感信息）
        
        Returns:
            Dict[str, Any]: 不含敏感信息的字典表示
        """
        result = self.to_dict()
        if "auth_credentials" in result:
            result["auth_credentials"] = "********" if result["auth_credentials"] else None
        return result
    
    @classmethod
    def create(cls, server_name: str, endpoint_url: str,
               auth_type: str = 'none',
               auth_credentials: Dict[str, Any] = None,
               resource_configs: Dict[str, Any] = None,
               server_capabilities: List[str] = None,
               status: str = 'inactive') -> 'MCPIntegration':
        """创建新的MCP服务集成配置
        
        Args:
            server_name: 服务器名称
            endpoint_url: 端点URL
            auth_type: 认证类型 (默认: 'none')
            auth_credentials: 认证凭据 (可选)
            resource_configs: 资源配置 (可选)
            server_capabilities: 服务器能力 (可选)
            status: 状态 (默认: 'inactive')
            
        Returns:
            MCPIntegration: 创建的MCP服务集成配置实例
        """
        return cls(
            id=str(uuid.uuid4()),
            server_name=server_name,
            endpoint_url=endpoint_url,
            auth_type=auth_type,
            auth_credentials=auth_credentials,
            resource_configs=resource_configs,
            server_capabilities=server_capabilities or [],
            status=status
        )
    
    def activate(self) -> None:
        """激活MCP服务"""
        self.status = 'active'
        self.updated_at = func.now()
    
    def deactivate(self) -> None:
        """停用MCP服务"""
        self.status = 'inactive'
        self.updated_at = func.now()
    
    def update_auth_credentials(self, auth_type: str, credentials: Dict[str, Any]) -> None:
        """更新认证凭据
        
        Args:
            auth_type: 认证类型
            credentials: 认证凭据
        """
        self.auth_type = auth_type
        self.auth_credentials = credentials
        self.updated_at = func.now()
    
    def update_resource_configs(self, new_configs: Dict[str, Any]) -> None:
        """更新资源配置
        
        Args:
            new_configs: 新的资源配置
        """
        self.resource_configs = new_configs
        self.updated_at = func.now()
    
    def add_capability(self, capability: str) -> None:
        """添加服务器能力
        
        Args:
            capability: 能力名称
        """
        if not isinstance(self.server_capabilities, list):
            self.server_capabilities = []
            
        if capability not in self.server_capabilities:
            self.server_capabilities.append(capability)
            self.updated_at = func.now()
    
    def remove_capability(self, capability: str) -> None:
        """移除服务器能力
        
        Args:
            capability: 能力名称
        """
        if isinstance(self.server_capabilities, list) and capability in self.server_capabilities:
            self.server_capabilities.remove(capability)
            self.updated_at = func.now()
