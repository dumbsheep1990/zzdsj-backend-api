from typing import Any, Dict, List, Optional, Tuple

from app.frameworks.integration.framework_manager import FrameworkManager
from app.frameworks.integration.agent_factory import AgentFactory
from app.config import settings

class AgentManager:
    """系统智能体管理器，将OWL框架与现有系统集成"""
    
    def __init__(self):
        self.framework_manager = FrameworkManager()
        self.agent_factory = AgentFactory(self.framework_manager)
        self.initialized = False
        
    async def initialize(self) -> None:
        """初始化智能体管理器"""
        if self.initialized:
            return
            
        # 框架搭建阶段，先创建框架类
        # 注册LlamaIndex框架
        from app.frameworks.llamaindex.integration import LlamaIndexFramework
        llamaindex_framework = LlamaIndexFramework()
        await self.framework_manager.register_framework("llamaindex", llamaindex_framework)
        
        # 注册OWL框架
        from app.frameworks.owl.integration import OwlFramework
        owl_framework = OwlFramework()
        await self.framework_manager.register_framework("owl", owl_framework, is_default=True)
        
        self.initialized = True
        
    async def process_task(self, task: str, use_framework: Optional[str] = None, 
                          tools: Optional[List[Any]] = None, **kwargs) -> Tuple[str, Any]:
        """处理用户任务
        
        Args:
            task: 任务描述
            use_framework: 指定使用的框架
            tools: 可用工具列表
            **kwargs: 额外参数，包括:
                - agent_config: 智能体配置，用于指定使用的模型
                - society_config: 社会配置
            
        Returns:
            Tuple[str, Any]: (结果, 元数据)
        """
        if not self.initialized:
            await self.initialize()
            
        # 获取所有可用工具
        all_tools = tools or []
        if not all_tools:
            # 加载系统默认工具
            from app.frameworks.owl.toolkits.base import OwlToolkitManager
            toolkit_manager = OwlToolkitManager()
            await toolkit_manager.initialize()
            all_tools = await toolkit_manager.get_tools()
            
        # 处理任务
        answer, chat_history, metadata = await self.framework_manager.run_task(
            task, 
            framework_name=use_framework,
            tools=all_tools,
            **kwargs
        )
        
        return answer, {"chat_history": chat_history, **metadata}
    
    async def process_task_with_agent(self, task: str, agent: Any, 
                                     parameters: Optional[Dict[str, Any]] = None) -> Tuple[str, Any]:
        """使用指定智能体处理任务
        
        Args:
            task: 任务描述
            agent: 智能体实例
            parameters: 任务参数
            
        Returns:
            Tuple[str, Any]: (结果, 元数据)
        """
        if not self.initialized:
            await self.initialize()
            
        # 获取工具包
        from app.frameworks.owl.toolkits.base import OwlToolkitManager
        toolkit_manager = OwlToolkitManager()
        await toolkit_manager.initialize()
        
        # 处理任务参数
        task_with_params = task
        if parameters:
            # 格式化任务或传递参数
            task_with_params = self._format_task_with_params(task, parameters)
        
        # 使用指定智能体处理任务
        # 框架搭建阶段，使用模拟方法
        # 实际实现时将调用agent.run_task
        try:
            answer, chat_history, metadata = await agent.run_task(
                task_with_params, 
                tools=await toolkit_manager.get_tools()
            )
        except AttributeError:
            # 如果agent没有run_task方法，模拟一个结果
            answer = f"使用自定义智能体处理任务: {task_with_params}"
            chat_history = [{"role": "user", "content": task}, {"role": "assistant", "content": answer}]
            metadata = {"token_count": len(task.split()) + len(answer.split())}
        
        return answer, {"chat_history": chat_history, **metadata}
    
    def _format_task_with_params(self, task: str, parameters: Dict[str, Any]) -> str:
        """根据参数格式化任务
        
        Args:
            task: 原始任务描述
            parameters: 任务参数
            
        Returns:
            str: 格式化后的任务
        """
        # 简单的参数替换实现
        formatted_task = task
        for key, value in parameters.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted_task:
                formatted_task = formatted_task.replace(placeholder, str(value))
        
        return formatted_task
