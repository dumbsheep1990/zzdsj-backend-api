"""
框架配置仓库模块
提供对框架配置的CRUD操作
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.models.framework_config import FrameworkConfig
from app.repositories.base import BaseRepository

class FrameworkConfigRepository(BaseRepository):
    """框架配置仓库类"""
    
    async def create(self, data: Dict[str, Any], db: Session) -> FrameworkConfig:
        """创建框架配置
        
        Args:
            data: 框架配置数据
            db: 数据库会话
            
        Returns:
            FrameworkConfig: 创建的框架配置实例
        """
        framework_config = FrameworkConfig(**data)
        db.add(framework_config)
        db.commit()
        db.refresh(framework_config)
        return framework_config
    
    async def get_by_id(self, config_id: str, db: Session) -> Optional[FrameworkConfig]:
        """通过ID获取框架配置
        
        Args:
            config_id: 框架配置ID
            db: 数据库会话
            
        Returns:
            Optional[FrameworkConfig]: 查找到的框架配置或None
        """
        return db.query(FrameworkConfig).filter(FrameworkConfig.id == config_id).first()
    
    async def get_by_name(self, framework_name: str, db: Session) -> Optional[FrameworkConfig]:
        """通过框架名称获取配置
        
        Args:
            framework_name: 框架名称
            db: 数据库会话
            
        Returns:
            Optional[FrameworkConfig]: 查找到的框架配置或None
        """
        return db.query(FrameworkConfig).filter(FrameworkConfig.framework_name == framework_name).first()
    
    async def list_all(self, skip: int = 0, limit: int = 100, db: Session = None) -> List[FrameworkConfig]:
        """获取所有框架配置列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            db: 数据库会话
            
        Returns:
            List[FrameworkConfig]: 框架配置列表
        """
        return db.query(FrameworkConfig)\
            .order_by(asc(FrameworkConfig.priority))\
            .offset(skip)\
            .limit(limit)\
            .all()
    
    async def list_enabled(self, db: Session) -> List[FrameworkConfig]:
        """获取所有启用的框架配置列表
        
        Args:
            db: 数据库会话
            
        Returns:
            List[FrameworkConfig]: 启用的框架配置列表
        """
        return db.query(FrameworkConfig)\
            .filter(FrameworkConfig.is_enabled == True)\
            .order_by(asc(FrameworkConfig.priority))\
            .all()
    
    async def list_by_capability(self, capability: str, enabled_only: bool = True, db: Session = None) -> List[FrameworkConfig]:
        """获取具有特定能力的框架配置列表
        
        Args:
            capability: 框架能力
            enabled_only: 是否只返回已启用的框架
            db: 数据库会话
            
        Returns:
            List[FrameworkConfig]: 框架配置列表
        """
        query = db.query(FrameworkConfig)\
            .filter(FrameworkConfig.capabilities.contains([capability]))
        
        if enabled_only:
            query = query.filter(FrameworkConfig.is_enabled == True)
            
        return query.order_by(asc(FrameworkConfig.priority)).all()
    
    async def update(self, config_id: str, data: Dict[str, Any], db: Session) -> Optional[FrameworkConfig]:
        """更新框架配置
        
        Args:
            config_id: 框架配置ID
            data: 更新数据
            db: 数据库会话
            
        Returns:
            Optional[FrameworkConfig]: 更新后的框架配置或None
        """
        framework_config = await self.get_by_id(config_id, db)
        if not framework_config:
            return None
        
        for key, value in data.items():
            setattr(framework_config, key, value)
        
        db.commit()
        db.refresh(framework_config)
        return framework_config
    
    async def enable(self, config_id: str, db: Session) -> Optional[FrameworkConfig]:
        """启用框架配置
        
        Args:
            config_id: 框架配置ID
            db: 数据库会话
            
        Returns:
            Optional[FrameworkConfig]: 更新后的框架配置或None
        """
        framework_config = await self.get_by_id(config_id, db)
        if not framework_config:
            return None
        
        framework_config.is_enabled = True
        db.commit()
        db.refresh(framework_config)
        return framework_config
    
    async def disable(self, config_id: str, db: Session) -> Optional[FrameworkConfig]:
        """禁用框架配置
        
        Args:
            config_id: 框架配置ID
            db: 数据库会话
            
        Returns:
            Optional[FrameworkConfig]: 更新后的框架配置或None
        """
        framework_config = await self.get_by_id(config_id, db)
        if not framework_config:
            return None
        
        framework_config.is_enabled = False
        db.commit()
        db.refresh(framework_config)
        return framework_config
    
    async def delete(self, config_id: str, db: Session) -> bool:
        """删除框架配置
        
        Args:
            config_id: 框架配置ID
            db: 数据库会话
            
        Returns:
            bool: 是否成功删除
        """
        framework_config = await self.get_by_id(config_id, db)
        if not framework_config:
            return False
        
        db.delete(framework_config)
        db.commit()
        return True
