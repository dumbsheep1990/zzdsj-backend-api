from typing import Any, Dict, List, Optional, Tuple, Union

from app.frameworks.integration.interfaces import IAgentFramework

class FrameworkManager:
    """框架管理器，统一管理不同的智能体框架"""
    
    def __init__(self):
        self.frameworks = {}
        self.default_framework = None
        
    async def register_framework(self, name: str, framework: IAgentFramework, is_default: bool = False) -> None:
        """注册框架
        
        Args:
            name: 框架名称
            framework: 框架实例
            is_default: 是否设置为默认框架
        """
        self.frameworks[name] = framework
        
        # 初始化框架
        await framework.initialize()
        
        if is_default or self.default_framework is None:
            self.default_framework = name
            
    def get_framework(self, name: Optional[str] = None) -> IAgentFramework:
        """获取指定框架实例
        
        Args:
            name: 框架名称，如果为None则返回默认框架
            
        Returns:
            IAgentFramework: 框架实例
        """
        if name and name in self.frameworks:
            return self.frameworks[name]
            
        if not self.default_framework:
            raise ValueError("没有可用的框架")
            
        return self.frameworks[self.default_framework]
        
    async def run_task(self, task: str, framework_name: Optional[str] = None, **kwargs) -> Tuple[str, Any, Dict[str, Any]]:
        """使用指定框架运行任务
        
        Args:
            task: 任务描述
            framework_name: 框架名称
            
        Returns:
            Tuple[str, Any, Dict[str, Any]]: 任务结果
        """
        framework = self.get_framework(framework_name)
        return await framework.run_task(task, **kwargs)
