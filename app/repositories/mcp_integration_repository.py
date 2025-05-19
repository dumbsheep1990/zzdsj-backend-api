"""
MCP服务集成仓库模块
提供对MCP服务集成配置的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.mcp_integration import MCPIntegration
from app.repositories.base import BaseRepository

class MCPIntegrationRepository(BaseRepository):
    """MCP服务集成仓库类"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> MCPIntegration:
        """创建MCP服务集成配置
        
        Args:
            data: 集成配置数据
            db: 数据库会话
            
        Returns:
            MCPIntegration: 创建的集成配置实例
        """
        integration = MCPIntegration(**data)
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def get_by_id(self, integration_id: str, db: Session) -> Optional[MCPIntegration]:
        """通过ID获取MCP服务集成配置
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 查找到的集成配置或None
        """
        return db.query(MCPIntegration).filter(MCPIntegration.id == integration_id).first()
    
    async def get_by_server_name(self, server_name: str, db: Session) -> Optional[MCPIntegration]:
        """通过服务器名称获取MCP服务集成配置
        
        Args:
            server_name: 服务器名称
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 查找到的集成配置或None
        """
        return db.query(MCPIntegration).filter(MCPIntegration.server_name == server_name).first()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[MCPIntegration]:
        """获取所有MCP服务集成配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[MCPIntegration]: 集成配置列表
        """
        return db.query(MCPIntegration)\
            .order_by(desc(MCPIntegration.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def list_active(self, db: Session) -> List[MCPIntegration]:
        """获取所有活跃的MCP服务集成配置列表
        
        Args:
            db: 数据库会话
            
        Returns:
            List[MCPIntegration]: 活跃的集成配置列表
        """
        return db.query(MCPIntegration)\
            .filter(MCPIntegration.status == 'active')\
            .order_by(desc(MCPIntegration.created_at))\
            .all()
    
    async def update(self, integration_id: str, data: Dict[str, Any], db: Session) -> Optional[MCPIntegration]:
        """更新MCP服务集成配置
        
        Args:
            integration_id: 集成配置ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        for key, value in data.items():
            setattr(integration, key, value)
        
        db.commit()
        db.refresh(integration)
        return integration
    
    async def activate(self, integration_id: str, db: Session) -> Optional[MCPIntegration]:
        """激活MCP服务
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.activate()
        db.commit()
        db.refresh(integration)
        return integration
    
    async def deactivate(self, integration_id: str, db: Session) -> Optional[MCPIntegration]:
        """停用MCP服务
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.deactivate()
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_auth_credentials(self, integration_id: str, auth_type: str, credentials: Dict[str, Any], db: Session) -> Optional[MCPIntegration]:
        """更新认证凭据
        
        Args:
            integration_id: 集成配置ID
            auth_type: 认证类型
            credentials: 认证凭据
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_auth_credentials(auth_type, credentials)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_resource_configs(self, integration_id: str, new_configs: Dict[str, Any], db: Session) -> Optional[MCPIntegration]:
        """更新资源配置
        
        Args:
            integration_id: 集成配置ID
            new_configs: 新的资源配置
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_resource_configs(new_configs)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def add_capability(self, integration_id: str, capability: str, db: Session) -> Optional[MCPIntegration]:
        """添加服务器能力
        
        Args:
            integration_id: 集成配置ID
            capability: 能力名称
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.add_capability(capability)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def remove_capability(self, integration_id: str, capability: str, db: Session) -> Optional[MCPIntegration]:
        """移除服务器能力
        
        Args:
            integration_id: 集成配置ID
            capability: 能力名称
            db: 数据库会话
            
        Returns:
            Optional[MCPIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.remove_capability(capability)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def delete(self, integration_id: str, db: Session) -> bool:
        """删除MCP服务集成配置
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return False
        
        db.delete(integration)
        db.commit()
        return True
