"""
上下文压缩模型模块
定义与上下文压缩功能相关的数据库模型
"""

import uuid
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.utils.core.database import Base


class ContextCompressionTool(Base):
    """上下文压缩工具模型"""
    __tablename__ = "context_compression_tools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    compression_method = Column(String(50), nullable=False, default='tree_summarize')
    is_enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "compression_method": self.compression_method,
            "is_enabled": self.is_enabled,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AgentContextCompressionConfig(Base):
    """智能体上下文压缩配置模型"""
    __tablename__ = "agent_context_compression_config"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    method = Column(String(50), nullable=False, default='tree_summarize')
    top_n = Column(Integer, nullable=False, default=5)
    num_children = Column(Integer, nullable=False, default=2)
    streaming = Column(Boolean, nullable=False, default=False)
    rerank_model = Column(String(255), default='BAAI/bge-reranker-base')
    max_tokens = Column(Integer)
    temperature = Column(Float, nullable=False, default=0.1)
    store_original = Column(Boolean, nullable=False, default=False)
    use_message_format = Column(Boolean, nullable=False, default=True)
    phase = Column(String(50), nullable=False, default='final')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    agent = relationship("OwlAgentDefinition", back_populates="context_compression_config")
    executions = relationship("ContextCompressionExecution", back_populates="compression_config")
    
    # 检查约束
    __table_args__ = (
        CheckConstraint(
            method.in_(["tree_summarize", "compact_and_refine"]),
            name="check_compression_method"
        ),
        CheckConstraint(
            phase.in_(["retrieval", "final"]),
            name="check_compression_phase"
        ),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "enabled": self.enabled,
            "method": self.method,
            "top_n": self.top_n,
            "num_children": self.num_children,
            "streaming": self.streaming,
            "rerank_model": self.rerank_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "store_original": self.store_original,
            "use_message_format": self.use_message_format,
            "phase": self.phase,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ContextCompressionExecution(Base):
    """上下文压缩执行记录模型"""
    __tablename__ = "context_compression_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(36), nullable=False, unique=True)
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="SET NULL"))
    compression_config_id = Column(Integer, ForeignKey("agent_context_compression_config.id", ondelete="SET NULL"))
    query = Column(Text)
    original_content_length = Column(Integer, nullable=False, default=0)
    compressed_content_length = Column(Integer, nullable=False, default=0)
    compression_ratio = Column(Float)
    source_count = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    status = Column(String(50), nullable=False, default='success')
    error = Column(Text)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    agent = relationship("OwlAgentDefinition")
    compression_config = relationship("AgentContextCompressionConfig", back_populates="executions")
    
    # 检查约束
    __table_args__ = (
        CheckConstraint(
            status.in_(["success", "failed", "partial"]),
            name="check_compression_status"
        ),
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "compression_config_id": self.compression_config_id,
            "query": self.query,
            "original_content_length": self.original_content_length,
            "compressed_content_length": self.compressed_content_length,
            "compression_ratio": self.compression_ratio,
            "source_count": self.source_count,
            "execution_time_ms": self.execution_time_ms,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
