"""
压缩策略管理模型
用于定义上下文压缩策略的数据库模型
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any
from app.models.database import Base


class CompressionStrategy(Base):
    """压缩策略模型"""
    __tablename__ = 'compression_strategies'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, comment="策略名称")
    description = Column(Text, comment="策略描述")
    strategy_type = Column(String(50), nullable=False, comment="策略类型: llm, embedding, keyword")
    config = Column(JSON, nullable=False, comment="策略配置")
    is_default = Column(Boolean, default=False, comment="是否为默认策略")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "config": self.config,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 