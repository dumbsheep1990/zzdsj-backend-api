"""
智能体记忆系统 - 数据模型

定义记忆系统的数据库模型。
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.utils.core.database import Base

class AgentMemory(Base):
    """智能体记忆绑定关系表"""
    __tablename__ = "agent_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True, nullable=False, 
                    comment="智能体ID")
    memory_id = Column(String, index=True, nullable=False, 
                     comment="记忆ID")
    created_at = Column(DateTime, default=datetime.utcnow,
                      comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
                      comment="更新时间")
    
    def __repr__(self):
        return f"<AgentMemory(agent_id='{self.agent_id}', memory_id='{self.memory_id}')>"
