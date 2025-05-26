"""
上下文压缩仓库模块
提供对上下文压缩相关数据模型的存取操作
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.context_compression import (
    ContextCompressionTool,
    AgentContextCompressionConfig,
    ContextCompressionExecution
)


class ContextCompressionToolRepository:
    """上下文压缩工具仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, tool_id: int) -> Optional[ContextCompressionTool]:
        """根据ID获取压缩工具"""
        return self.db.query(ContextCompressionTool).filter(ContextCompressionTool.id == tool_id).first()
    
    def get_by_name(self, name: str) -> Optional[ContextCompressionTool]:
        """根据名称获取压缩工具"""
        return self.db.query(ContextCompressionTool).filter(ContextCompressionTool.name == name).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ContextCompressionTool]:
        """获取所有压缩工具"""
        return self.db.query(ContextCompressionTool).offset(skip).limit(limit).all()
    
    def get_enabled(self) -> List[ContextCompressionTool]:
        """获取所有启用的压缩工具"""
        return self.db.query(ContextCompressionTool).filter(ContextCompressionTool.is_enabled == True).all()
    
    def create(self, tool: Dict[str, Any]) -> ContextCompressionTool:
        """创建新压缩工具"""
        db_tool = ContextCompressionTool(**tool)
        self.db.add(db_tool)
        self.db.commit()
        self.db.refresh(db_tool)
        return db_tool
    
    def update(self, tool_id: int, tool_data: Dict[str, Any]) -> Optional[ContextCompressionTool]:
        """更新压缩工具"""
        db_tool = self.get_by_id(tool_id)
        if not db_tool:
            return None
        
        for key, value in tool_data.items():
            if hasattr(db_tool, key):
                setattr(db_tool, key, value)
        
        self.db.commit()
        self.db.refresh(db_tool)
        return db_tool
    
    def delete(self, tool_id: int) -> bool:
        """删除压缩工具"""
        db_tool = self.get_by_id(tool_id)
        if not db_tool:
            return False
        
        self.db.delete(db_tool)
        self.db.commit()
        return True


class AgentCompressionConfigRepository:
    """智能体压缩配置仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, config_id: int) -> Optional[AgentContextCompressionConfig]:
        """根据ID获取压缩配置"""
        return self.db.query(AgentContextCompressionConfig).filter(AgentContextCompressionConfig.id == config_id).first()
    
    def get_by_agent_id(self, agent_id: int) -> Optional[AgentContextCompressionConfig]:
        """根据智能体ID获取压缩配置"""
        return self.db.query(AgentContextCompressionConfig).filter(AgentContextCompressionConfig.agent_id == agent_id).first()
    
    def create(self, config: Dict[str, Any]) -> AgentContextCompressionConfig:
        """创建新压缩配置"""
        db_config = AgentContextCompressionConfig(**config)
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        return db_config
    
    def update(self, config_id: int, config_data: Dict[str, Any]) -> Optional[AgentContextCompressionConfig]:
        """更新压缩配置"""
        db_config = self.get_by_id(config_id)
        if not db_config:
            return None
        
        for key, value in config_data.items():
            if hasattr(db_config, key):
                setattr(db_config, key, value)
        
        self.db.commit()
        self.db.refresh(db_config)
        return db_config
    
    def delete(self, config_id: int) -> bool:
        """删除压缩配置"""
        db_config = self.get_by_id(config_id)
        if not db_config:
            return False
        
        self.db.delete(db_config)
        self.db.commit()
        return True
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[AgentContextCompressionConfig]:
        """获取所有压缩配置"""
        return self.db.query(AgentContextCompressionConfig).offset(skip).limit(limit).all()
    
    def get_enabled(self) -> List[AgentContextCompressionConfig]:
        """获取所有启用的压缩配置"""
        return self.db.query(AgentContextCompressionConfig).filter(AgentContextCompressionConfig.enabled == True).all()


class CompressionExecutionRepository:
    """压缩执行记录仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, execution_id: int) -> Optional[ContextCompressionExecution]:
        """根据ID获取执行记录"""
        return self.db.query(ContextCompressionExecution).filter(ContextCompressionExecution.id == execution_id).first()
    
    def get_by_execution_id(self, execution_id: str) -> Optional[ContextCompressionExecution]:
        """根据执行ID获取执行记录"""
        return self.db.query(ContextCompressionExecution).filter(ContextCompressionExecution.execution_id == execution_id).first()
    
    def get_by_agent_id(self, agent_id: int, skip: int = 0, limit: int = 100) -> List[ContextCompressionExecution]:
        """根据智能体ID获取执行记录"""
        return self.db.query(ContextCompressionExecution).filter(
            ContextCompressionExecution.agent_id == agent_id
        ).order_by(ContextCompressionExecution.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_by_config_id(self, config_id: int, skip: int = 0, limit: int = 100) -> List[ContextCompressionExecution]:
        """根据配置ID获取执行记录"""
        return self.db.query(ContextCompressionExecution).filter(
            ContextCompressionExecution.compression_config_id == config_id
        ).order_by(ContextCompressionExecution.created_at.desc()).offset(skip).limit(limit).all()
    
    def create(self, execution_data: Dict[str, Any]) -> ContextCompressionExecution:
        """创建新执行记录"""
        # 确保有执行ID
        if 'execution_id' not in execution_data:
            execution_data['execution_id'] = str(uuid4())
            
        db_execution = ContextCompressionExecution(**execution_data)
        self.db.add(db_execution)
        self.db.commit()
        self.db.refresh(db_execution)
        return db_execution
    
    def update(self, execution_id: str, execution_data: Dict[str, Any]) -> Optional[ContextCompressionExecution]:
        """更新执行记录"""
        db_execution = self.get_by_execution_id(execution_id)
        if not db_execution:
            return None
        
        for key, value in execution_data.items():
            if hasattr(db_execution, key):
                setattr(db_execution, key, value)
        
        self.db.commit()
        self.db.refresh(db_execution)
        return db_execution
    
    def delete(self, execution_id: str) -> bool:
        """删除执行记录"""
        db_execution = self.get_by_execution_id(execution_id)
        if not db_execution:
            return False
        
        self.db.delete(db_execution)
        self.db.commit()
        return True
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ContextCompressionExecution]:
        """获取所有执行记录"""
        return self.db.query(ContextCompressionExecution).order_by(
            ContextCompressionExecution.created_at.desc()
        ).offset(skip).limit(limit).all()
