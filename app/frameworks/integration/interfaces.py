from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

class IAgentFramework(ABC):
    """智能体框架通用接口，为不同框架提供统一调用方式"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化框架"""
        pass
        
    @abstractmethod
    async def create_agent(self, agent_type: str, config: Dict[str, Any]) -> Any:
        """创建智能体"""
        pass
        
    @abstractmethod
    async def run_task(self, task: str, tools: List[Any], **kwargs) -> Tuple[str, Any, Dict[str, Any]]:
        """运行任务
        
        Args:
            task: 任务描述
            tools: 可用工具列表
            
        Returns:
            Tuple[str, Any, Dict[str, Any]]: (回答, 交互历史, 其他元数据)
        """
        pass

class IToolkitManager(ABC):
    """工具包管理器接口"""
    
    @abstractmethod
    async def load_toolkit(self, toolkit_name: str, config: Optional[Dict[str, Any]] = None) -> Any:
        """加载指定的工具包"""
        pass
        
    @abstractmethod
    async def get_tools(self, toolkit_name: Optional[str] = None) -> List[Any]:
        """获取指定工具包中的工具，如不指定则返回所有工具"""
        pass
        
    @abstractmethod
    async def register_custom_tool(self, tool: Any) -> None:
        """注册自定义工具"""
        pass

class IKnowledgeRetriever(ABC):
    """知识检索接口"""
    
    @abstractmethod
    async def query(self, query_text: str, **kwargs) -> List[Dict[str, Any]]:
        """从知识库中检索相关内容"""
        pass
        
    @abstractmethod
    async def create_retrieval_tool(self) -> Any:
        """创建检索工具，供智能体使用"""
        pass
