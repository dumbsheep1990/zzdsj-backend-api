from typing import Any, Dict, Optional

from app.frameworks.integration.framework_manager import FrameworkManager

class AgentFactory:
    """智能体工厂，统一创建智能体"""
    
    def __init__(self, framework_manager: FrameworkManager):
        """初始化工厂
        
        Args:
            framework_manager: 框架管理器
        """
        self.framework_manager = framework_manager
        
    async def create_agent(self, agent_type: str, config: Optional[Dict[str, Any]] = None, 
                          framework_name: Optional[str] = None) -> Any:
        """创建智能体
        
        Args:
            agent_type: 智能体类型
            config: 智能体配置
            framework_name: 框架名称
            
        Returns:
            Any: 创建的智能体
        """
        framework = self.framework_manager.get_framework(framework_name)
        return await framework.create_agent(agent_type, config or {})
