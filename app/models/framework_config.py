"""
框架配置模型模块
用于管理AI框架的配置参数和启用状态
"""

import uuid
from sqlalchemy import Column, String, JSON, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from app.utils.core.database import Base
from typing import Dict, Any, List, Optional

class FrameworkConfig(Base):
    """AI框架配置模型"""
    __tablename__ = 'framework_configs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    framework_name = Column(String(50), nullable=False)  # 框架名称(llamaindex, owl, lightrag等)
    settings = Column(JSON, default={})  # 框架设置
    is_enabled = Column(Boolean, default=True)  # 是否启用
    priority = Column(Integer, default=0)  # 优先级
    capabilities = Column(JSON, default=[])  # 支持的能力
    version = Column(String(20))  # 框架版本
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "framework_name": self.framework_name,
            "settings": self.settings,
            "is_enabled": self.is_enabled,
            "priority": self.priority,
            "capabilities": self.capabilities,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, framework_name: str, settings: Dict[str, Any] = None, 
               is_enabled: bool = True, priority: int = 0,
               capabilities: List[str] = None, version: Optional[str] = None) -> 'FrameworkConfig':
        """创建新的框架配置
        
        Args:
            framework_name: 框架名称
            settings: 框架设置 (可选)
            is_enabled: 是否启用 (默认: True)
            priority: 优先级 (默认: 0)
            capabilities: 支持的能力列表 (可选)
            version: 框架版本 (可选)
            
        Returns:
            FrameworkConfig: 创建的框架配置实例
        """
        return cls(
            id=str(uuid.uuid4()),
            framework_name=framework_name,
            settings=settings or {},
            is_enabled=is_enabled,
            priority=priority,
            capabilities=capabilities or [],
            version=version
        )
    
    def enable(self) -> None:
        """启用框架"""
        self.is_enabled = True
        self.updated_at = func.now()
    
    def disable(self) -> None:
        """禁用框架"""
        self.is_enabled = False
        self.updated_at = func.now()
    
    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """更新框架设置
        
        Args:
            new_settings: 新的设置值
        """
        if isinstance(self.settings, dict) and isinstance(new_settings, dict):
            # 合并设置，保留现有未覆盖的值
            self.settings.update(new_settings)
        else:
            # 如果现有设置不是字典或新设置不是字典，则直接替换
            self.settings = new_settings
        
        self.updated_at = func.now()
    
    def add_capability(self, capability: str) -> None:
        """添加框架能力
        
        Args:
            capability: 能力名称
        """
        if not isinstance(self.capabilities, list):
            self.capabilities = []
            
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            self.updated_at = func.now()
    
    def remove_capability(self, capability: str) -> None:
        """移除框架能力
        
        Args:
            capability: 能力名称
        """
        if isinstance(self.capabilities, list) and capability in self.capabilities:
            self.capabilities.remove(capability)
            self.updated_at = func.now()
