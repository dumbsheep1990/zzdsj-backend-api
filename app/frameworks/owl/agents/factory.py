from typing import Any, Dict, List, Optional, Type, Union

from app.config import settings
from app.frameworks.owl.agents.base import BaseAgent
from app.frameworks.owl.agents.planner import PlannerAgent
from app.frameworks.owl.agents.executor import ExecutorAgent
from app.frameworks.owl.society.society import Society

class AgentFactory:
    """智能体工厂，用于构建和配置不同类型的智能体"""
    
    def __init__(self):
        """初始化智能体工厂"""
        self.agent_classes = {
            "base": BaseAgent,
            "planner": PlannerAgent,
            "executor": ExecutorAgent
        }
        
    async def create_agent(self, agent_type: str, config: Optional[Dict[str, Any]] = None) -> BaseAgent:
        """创建指定类型的智能体
        
        Args:
            agent_type: 智能体类型
            config: 智能体配置，可以指定model_name覆盖默认模型
            
        Returns:
            BaseAgent: 创建的智能体实例
        """
        if agent_type not in self.agent_classes:
            raise ValueError(f"不支持的智能体类型: {agent_type}")
        
        # 获取角色对应的模型配置
        role = "default" if agent_type == "base" else agent_type
        agent_config = settings.owl.get_model_config(role, config)
            
        agent_class = self.agent_classes[agent_type]
        
        # 创建智能体实例
        agent = agent_class(agent_config)
        
        return agent
        
    async def create_society(self, society_config: Dict[str, Any]) -> Society:
        """创建智能体社会
        
        Args:
            society_config: 社会配置
            
        Returns:
            Society: 创建的社会实例
        """
        name = society_config.get("name", "默认社会")
        description = society_config.get("description", "")
        
        # 创建社会实例
        society = Society(name, description)
        
        # 添加智能体
        agents_config = society_config.get("agents", [])
        for agent_config in agents_config:
            agent_name = agent_config.get("name")
            agent_type = agent_config.get("type")
            agent_role = agent_config.get("role")
            agent_specific_config = agent_config.get("config", {})
            
            if not agent_name or not agent_type:
                continue
                
            # 创建智能体
            agent = await self.create_agent(agent_type, agent_specific_config)
            
            # 添加到社会
            society.add_agent(agent_name, agent, agent_role)
            
        # 设置工作流
        workflow = society_config.get("workflow")
        if workflow:
            society.set_workflow(workflow)
            
        return society
    
    def register_agent_class(self, agent_type: str, agent_class: Type[BaseAgent], 
                            default_config: Optional[Dict[str, Any]] = None) -> None:
        """注册新的智能体类型
        
        Args:
            agent_type: 智能体类型名称
            agent_class: 智能体类
            default_config: 默认配置
        """
        self.agent_classes[agent_type] = agent_class
        
        if default_config:
            self.default_configs[agent_type] = default_config
