"""
LightRAG框架集成仓库模块
提供对LightRAG框架集成配置的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.lightrag_integration import LightRAGIntegration
from app.repositories.base import BaseRepository

class LightRAGIntegrationRepository(BaseRepository):
    """LightRAG框架集成仓库类"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> LightRAGIntegration:
        """创建LightRAG框架集成配置
        
        Args:
            data: 集成配置数据
            db: 数据库会话
            
        Returns:
            LightRAGIntegration: 创建的集成配置实例
        """
        integration = LightRAGIntegration(**data)
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def get_by_id(self, integration_id: str, db: Session) -> Optional[LightRAGIntegration]:
        """通过ID获取LightRAG框架集成配置
        
        Args:
            integration_id: 集成配置ID
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 查找到的集成配置或None
        """
        return db.query(LightRAGIntegration).filter(LightRAGIntegration.id == integration_id).first()
    
    async def get_by_index_name(self, index_name: str, db: Session) -> Optional[LightRAGIntegration]:
        """通过索引名称获取LightRAG框架集成配置
        
        Args:
            index_name: 索引名称
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 查找到的集成配置或None
        """
        return db.query(LightRAGIntegration).filter(LightRAGIntegration.index_name == index_name).first()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[LightRAGIntegration]:
        """获取所有LightRAG框架集成配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[LightRAGIntegration]: 集成配置列表
        """
        return db.query(LightRAGIntegration)\
            .order_by(desc(LightRAGIntegration.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def update(self, integration_id: str, data: Dict[str, Any], db: Session) -> Optional[LightRAGIntegration]:
        """更新LightRAG框架集成配置
        
        Args:
            integration_id: 集成配置ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        for key, value in data.items():
            setattr(integration, key, value)
        
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_document_processor_config(self, integration_id: str, new_config: Dict[str, Any], db: Session) -> Optional[LightRAGIntegration]:
        """更新文档处理器配置
        
        Args:
            integration_id: 集成配置ID
            new_config: 新的文档处理器配置
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_document_processor_config(new_config)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_graph_config(self, integration_id: str, new_config: Dict[str, Any], db: Session) -> Optional[LightRAGIntegration]:
        """更新图谱配置
        
        Args:
            integration_id: 集成配置ID
            new_config: 新的图谱配置
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_graph_config(new_config)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def update_query_engine_config(self, integration_id: str, new_config: Dict[str, Any], db: Session) -> Optional[LightRAGIntegration]:
        """更新查询引擎配置
        
        Args:
            integration_id: 集成配置ID
            new_config: 新的查询引擎配置
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.update_query_engine_config(new_config)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def set_api_key(self, integration_id: str, api_key: str, db: Session) -> Optional[LightRAGIntegration]:
        """设置API密钥
        
        Args:
            integration_id: 集成配置ID
            api_key: API密钥
            db: 数据库会话
            
        Returns:
            Optional[LightRAGIntegration]: 更新后的集成配置或None
        """
        integration = await self.get_by_id(integration_id, db)
        if not integration:
            return None
        
        integration.set_api_key(api_key)
        db.commit()
        db.refresh(integration)
        return integration
    
    async def delete(self, integration_id: str, db: Session) -> bool:
        """删除LightRAG框架集成配置
        
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
