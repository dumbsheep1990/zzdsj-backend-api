"""
工具执行记录模型模块
用于记录智能体工具的执行历史和结果
"""

import uuid
from sqlalchemy import Column, String, JSON, ForeignKey, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.utils.database import Base
from typing import Dict, Any, Optional

class ToolExecution(Base):
    """工具执行记录模型"""
    __tablename__ = 'tool_executions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_id = Column(String(36), ForeignKey('tools.id'), nullable=False)
    agent_run_id = Column(String(36), ForeignKey('agent_runs.id'))
    user_id = Column(String(36), ForeignKey('users.id'))
    input_params = Column(JSON, nullable=False)  # 输入参数
    output_result = Column(JSON)  # 输出结果
    status = Column(String(50), default='running')  # 状态(成功、失败、运行中)
    error_message = Column(Text)  # 错误信息
    execution_time = Column(Integer)  # 执行时间(毫秒)
    created_at = Column(DateTime, server_default=func.now())  # 创建时间
    completed_at = Column(DateTime)  # 完成时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "agent_run_id": self.agent_run_id,
            "user_id": self.user_id,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def create(cls, tool_id: str, input_params: Dict[str, Any], 
               agent_run_id: Optional[str] = None, user_id: Optional[str] = None) -> 'ToolExecution':
        """创建新的工具执行记录
        
        Args:
            tool_id: 工具ID
            input_params: 输入参数
            agent_run_id: 智能体运行ID (可选)
            user_id: 用户ID (可选)
            
        Returns:
            ToolExecution: 创建的工具执行记录实例
        """
        return cls(
            id=str(uuid.uuid4()),
            tool_id=tool_id,
            agent_run_id=agent_run_id,
            user_id=user_id,
            input_params=input_params,
            status='running'
        )
    
    def complete(self, output_result: Dict[str, Any], execution_time: int) -> None:
        """标记工具执行完成
        
        Args:
            output_result: 输出结果
            execution_time: 执行时间(毫秒)
        """
        self.output_result = output_result
        self.status = 'success'
        self.execution_time = execution_time
        self.completed_at = func.now()
    
    def fail(self, error_message: str, execution_time: Optional[int] = None) -> None:
        """标记工具执行失败
        
        Args:
            error_message: 错误信息
            execution_time: 执行时间(毫秒) (可选)
        """
        self.error_message = error_message
        self.status = 'failed'
        self.execution_time = execution_time
        self.completed_at = func.now()
