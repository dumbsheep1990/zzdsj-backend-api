"""
工具链管理模型
用于定义工具链配置和执行记录的数据库模型
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any, List
from app.models.database import Base


class ToolChain(Base):
    """工具链定义模型"""
    __tablename__ = 'tool_chains'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, comment="工具链名称")
    description = Column(Text, comment="工具链描述")
    tools = Column(JSON, nullable=False, comment="工具链配置")
    metadata = Column(JSON, default={}, comment="元数据")
    creator_id = Column(String(36), ForeignKey('users.id'), comment="创建者ID")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    executions = relationship("ToolChainExecution", back_populates="chain", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
            "metadata": self.metadata,
            "creator_id": self.creator_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ToolChainExecution(Base):
    """工具链执行记录模型"""
    __tablename__ = 'tool_chain_executions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chain_id = Column(String(36), ForeignKey('tool_chains.id', ondelete='CASCADE'), 
                     nullable=False, comment="工具链ID")
    input_data = Column(JSON, nullable=False, comment="输入数据")
    output_data = Column(JSON, comment="输出数据")
    status = Column(String(20), nullable=False, default='pending', 
                   comment="执行状态: pending, running, completed, failed")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime, server_default=func.now(), comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    
    # 关系
    chain = relationship("ToolChain", back_populates="executions")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @property
    def execution_time_ms(self) -> int:
        """计算执行时间（毫秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return 0 