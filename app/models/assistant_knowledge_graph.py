"""
助手知识图谱关联模型
用于将助手与知识图谱进行关联
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from app.models.database import Base


class AssistantKnowledgeGraph(Base):
    """助手与知识图谱关联"""
    __tablename__ = "assistant_knowledge_graphs"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, index=True)
    graph_id = Column(String(255), nullable=False)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    assistant = relationship("Assistant", back_populates="knowledge_graphs")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "assistant_id": self.assistant_id,
            "graph_id": self.graph_id,
            "priority": self.priority,
            "is_active": self.is_active,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
