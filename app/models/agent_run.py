from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Float
from app.utils.database import Base
from datetime import datetime
from typing import Dict, Any, List

class AgentRun(Base):
    """智能体运行记录模型"""
    __tablename__ = 'agent_runs'
    
    id = Column(Integer, primary_key=True)
    agent_definition_id = Column(Integer, ForeignKey('agent_definitions.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    task = Column(String, nullable=False)  # 输入任务
    result = Column(String)  # 运行结果
    
    # 运行状态和指标
    status = Column(String, default="pending")  # pending, running, completed, failed
    start_time = Column(String)
    end_time = Column(String)
    duration = Column(Float)  # 运行时长（秒）
    
    # 工具使用记录
    tool_calls = Column(JSON)  # 工具调用记录
    
    # 错误信息（如有）
    error = Column(String)
    
    # 元数据
    metadata = Column(JSON)
    
    # 创建时间
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "agent_definition_id": self.agent_definition_id,
            "user_id": self.user_id,
            "task": self.task,
            "result": self.result,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "tool_calls": self.tool_calls,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
