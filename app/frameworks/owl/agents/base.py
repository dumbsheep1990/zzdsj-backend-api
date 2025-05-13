from typing import Any, Dict, List, Optional

try:
    from camel.agents import ChatAgent
    from camel.types import ModelType
except ImportError:
    # 如果尚未安装camel库，提供一个模拟实现
    class ModelType:
        GPT_4 = "gpt-4"
        GPT_3_5_TURBO = "gpt-3.5-turbo"
        
    class ChatAgent:
        def __init__(self, model_type: Any, system_message: str = "", **kwargs):
            self.model_type = model_type
            self.system_message = system_message
            self.kwargs = kwargs
            
        async def chat(self, message: str) -> str:
            return f"模拟回复: {message}"

class BaseAgent:
    """基础智能体，扩展OWL的ChatAgent"""
    
    def __init__(self, model_config: Dict[str, Any], system_message: Optional[str] = None):
        """初始化基础智能体
        
        Args:
            model_config: 模型配置
            system_message: 系统消息
        """
        model_name = model_config.get("model_name", "gpt-4")
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("max_tokens", 1500)
        
        # 映射模型名称到ModelType
        model_mapping = {
            "gpt-4": ModelType.GPT_4,
            "gpt-3.5-turbo": ModelType.GPT_3_5_TURBO,
            # ... 其他模型
        }
        
        model_type = model_mapping.get(model_name, ModelType.GPT_4)
        
        self.agent = ChatAgent(
            model_type=model_type,
            system_message=system_message or "",
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        self.tools = []
        self.model_config = model_config
        self.system_message = system_message
        self.workflow = None
        
    def add_tools(self, tools: List[Any]) -> None:
        """添加工具
        
        Args:
            tools: 要添加的工具列表
        """
        self.tools.extend(tools)
        
    def set_workflow(self, workflow_definition: Dict[str, Any]) -> None:
        """设置工作流定义
        
        Args:
            workflow_definition: 工作流定义
        """
        self.workflow = workflow_definition
        
    async def chat(self, message: str) -> str:
        """与智能体交互
        
        Args:
            message: 用户消息
            
        Returns:
            str: 智能体回复
        """
        # 使用CAMEL的agent进行聊天
        response = await self.agent.chat(message)
        return response
        
    async def run_task(self, task: str, tools: List[Any] = None, **kwargs) -> tuple[str, List[Dict[str, str]], int]:
        """运行任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表，如果为None，则使用已添加的工具
            
        Returns:
            tuple[str, List[Dict[str, str]], int]: (回答, 交互历史, token消耗)
        """
        all_tools = tools or self.tools
        
        # 在实际实现中，这里会处理工具调用和任务执行
        # 此处简化实现，仅使用chat方法获取回答
        response = await self.chat(task)
        
        # 简单模拟聊天历史
        chat_history = [
            {"role": "user", "content": task},
            {"role": "assistant", "content": response}
        ]
        
        # 简单计算token消耗
        token_count = len(task.split()) + len(response.split())
        
        return response, chat_history, token_count
