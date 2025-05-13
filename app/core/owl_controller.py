from typing import Any, Dict, List, Optional, Tuple
import json

from app.core.agent_manager import AgentManager
from app.frameworks.owl.utils.tool_chain_helper import ToolChainHelper
from app.frameworks.owl.toolkits.base import OwlToolkitManager
from app.config import settings

class OwlController:
    """OWL框架控制器，为API层提供服务"""
    
    def __init__(self):
        """初始化OWL控制器"""
        self.agent_manager = AgentManager()
        self.toolkit_manager = None
        self.tool_chain_helper = None
        self.initialized = False
        
    async def initialize(self) -> None:
        """初始化控制器"""
        if self.initialized:
            return
            
        # 初始化智能体管理器
        await self.agent_manager.initialize()
        
        # 初始化工具包管理器
        self.toolkit_manager = OwlToolkitManager()
        await self.toolkit_manager.initialize(settings.owl.mcp_config_path)
        
        # 初始化工具链助手
        self.tool_chain_helper = ToolChainHelper(self.toolkit_manager)
        await self.tool_chain_helper.initialize()
        
        self.initialized = True
        
    async def process_task(self, task: str, tools: Optional[List[str]] = None, 
                          user_id: Optional[str] = None,
                          model_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理用户任务
        
        Args:
            task: 任务描述
            tools: 工具ID列表
            user_id: 用户ID
            model_config: 用户指定的模型配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if not self.initialized:
            await self.initialize()
            
        # 加载指定的工具
        selected_tools = []
        if tools:
            all_tools = await self.toolkit_manager.get_tools()
            tool_map = {tool.name: tool for tool in all_tools if hasattr(tool, 'name')}
            selected_tools = [tool_map[name] for name in tools if name in tool_map]
        
        # 准备额外参数
        extra_params = {}
        if model_config:
            extra_params["agent_config"] = model_config
            
        # 处理任务
        answer, metadata = await self.agent_manager.process_task(
            task=task,
            use_framework="owl",
            tools=selected_tools,
            **extra_params
        )
        
        # 构造结果
        result = {
            "result": answer,
            "chat_history": metadata.get("chat_history", []),
            "metadata": {k: v for k, v in metadata.items() if k != "chat_history"}
        }
        
        return result
    
    async def create_workflow(self, name: str, description: str) -> Dict[str, Any]:
        """创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        if not self.initialized:
            await self.initialize()
            
        # 创建工作流
        workflow_json = await self.tool_chain_helper.create_workflow_from_description(name, description)
        
        return {
            "name": name,
            "description": description,
            "workflow": json.loads(workflow_json)
        }
    
    async def execute_workflow(self, workflow_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流
        
        Args:
            workflow_name: 工作流名称
            inputs: 输入参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.initialized:
            await self.initialize()
            
        # 执行工作流
        result = await self.tool_chain_helper.execute_workflow(workflow_name, inputs)
        
        return result
    
    async def get_available_tools(self) -> List[Dict[str, str]]:
        """获取所有可用工具
        
        Returns:
            List[Dict[str, str]]: 工具列表
        """
        if not self.initialized:
            await self.initialize()
            
        all_tools = []
        for name, tool_info in self.tool_chain_helper.available_tools.items():
            all_tools.append({
                "name": name,
                "description": tool_info["description"]
            })
            
        return all_tools
    
    async def get_available_workflows(self) -> List[Dict[str, Any]]:
        """获取所有可用工作流
        
        Returns:
            List[Dict[str, Any]]: 工作流列表
        """
        if not self.initialized:
            await self.initialize()
            
        all_workflows = []
        for name, workflow in self.tool_chain_helper.workflows.items():
            all_workflows.append({
                "name": name,
                "description": workflow.get("description", ""),
                "steps_count": len(workflow.get("steps", []))
            })
            
        return all_workflows
