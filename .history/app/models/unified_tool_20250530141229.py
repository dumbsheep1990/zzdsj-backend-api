"""
统一工具管理模型
用于定义统一工具注册和使用统计的数据库模型
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean, BigInteger, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any
from datetime import date
from app.models.database import Base


class UnifiedTool(Base):
    """统一工具注册模型"""
    __tablename__ = 'unified_tools'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, comment="工具名称")
    description = Column(Text, comment="工具描述")
    tool_type = Column(String(50), nullable=False, comment="工具类型: builtin, custom, mcp, external")
    source_type = Column(String(50), nullable=False, comment="来源类型: internal, mcp_service, external_api")
    source_id = Column(String(36), comment="指向具体的工具源ID")
    category = Column(String(50), comment="工具分类")
    tags = Column(JSON, default=[], comment="工具标签")
    schema = Column(JSON, nullable=False, comment="工具Schema定义")
    config = Column(JSON, default={}, comment="工具配置")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    version = Column(String(20), default='1.0.0', comment="工具版本")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    usage_stats = relationship("ToolUsageStat", back_populates="tool", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "category": self.category,
            "tags": self.tags,
            "schema": self.schema,
            "config": self.config,
            "is_enabled": self.is_enabled,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ToolUsageStat(Base):
    """工具使用统计模型"""
    __tablename__ = 'tool_usage_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_id = Column(String(36), ForeignKey('unified_tools.id', ondelete='CASCADE'), 
                    nullable=False, comment="工具ID")
    user_id = Column(String(36), ForeignKey('users.id'), comment="用户ID")
    execution_count = Column(Integer, default=0, comment="执行次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    error_count = Column(Integer, default=0, comment="错误次数")
    total_execution_time_ms = Column(BigInteger, default=0, comment="总执行时间(毫秒)")
    last_used_at = Column(DateTime, comment="最后使用时间")
    date = Column(Date, nullable=False, default=func.current_date(), comment="统计日期")
    
    # 关系
    tool = relationship("UnifiedTool", back_populates="usage_stats")
    
    # 唯一约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "user_id": self.user_id,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "total_execution_time_ms": self.total_execution_time_ms,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "date": self.date.isoformat() if self.date else None
        }
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
    
    @property
    def avg_execution_time_ms(self) -> float:
        """计算平均执行时间"""
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time_ms / self.execution_count 