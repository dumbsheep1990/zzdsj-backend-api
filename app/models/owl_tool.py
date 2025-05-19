"""
OWL框架工具模型
定义与OWL框架工具相关的数据模型
"""

from sqlalchemy import Column, String, Boolean, JSON, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base

class OwlTool(Base):
    """OWL框架工具模型"""
    
    __tablename__ = "owl_tools"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    toolkit_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    function_name = Column(String(100), nullable=False)
    parameters_schema = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, default=True)
    requires_api_key = Column(Boolean, default=False)
    api_key_config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    executions = relationship("ToolExecution", back_populates="tool", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OwlTool {self.name}>"


class OwlToolkit(Base):
    """OWL框架工具包模型"""
    
    __tablename__ = "owl_toolkits"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<OwlToolkit {self.name}>"
