from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.utils.database import Base
from datetime import datetime
from typing import Dict, Any, List

class AgentTemplate(Base):
    """智能体模板模型"""
    __tablename__ = 'agent_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)
    base_agent_type = Column(String, nullable=False)
    is_system = Column(Boolean, default=False)
    creator_id = Column(Integer, ForeignKey('users.id'))
    
    # 模板配置
    configuration = Column(JSON)
    system_prompt_template = Column(String)
    
    # 推荐工具
    recommended_tools = Column(JSON)
    
    # 示例工作流
    example_workflow = Column(JSON)
    
    # 使用说明
    usage_guide = Column(String)
    
    # 创建和更新时间
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat(), onupdate=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "base_agent_type": self.base_agent_type,
            "is_system": self.is_system,
            "creator_id": self.creator_id,
            "configuration": self.configuration,
            "system_prompt_template": self.system_prompt_template,
            "recommended_tools": self.recommended_tools,
            "example_workflow": self.example_workflow,
            "usage_guide": self.usage_guide,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
