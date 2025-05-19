"""
LlamaIndex集成仓库模块
提供对LlamaIndex集成配置的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.llamaindex_integration import LlamaIndexIntegration
from app.repositories.base import BaseRepository

class LlamaIndexIntegrationRepository(BaseRepository):
    """LlamaIndex集成仓库类"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> LlamaIndexIntegration:
        """创建LlamaIndex集成配置
        
        Args:
            data: 集成配置数据
            db: 数据库会话
            
        Returns:
            LlamaIndexIntegration: 创建的集成配置实例
        """
        integration = LlamaIndexIntegration(**data)
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def get_by_id(self, integration_id: str, db: Session) -> Optional[LlamaIndexIntegration]:
        """通过ID获取LlamaIndex集成配置
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            Optional[LlamaIndexIntegration]: 查找到的集成配置或None
        """
        return db.query(LlamaIndexIntegration).filter(LlamaIndexIntegration.id == integration_id).first()
    
    async def get_by_index_name(self, index_name: str, db: Session) -> Optional[LlamaIndexIntegration]:
        """通过索引名称获取LlamaIndex集成配置
        
        Args:
            index_name: 索引名称
            db: 数据库会话
            
        Returns:
            Optional[LlamaIndexIntegration]: 查找到的集成配置或None
        """
        return db.query(LlamaIndexIntegration).filter(LlamaIndexIntegration.index_name == index_name).first()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[LlamaIndexIntegration]:
        """获取所有LlamaIndex集成配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[LlamaIndexIntegration]: 集成配置列表
        """
        return db.query(LlamaIndexIntegration)\
            .order_by(desc(LlamaIndexIntegration.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def list_by_knowledge_base(self, knowledge_base_id: str, db: Session) -> List[LlamaIndexIntegration]:
        """获取与指定知识库关联的LlamaIndex集成配置列表
        
        Args:
            knowledge_base_id: 知识库ID
            db: 数据库会话
            
        Returns:
            List[LlamaIndexIntegration]: 集成配置列表
        """
        return db.query(LlamaIndexIntegration)\
            .filter(LlamaIndexIntegration.knowledge_base_id == knowledge_base_id)\
            .order_by(desc(LlamaIndexIntegration.created_at))\
            .all()
    
    async def update(self, integration_id: str, data: Dict[str, Any], db: Session) -> Optional[LlamaIndexIntegration]:
        """更新LlamaIndex集成配置
        
        Args:
            integration_id: 集成配置ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        for key, value in data.items():
            setattr(integration, key, value)
        
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_index_settings(self, integration_id: str, new_settings: Dict[str, Any], db: Session) -> Optional[LlamaIndexIntegration]:
        """更新索引设置
        
        Args:
            integration_id: 集成配置ID
            new_settings: 新的索引设置
            db: 数据库会话
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_index_settings(new_settings)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_storage_context(self, integration_id: str, new_context: Dict[str, Any], db: Session) -> Optional[LlamaIndexIntegration]:
        """更新存储上下文配置
        
        Args:
            integration_id: 集成配置ID
            new_context: 新的存储上下文配置
            db: 数据库会话
            
        Returns:
            Optional[LlamaIndexIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_storage_context(new_context)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def delete(self, integration_id: str, db: Session) -> bool:
        """删除LlamaIndex集成配置
        
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
