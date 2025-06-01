from typing import Dict, Any, List, Optional, Type
import importlib
from app.models.agent_definition import AgentDefinition
from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.repositories.tool_repository import ToolRepository
from app.frameworks.owl.agents.base import BaseAgent
from app.frameworks.owl.utils.tool_factory import create_custom_tool
from app.utils.core.database import get_db
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class AgentBuilder:
    """动态智能体构建器，根据定义构建可执行的智能体实例"""
    
    def __init__(self):
        self.agent_definition_repo = AgentDefinitionRepository()
        self.tool_repo = ToolRepository()
        
    async def build_from_definition(self, definition_id: int, db: Optional[Session] = None) -> BaseAgent:
        """从定义构建智能体实例
        
        Args:
            definition_id: 智能体定义ID
            db: 数据库会话
            
        Returns:
            BaseAgent: 智能体实例
            
        Raises:
            ValueError: 定义不存在或构建失败
        """
        if db is None:
            db = next(get_db())
            
        # 获取智能体定义
        definition = await self.agent_definition_repo.get_by_id(definition_id, db)
        if not definition:
            raise ValueError(f"智能体定义 {definition_id} 不存在")
            
        return await self.build_from_model(definition, db)
        
    async def build_from_model(self, definition: AgentDefinition, db: Optional[Session] = None) -> BaseAgent:
        """从模型构建智能体
        
        Args:
            definition: 智能体定义
            db: 数据库会话
            
        Returns:
            BaseAgent: 智能体实例
            
        Raises:
            ValueError: 构建失败
        """
        try:
            # 加载基础智能体类
            agent_cls = self._load_agent_class(definition.base_agent_type)
            
            # 创建智能体实例
            agent_config = definition.configuration or {}
            agent = agent_cls(**agent_config)
            
            # 设置系统提示词
            if hasattr(agent, "set_system_prompt") and definition.system_prompt:
                agent.set_system_prompt(definition.system_prompt)
                
            # 加载和配置工具
            if definition.tools:
                tools = await self._load_tools(definition, db)
                if hasattr(agent, "set_tools") and tools:
                    agent.set_tools(tools)
                    
            # 配置工作流
            if hasattr(agent, "set_workflow") and definition.workflow_definition:
                agent.set_workflow(definition.workflow_definition)
                
            return agent
            
        except Exception as e:
            logger.error(f"构建智能体实例失败: {str(e)}", exc_info=True)
            raise ValueError(f"构建智能体实例失败: {str(e)}")
            
    def _load_agent_class(self, agent_type: str) -> Type[BaseAgent]:
        """加载智能体类
        
        Args:
            agent_type: 智能体类型
            
        Returns:
            Type[BaseAgent]: 智能体类
            
        Raises:
            ValueError: 类型不存在或不是BaseAgent子类
        """
        try:
            # 解析模块路径和类名
            if "." not in agent_type:
                # 使用默认路径
                module_path = f"app.frameworks.owl.agents.{agent_type.lower()}"
                class_name = f"{agent_type}Agent"
            else:
                # 完整路径
                module_path, class_name = agent_type.rsplit(".", 1)
                
            # 动态导入
            module = importlib.import_module(module_path)
            agent_cls = getattr(module, class_name)
            
            # 确保是BaseAgent子类
            if not issubclass(agent_cls, BaseAgent):
                raise ValueError(f"{agent_type} 不是 BaseAgent 的子类")
                
            return agent_cls
            
        except (ImportError, AttributeError) as e:
            logger.error(f"加载智能体类 {agent_type} 失败: {str(e)}")
            raise ValueError(f"找不到智能体类型 {agent_type}")
            
    async def _load_tools(self, definition: AgentDefinition, db: Session) -> List[Any]:
        """加载工具
        
        Args:
            definition: 智能体定义
            db: 数据库会话
            
        Returns:
            List[Any]: 工具实例列表
        """
        tools = []
        
        for tool_config in definition.tools:
            tool_model = await self.tool_repo.get_by_id(tool_config.id, db)
            if not tool_model:
                logger.warning(f"跳过不存在的工具 {tool_config.id}")
                continue
                
            try:
                # 获取工具实例
                tool_instance = self._instantiate_tool(tool_model)
                
                # 配置工具参数
                if tool_config.parameters:
                    tool_instance = self._configure_tool_parameters(
                        tool_instance, tool_config.parameters
                    )
                    
                # 添加到工具列表
                tools.append(tool_instance)
                
            except Exception as e:
                logger.error(f"加载工具 {tool_model.name} 失败: {str(e)}", exc_info=True)
                
        # 按顺序排序
        tools.sort(key=lambda t: getattr(t, "_order", 0))
        
        return tools
        
    def _instantiate_tool(self, tool_model: Any) -> Any:
        """实例化工具
        
        Args:
            tool_model: 工具模型
            
        Returns:
            Any: 工具实例
        """
        try:
            # 解析模块路径和类名
            module_path = tool_model.module_path
            class_name = tool_model.class_name
            
            # 动态导入
            module = importlib.import_module(module_path)
            tool_cls = getattr(module, class_name)
            
            # 创建实例
            return tool_cls()
            
        except Exception as e:
            logger.error(f"实例化工具失败: {str(e)}", exc_info=True)
            raise ValueError(f"实例化工具失败: {str(e)}")
            
    def _configure_tool_parameters(self, tool: Any, parameters: Dict[str, Any]) -> Any:
        """配置工具参数
        
        Args:
            tool: 工具实例
            parameters: 参数配置
            
        Returns:
            Any: 配置后的工具实例
        """
        if hasattr(tool, "configure"):
            # 如果工具有配置方法，使用它
            tool.configure(**parameters)
        else:
            # 否则，直接设置属性
            for key, value in parameters.items():
                if hasattr(tool, key):
                    setattr(tool, key, value)
                    
        return tool
