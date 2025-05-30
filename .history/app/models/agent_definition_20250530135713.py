from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime
from typing import List, Dict, Any, Optional

# 智能体与工具多对多关系表
agent_tool_association = Table(
    'agent_tool_association',
    Base.metadata,
    Column('agent_definition_id', Integer, ForeignKey('agent_definitions.id')),
    Column('tool_id', Integer, ForeignKey('tools.id')),
    Column('order', Integer),  # 工具调用顺序
    Column('condition', String),  # 条件表达式，决定何时使用此工具
    Column('parameters', JSON)  # 工具参数默认配置
)

class AgentDefinition(Base):
    """智能体定义模型"""
    __tablename__ = 'agent_definitions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    base_agent_type = Column(String, nullable=False)  # 基础智能体类型
    creator_id = Column(Integer, ForeignKey('users.id'))
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    configuration = Column(JSON)  # 智能体特定配置
    system_prompt = Column(String)  # 系统提示词
    
    # 关联的工具
    tools = relationship(
        "Tool", 
        secondary=agent_tool_association,
        order_by="agent_tool_association.c.order",
        collection_class=list
    )
    
    # 工作流定义（如有）
    workflow_definition = Column(JSON)
    
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
            "base_agent_type": self.base_agent_type,
            "creator_id": self.creator_id,
            "is_public": self.is_public,
            "is_system": self.is_system,
            "configuration": self.configuration,
            "system_prompt": self.system_prompt,
            "workflow_definition": self.workflow_definition,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tools": [
                {
                    "id": tool.id,
                    "name": tool.name,
                    "order": self._get_tool_order(tool.id),
                    "condition": self._get_tool_condition(tool.id),
                    "parameters": self._get_tool_parameters(tool.id)
                }
                for tool in self.tools
            ]
        }
    
    def _get_tool_order(self, tool_id: int) -> Optional[int]:
        """获取工具顺序
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Optional[int]: 工具顺序
        """
        # 在实际实现中，这需要通过查询association表
        # 这里是一个简化实现
        return None
    
    def _get_tool_condition(self, tool_id: int) -> Optional[str]:
        """获取工具条件
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Optional[str]: 工具条件
        """
        # 在实际实现中，这需要通过查询association表
        # 这里是一个简化实现
        return None
    
    def _get_tool_parameters(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """获取工具参数
        
        Args:
            tool_id: 工具ID
            
        Returns:
            Optional[Dict[str, Any]]: 工具参数
        """
        # 在实际实现中，这需要通过查询association表
        # 这里是一个简化实现
        return None
