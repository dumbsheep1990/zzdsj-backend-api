"""
MCP服务数据库模型
定义MCP服务、工具、配置和调用历史等数据结构
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
import datetime

from app.utils.database import Base

class MCPServiceConfig(Base):
    """MCP服务配置表"""
    __tablename__ = "mcp_service_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(String(50), nullable=False, default="docker")  # docker, kubernetes, cloud, local
    status = Column(String(20), nullable=False, default="pending")  # pending, running, stopped, error
    
    # Docker相关信息
    image = Column(String(255), nullable=True)
    container = Column(String(255), nullable=True)
    service_port = Column(Integer, nullable=True)
    deploy_directory = Column(String(255), nullable=True)
    
    # 配置信息
    settings = Column(JSON, nullable=True)
    
    # 资源限制
    cpu_limit = Column(String(20), nullable=True)
    memory_limit = Column(String(20), nullable=True)
    disk_limit = Column(String(20), nullable=True)
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    last_started_at = Column(DateTime, nullable=True)
    last_stopped_at = Column(DateTime, nullable=True)
    
    # 关联
    tools = relationship("MCPTool", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MCPServiceConfig(id={self.id}, name='{self.name}', status='{self.status}')>"


class MCPTool(Base):
    """MCP工具表"""
    __tablename__ = "mcp_tool"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("mcp_service_config.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="general")
    is_enabled = Column(Boolean, nullable=False, default=True)
    
    # 工具定义
    schema = Column(JSON, nullable=True)
    examples = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 关联
    service = relationship("MCPServiceConfig", back_populates="tools")
    executions = relationship("MCPToolExecution", back_populates="tool", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("ix_mcp_tool_service_name", "service_id", "tool_name", unique=True),
    )
    
    def __repr__(self):
        return f"<MCPTool(id={self.id}, tool_name='{self.tool_name}', service_id={self.service_id})>"


class MCPToolExecution(Base):
    """MCP工具调用历史表"""
    __tablename__ = "mcp_tool_execution"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    tool_id = Column(Integer, ForeignKey("mcp_tool.id"), nullable=False)
    
    # 调用信息
    parameters = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, success, error
    error_message = Column(Text, nullable=True)
    
    # 上下文信息
    context = Column(JSON, nullable=True)
    agent_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    
    # 时间和性能信息
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)  # 执行时间（毫秒）
    
    # 关联
    tool = relationship("MCPTool", back_populates="executions")
    
    def __repr__(self):
        return f"<MCPToolExecution(id={self.id}, tool_id={self.tool_id}, status='{self.status}')>"


class AgentConfig(Base):
    """Agent配置表"""
    __tablename__ = "agent_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=False, default="llamaindex")  # llamaindex, custom
    model = Column(String(100), nullable=True)
    settings = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 关联
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentConfig(id={self.id}, name='{self.name}', agent_type='{self.agent_type}')>"


class AgentTool(Base):
    """Agent工具配置表"""
    __tablename__ = "agent_tool"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agent_config.id"), nullable=False)
    tool_type = Column(String(50), nullable=False)  # mcp, query_engine, function
    tool_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    
    # 关联信息
    mcp_tool_id = Column(Integer, ForeignKey("mcp_tool.id"), nullable=True)
    settings = Column(JSON, nullable=True)
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # 关联
    agent = relationship("AgentConfig", back_populates="tools")
    
    # 索引
    __table_args__ = (
        Index("ix_agent_tool_agent_name", "agent_id", "tool_name", unique=True),
    )
    
    def __repr__(self):
        return f"<AgentTool(id={self.id}, tool_type='{self.tool_type}', tool_name='{self.tool_name}')>"
