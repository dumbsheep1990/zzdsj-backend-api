"""
OWL框架Agent数据库模型
定义与Agent定义、链执行和消息系统集成相关的数据库模型
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.database import Base


class OwlAgentDefinition(Base):
    """OWL Agent定义模型"""
    __tablename__ = "owl_agent_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    model_name = Column(String(255), nullable=False)
    model_provider = Column(String(255))
    system_prompt = Column(Text)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1500)
    top_p = Column(Float)
    top_k = Column(Integer)
    metadata = Column(JSONB, default={})
    prompt_templates = Column(JSONB, default={})
    behaviors = Column(JSONB, default={})
    knowledge = Column(JSONB, default=[])
    version = Column(String(50), default="1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer)
    is_active = Column(Boolean, default=True)

    # 关系
    capabilities = relationship("OwlAgentCapability", back_populates="agent")
    tools = relationship("OwlAgentTool", back_populates="agent")
    chain_steps = relationship("OwlAgentChainStep", back_populates="agent")
    messages = relationship("OwlAgentMessage", back_populates="agent")
    context_compression_config = relationship("AgentContextCompressionConfig", back_populates="agent", uselist=False)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "model_name": self.model_name,
            "model_provider": self.model_provider,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "metadata": self.metadata,
            "prompt_templates": self.prompt_templates,
            "behaviors": self.behaviors,
            "knowledge": self.knowledge,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "is_active": self.is_active
        }


class OwlAgentCapability(Base):
    """OWL Agent能力模型"""
    __tablename__ = "owl_agent_capabilities"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    parameters = Column(JSONB, default={})
    required = Column(Boolean, default=False)
    category = Column(String(100), default="general")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    agent = relationship("OwlAgentDefinition", back_populates="capabilities")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "required": self.required,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class OwlAgentTool(Base):
    """OWL Agent工具模型"""
    __tablename__ = "owl_agent_tools"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="CASCADE"))
    tool_name = Column(String(255), nullable=False)
    tool_description = Column(Text)
    parameters = Column(JSONB, default={})
    is_required = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    agent = relationship("OwlAgentDefinition", back_populates="tools")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "tool_description": self.tool_description,
            "parameters": self.parameters,
            "is_required": self.is_required,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class OwlAgentChainDefinition(Base):
    """OWL Agent链定义模型"""
    __tablename__ = "owl_agent_chain_definitions"

    id = Column(Integer, primary_key=True, index=True)
    chain_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    execution_mode = Column(String(50), default="sequential")
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer)
    is_active = Column(Boolean, default=True)

    # 检查约束
    __table_args__ = (
        CheckConstraint(
            execution_mode.in_(["sequential", "parallel", "conditional"]),
            name="check_execution_mode"
        ),
    )

    # 关系
    steps = relationship("OwlAgentChainStep", back_populates="chain")
    executions = relationship("OwlAgentChainExecution", back_populates="chain")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "execution_mode": self.execution_mode,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "is_active": self.is_active
        }


class OwlAgentChainStep(Base):
    """OWL Agent链步骤模型"""
    __tablename__ = "owl_agent_chain_steps"

    id = Column(Integer, primary_key=True, index=True)
    chain_id = Column(Integer, ForeignKey("owl_agent_chain_definitions.id", ondelete="CASCADE"))
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="CASCADE"))
    agent_name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)
    role = Column(String(100), default="processor")
    input_mapping = Column(JSONB, default={})
    output_mapping = Column(JSONB, default={})
    condition = Column(Text)
    fallback = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    chain = relationship("OwlAgentChainDefinition", back_populates="steps")
    agent = relationship("OwlAgentDefinition", back_populates="chain_steps")
    execution_steps = relationship("OwlAgentChainExecutionStep", back_populates="chain_step")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "chain_id": self.chain_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "position": self.position,
            "role": self.role,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "condition": self.condition,
            "fallback": self.fallback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class OwlAgentChainExecution(Base):
    """OWL Agent链执行记录模型"""
    __tablename__ = "owl_agent_chain_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(255), unique=True, nullable=False)
    chain_id = Column(Integer, ForeignKey("owl_agent_chain_definitions.id", ondelete="SET NULL"))
    status = Column(String(50), default="pending")
    input_message = Column(Text)
    result_content = Column(Text)
    metadata = Column(JSONB, default={})
    context = Column(JSONB, default={})
    error = Column(Text)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer)

    # 检查约束
    __table_args__ = (
        CheckConstraint(
            status.in_(["pending", "running", "completed", "failed", "cancelled"]),
            name="check_execution_status"
        ),
    )

    # 关系
    chain = relationship("OwlAgentChainDefinition", back_populates="executions")
    steps = relationship("OwlAgentChainExecutionStep", back_populates="execution")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "chain_id": self.chain_id,
            "status": self.status,
            "input_message": self.input_message,
            "result_content": self.result_content,
            "metadata": self.metadata,
            "context": self.context,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id
        }


class OwlAgentChainExecutionStep(Base):
    """OWL Agent链执行步骤记录模型"""
    __tablename__ = "owl_agent_chain_execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("owl_agent_chain_executions.id", ondelete="CASCADE"))
    chain_step_id = Column(Integer, ForeignKey("owl_agent_chain_steps.id", ondelete="SET NULL"))
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="SET NULL"))
    agent_name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")
    input = Column(JSONB, default={})
    output = Column(JSONB, default={})
    error = Column(Text)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 检查约束
    __table_args__ = (
        CheckConstraint(
            status.in_(["pending", "running", "completed", "failed", "skipped", "fallback"]),
            name="check_execution_step_status"
        ),
    )

    # 关系
    execution = relationship("OwlAgentChainExecution", back_populates="steps")
    chain_step = relationship("OwlAgentChainStep", back_populates="execution_steps")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "chain_step_id": self.chain_step_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "position": self.position,
            "status": self.status,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class OwlAgentMessage(Base):
    """OWL Agent消息模型"""
    __tablename__ = "owl_agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, nullable=False)
    agent_id = Column(Integer, ForeignKey("owl_agent_definitions.id", ondelete="SET NULL"))
    agent_execution_id = Column(String(255))
    message_type = Column(String(50), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text)
    content_format = Column(String(50), default="text")
    raw_content = Column(JSONB, default={})
    metadata = Column(JSONB, default={})
    parent_message_id = Column(String(255))
    conversation_id = Column(String(255))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer)

    # 关系
    agent = relationship("OwlAgentDefinition", back_populates="messages")
    mappings = relationship("OwlAgentMessageMapping", back_populates="internal_message")
    tool_calls = relationship("OwlAgentToolCall", back_populates="message")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "agent_id": self.agent_id,
            "agent_execution_id": self.agent_execution_id,
            "message_type": self.message_type,
            "role": self.role,
            "content": self.content,
            "content_format": self.content_format,
            "raw_content": self.raw_content,
            "metadata": self.metadata,
            "parent_message_id": self.parent_message_id,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id
        }


class OwlAgentMessageMapping(Base):
    """OWL Agent消息映射模型"""
    __tablename__ = "owl_agent_message_mappings"

    id = Column(Integer, primary_key=True, index=True)
    internal_message_id = Column(Integer, ForeignKey("owl_agent_messages.id", ondelete="CASCADE"))
    external_message_id = Column(String(255))
    mapping_type = Column(String(50), default="direct")
    mapping_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    internal_message = relationship("OwlAgentMessage", back_populates="mappings")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "internal_message_id": self.internal_message_id,
            "external_message_id": self.external_message_id,
            "mapping_type": self.mapping_type,
            "mapping_data": self.mapping_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class OwlAgentToolCall(Base):
    """OWL Agent工具调用记录模型"""
    __tablename__ = "owl_agent_tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("owl_agent_messages.id", ondelete="CASCADE"))
    tool_name = Column(String(255), nullable=False)
    tool_arguments = Column(JSONB, default={})
    tool_result = Column(JSONB, default={})
    status = Column(String(50), default="pending")
    error = Column(Text)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 检查约束
    __table_args__ = (
        CheckConstraint(
            status.in_(["pending", "running", "completed", "failed"]),
            name="check_tool_call_status"
        ),
    )

    # 关系
    message = relationship("OwlAgentMessage", back_populates="tool_calls")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "tool_result": self.tool_result,
            "status": self.status,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
