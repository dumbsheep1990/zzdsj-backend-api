"""
OWL框架集成仓库模块
提供对OWL框架集成配置的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.owl_integration import OwlIntegration
from app.repositories.base import BaseRepository

class OwlIntegrationRepository(BaseRepository):
    """OWL框架集成仓库类"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> OwlIntegration:
        """创建OWL框架集成配置
        
        Args:
            data: 集成配置数据
            db: 数据库会话
            
        Returns:
            OwlIntegration: 创建的集成配置实例
        """
        integration = OwlIntegration(**data)
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def get_by_id(self, integration_id: str, db: Session) -> Optional[OwlIntegration]:
        """通过ID获取OWL框架集成配置
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 查找到的集成配置或None
        """
        return db.query(OwlIntegration).filter(OwlIntegration.id == integration_id).first()
    
    async def get_by_society_name(self, society_name: str, db: Session) -> Optional[OwlIntegration]:
        """通过社会名称获取OWL框架集成配置
        
        Args:
            society_name: 社会名称
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 查找到的集成配置或None
        """
        return db.query(OwlIntegration).filter(OwlIntegration.society_name == society_name).first()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[OwlIntegration]:
        """获取所有OWL框架集成配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[OwlIntegration]: 集成配置列表
        """
        return db.query(OwlIntegration)\
            .order_by(desc(OwlIntegration.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def update(self, integration_id: str, data: Dict[str, Any], db: Session) -> Optional[OwlIntegration]:
        """更新OWL框架集成配置
        
        Args:
            integration_id: 集成配置ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        for key, value in data.items():
            setattr(integration, key, value)
        
        db.commit()
        db.refresh(integration)
        return integration
    
    async def add_agent_config(self, integration_id: str, agent_config: Dict[str, Any], db: Session) -> Optional[OwlIntegration]:
        """添加智能体配置
        
        Args:
            integration_id: 集成配置ID
            agent_config: 智能体配置
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.add_agent_config(agent_config)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def remove_agent_config(self, integration_id: str, agent_name: str, db: Session) -> Optional[OwlIntegration]:
        """移除智能体配置
        
        Args:
            integration_id: 集成配置ID
            agent_name: 智能体名称
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        removed = integration.remove_agent_config(agent_name)
        if removed:
            db.commit()
            db.refresh(integration)
        return integration
    
    async def update_toolkit_configs(self, integration_id: str, new_configs: Dict[str, Any], db: Session) -> Optional[OwlIntegration]:
        """更新工具包配置
        
        Args:
            integration_id: 集成配置ID
            new_configs: 新的工具包配置
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_toolkit_configs(new_configs)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_workflow_configs(self, integration_id: str, new_configs: Dict[str, Any], db: Session) -> Optional[OwlIntegration]:
        """更新工作流配置
        
        Args:
            integration_id: 集成配置ID
            new_configs: 新的工作流配置
            db: 数据库会话
            
        Returns:
            Optional[OwlIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_workflow_configs(new_configs)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def delete(self, integration_id: str, db: Session) -> bool:
        """删除OWL框架集成配置
        
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
