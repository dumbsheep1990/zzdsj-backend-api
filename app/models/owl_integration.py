"""
OWL框架集成模型模块
用于管理OWL框架的社会协作系统、智能体配置和工具包配置
"""

import uuid
from sqlalchemy import Column, String, JSON, Text, DateTime
from sqlalchemy.sql import func
from app.utils.core.database import Base
from typing import Dict, Any, List, Optional

class OwlIntegration(Base):
    """OWL框架集成模型"""
    __tablename__ = 'owl_integrations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    society_name = Column(String(100))  # 社会名称
    agent_configs = Column(JSON, default=[])  # 智能体配置列表
    toolkit_configs = Column(JSON, default={})  # 工具包配置
    workflow_configs = Column(JSON, default={})  # 工作流配置
    mcp_config_path = Column(Text)  # MCP配置路径
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "society_name": self.society_name,
            "agent_configs": self.agent_configs,
            "toolkit_configs": self.toolkit_configs,
            "workflow_configs": self.workflow_configs,
            "mcp_config_path": self.mcp_config_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, society_name: Optional[str] = None,
               agent_configs: List[Dict[str, Any]] = None,
               toolkit_configs: Dict[str, Any] = None,
               workflow_configs: Dict[str, Any] = None,
               mcp_config_path: Optional[str] = None) -> 'OwlIntegration':
        """创建新的OWL框架集成配置
        
        Args:
            society_name: 社会名称 (可选)
            agent_configs: 智能体配置列表 (可选)
            toolkit_configs: 工具包配置 (可选)
            workflow_configs: 工作流配置 (可选)
            mcp_config_path: MCP配置路径 (可选)
            
        Returns:
            OwlIntegration: 创建的OWL框架集成配置实例
        """
        return cls(
            id=str(uuid.uuid4()),
            society_name=society_name,
            agent_configs=agent_configs or [],
            toolkit_configs=toolkit_configs or {},
            workflow_configs=workflow_configs or {},
            mcp_config_path=mcp_config_path
        )
    
    def add_agent_config(self, agent_config: Dict[str, Any]) -> None:
        """添加智能体配置
        
        Args:
            agent_config: 智能体配置
        """
        if not isinstance(self.agent_configs, list):
            self.agent_configs = []
        
        # 检查是否已存在相同名称的智能体配置
        agent_name = agent_config.get('name')
        if agent_name:
            # 移除旧的配置（如果存在）
            self.agent_configs = [cfg for cfg in self.agent_configs 
                                if cfg.get('name') != agent_name]
        
        # 添加新配置
        self.agent_configs.append(agent_config)
        self.updated_at = func.now()
    
    def remove_agent_config(self, agent_name: str) -> bool:
        """移除智能体配置
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            bool: 是否成功移除
        """
        if not isinstance(self.agent_configs, list):
            return False
        
        original_length = len(self.agent_configs)
        self.agent_configs = [cfg for cfg in self.agent_configs 
                            if cfg.get('name') != agent_name]
        
        if len(self.agent_configs) < original_length:
            self.updated_at = func.now()
            return True
        
        return False
    
    def update_toolkit_configs(self, new_configs: Dict[str, Any]) -> None:
        """更新工具包配置
        
        Args:
            new_configs: 新的工具包配置
        """
        if isinstance(self.toolkit_configs, dict) and isinstance(new_configs, dict):
            # 合并配置，保留现有未覆盖的值
            self.toolkit_configs.update(new_configs)
        else:
            # 如果现有配置不是字典或新配置不是字典，则直接替换
            self.toolkit_configs = new_configs
        
        self.updated_at = func.now()
    
    def update_workflow_configs(self, new_configs: Dict[str, Any]) -> None:
        """更新工作流配置
        
        Args:
            new_configs: 新的工作流配置
        """
        if isinstance(self.workflow_configs, dict) and isinstance(new_configs, dict):
            # 合并配置，保留现有未覆盖的值
            self.workflow_configs.update(new_configs)
        else:
            # 如果现有配置不是字典或新配置不是字典，则直接替换
            self.workflow_configs = new_configs
        
        self.updated_at = func.now()
