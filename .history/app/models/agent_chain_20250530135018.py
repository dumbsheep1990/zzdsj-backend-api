"""
Agent调用链管理模型
用于定义Agent链配置、执行记录和执行步骤的数据库模型
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSONB, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any, List
from app.utils.database import Base


class AgentChain(Base):
    """Agent调用链配置模型"""
    __tablename__ = 'agent_chains'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, comment="调用链名称")
    description = Column(Text, comment="调用链描述")
    execution_mode = Column(String(20), nullable=False, default='sequential', 
                          comment="执行模式: sequential, parallel, conditional")
    agents = Column(JSONB, nullable=False, comment="Agent引用列表")
    conditions = Column(JSONB, comment="条件执行配置，仅conditional模式使用")
    metadata = Column(JSONB, default={}, comment="元数据")
    creator_id = Column(String(36), ForeignKey('users.id'), comment="创建者ID")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    executions = relationship("AgentChainExecution", back_populates="chain", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "execution_mode": self.execution_mode,
            "agents": self.agents,
            "conditions": self.conditions,
            "metadata": self.metadata,
            "creator_id": self.creator_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AgentChainExecution(Base):
    """Agent调用链执行记录模型"""
    __tablename__ = 'agent_chain_executions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chain_id = Column(String(36), ForeignKey('agent_chains.id', ondelete='CASCADE'), 
                     nullable=False, comment="调用链ID")
    user_id = Column(String(36), ForeignKey('users.id'), comment="用户ID")
    input_data = Column(JSONB, nullable=False, comment="输入数据")
    output_data = Column(JSONB, comment="输出数据")
    status = Column(String(20), nullable=False, default='pending', 
                   comment="执行状态: pending, running, completed, failed")
    progress = Column(Integer, default=0, comment="进度百分比")
    error_message = Column(Text, comment="错误信息")
    context = Column(JSONB, default={}, comment="上下文信息")
    started_at = Column(DateTime, server_default=func.now(), comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    
    # 关系
    chain = relationship("AgentChain", back_populates="executions")
    steps = relationship("AgentChainExecutionStep", back_populates="execution", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "user_id": self.user_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "context": self.context,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class AgentChainExecutionStep(Base):
    """Agent执行步骤模型"""
    __tablename__ = 'agent_chain_execution_steps'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(36), ForeignKey('agent_chain_executions.id', ondelete='CASCADE'), 
                         nullable=False, comment="执行记录ID")
    agent_id = Column(Integer, nullable=False, comment="Agent ID")
    step_order = Column(Integer, nullable=False, comment="步骤顺序")
    status = Column(String(20), nullable=False, default='pending', 
                   comment="步骤状态: pending, running, completed, failed")
    input_data = Column(JSONB, comment="步骤输入数据")
    output_data = Column(JSONB, comment="步骤输出数据")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime, server_default=func.now(), comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    
    # 关系
    execution = relationship("AgentChainExecution", back_populates="steps")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "step_order": self.step_order,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        } 