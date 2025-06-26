from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base


class AgentOrchestration(Base):
    """智能体编排配置模型"""
    __tablename__ = "agent_orchestrations"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # 编排配置
    orchestration_config = Column(JSON, nullable=False)  # 前端原始配置
    execution_plan = Column(JSON, nullable=True)         # 解析后的执行计划
    
    # 状态管理
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    assistant = relationship("Assistant", back_populates="orchestrations")
    execution_logs = relationship("OrchestrationExecutionLog", back_populates="orchestration", cascade="all, delete-orphan")


class OrchestrationExecutionLog(Base):
    """编排执行日志模型"""
    __tablename__ = "orchestration_execution_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    orchestration_id = Column(Integer, ForeignKey("agent_orchestrations.id"))
    session_id = Column(String(255), nullable=False, index=True)
    
    # 执行详情
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    execution_trace = Column(JSON, nullable=True)  # 详细执行追踪
    
    # 状态和性能
    status = Column(String(50), nullable=False)  # running, completed, failed
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # 关系
    orchestration = relationship("AgentOrchestration", back_populates="execution_logs") 