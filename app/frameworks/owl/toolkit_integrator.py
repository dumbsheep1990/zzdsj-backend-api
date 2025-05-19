"""
OWL框架工具包集成器
负责将Camel OWL框架的工具包集成到系统中
"""

from typing import Dict, List, Any, Optional
import importlib
import logging
import os
import sys
from pathlib import Path

from app.frameworks.owl.toolkits.base import OwlToolkitManager
from app.frameworks.owl.utils.tool_factory import CustomTool, create_custom_tool
from app.services.owl_tool_service import OwlToolService
from app.utils.config import get_app_settings

logger = logging.getLogger(__name__)

class OwlToolkitIntegrator:
    """OWL框架工具包集成器"""
    
    def __init__(self, tool_service: OwlToolService, toolkit_manager: Optional[OwlToolkitManager] = None):
        """初始化工具包集成器
        
        Args:
            tool_service: OWL工具服务
            toolkit_manager: OWL工具包管理器
        """
        self.tool_service = tool_service
        self.toolkit_manager = toolkit_manager or OwlToolkitManager()
        self.available_toolkits = {
            "ArxivToolkit": "camel.toolkits",
            "AskNewsToolkit": "camel.toolkits",
            "AudioAnalysisToolkit": "camel.toolkits",
            "BrowserToolkit": "camel.toolkits",
            "CodeExecutionToolkit": "camel.toolkits",
            "DalleToolkit": "camel.toolkits",
            "DataCommonsToolkit": "camel.toolkits",
            "ExcelToolkit": "camel.toolkits",
            "FileWriteTool": "camel.toolkits",
            "GitHubToolkit": "camel.toolkits",
            "GoogleMapsToolkit": "camel.toolkits",
            "GoogleScholarToolkit": "camel.toolkits",
            "HumanToolkit": "camel.toolkits",
            "ImageAnalysisToolkit": "camel.toolkits",
            "MathToolkit": "camel.toolkits",
            "MemoryToolkit": "camel.toolkits",
            "NetworkXToolkit": "camel.toolkits",
            "OpenAPIToolkit": "camel.toolkits",
            "SearchToolkit": "camel.toolkits",
            "TerminalToolkit": "camel.toolkits",
            "VideoAnalysisToolkit": "camel.toolkits",
            "WeatherToolkit": "camel.toolkits"
        }
        self.system_user_id = "system"
        self.initialized_toolkits = {}
    
    async def initialize(self) -> None:
        """初始化集成器"""
        # 初始化工具包管理器
        await self.toolkit_manager.initialize()
        
        # 检查数据库中的工具包和工具，确保与可用工具包同步
        await self.sync_available_toolkits()
    
    async def sync_available_toolkits(self) -> None:
        """同步可用的工具包到数据库"""
        for toolkit_name, module_path in self.available_toolkits.items():
            # 检查工具包是否已在数据库中注册
            existing_toolkit = await self.tool_service.get_toolkit_by_name(toolkit_name)
            if not existing_toolkit:
                # 注册工具包
                toolkit_data = {
                    "name": toolkit_name,
                    "description": f"{toolkit_name} 工具包",
                    "is_enabled": True,
                    "config": {"module_path": module_path}
                }
                
                try:
                    await self.tool_service.register_toolkit(toolkit_data, self.system_user_id)
                    logger.info(f"已注册工具包: {toolkit_name}")
                except Exception as e:
                    logger.error(f"注册工具包 {toolkit_name} 失败: {str(e)}")
    
    async def load_toolkit(self, toolkit_name: str) -> Any:
        """加载指定的工具包
        
        Args:
            toolkit_name: 工具包名称
            
        Returns:
            Any: 工具包实例
            
        Raises:
            ImportError: 如果导入工具包失败
            ValueError: 如果工具包不可用
        """
        # 如果工具包已初始化，直接返回
        if toolkit_name in self.initialized_toolkits:
            return self.initialized_toolkits[toolkit_name]
        
        # 检查工具包是否存在
        if toolkit_name not in self.available_toolkits:
            raise ValueError(f"工具包 '{toolkit_name}' 不可用")
        
        # 获取工具包配置
        toolkit_config = await self.tool_service.get_toolkit_by_name(toolkit_name)
        if not toolkit_config or not toolkit_config.is_enabled:
            raise ValueError(f"工具包 '{toolkit_name}' 未配置或未启用")
        
        # 导入工具包
        module_path = self.available_toolkits[toolkit_name]
        try:
            module = importlib.import_module(module_path)
            toolkit_class = getattr(module, toolkit_name)
            
            # 初始化工具包
            toolkit_instance = toolkit_class()
            
            # 注册到管理器
            self.initialized_toolkits[toolkit_name] = toolkit_instance
            
            # 注册工具包中的工具
            await self.register_toolkit_tools(toolkit_name, toolkit_instance)
            
            return toolkit_instance
            
        except ImportError as e:
            logger.error(f"导入工具包 {toolkit_name} 失败: {str(e)}")
            raise ImportError(f"导入工具包失败: {str(e)}")
            
        except AttributeError as e:
            logger.error(f"工具包 {toolkit_name} 不存在: {str(e)}")
            raise ValueError(f"工具包类不存在: {str(e)}")
    
    async def register_toolkit_tools(self, toolkit_name: str, toolkit_instance: Any) -> None:
        """注册工具包中的所有工具
        
        Args:
            toolkit_name: 工具包名称
            toolkit_instance: 工具包实例
        """
        # 获取工具包中的所有工具
        if hasattr(toolkit_instance, 'get_tools'):
            tools = toolkit_instance.get_tools()
            
            for tool in tools:
                # 提取工具信息
                try:
                    if hasattr(tool, 'get_function_name'):
                        function_name = tool.get_function_name()
                    elif hasattr(tool, 'name'):
                        function_name = tool.name
                    else:
                        function_name = str(tool).split(' ')[0]
                    
                    # 工具名称为工具包名.函数名
                    tool_name = f"{toolkit_name}.{function_name}"
                    
                    # 获取工具描述
                    if hasattr(tool, 'get_function_description'):
                        description = tool.get_function_description()
                    elif hasattr(tool, 'description'):
                        description = tool.description
                    else:
                        description = f"{toolkit_name} 中的 {function_name} 工具"
                    
                    # 获取参数模式
                    if hasattr(tool, 'get_openai_function_schema'):
                        parameters_schema = tool.get_openai_function_schema()['parameters']
                    else:
                        parameters_schema = {"type": "object", "properties": {}}
                    
                    # 检查工具是否已在数据库中注册
                    existing_tool = await self.tool_service.get_tool_by_name(tool_name)
                    if not existing_tool:
                        # 注册工具
                        tool_data = {
                            "name": tool_name,
                            "toolkit_name": toolkit_name,
                            "description": description,
                            "function_name": function_name,
                            "parameters_schema": parameters_schema,
                            "is_enabled": True,
                            "requires_api_key": False
                        }
                        
                        await self.tool_service.register_tool(tool_data, self.system_user_id)
                        logger.info(f"已注册工具: {tool_name}")
                        
                except Exception as e:
                    logger.error(f"注册工具失败: {str(e)}")
    
    async def get_custom_tool(self, tool_name: str) -> Optional[CustomTool]:
        """获取自定义工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[CustomTool]: 自定义工具或None
        """
        # 获取工具配置
        tool_config = await self.tool_service.get_tool_by_name(tool_name)
        if not tool_config or not tool_config.is_enabled:
            return None
        
        # 获取工具包
        toolkit_name = tool_config.toolkit_name
        function_name = tool_config.function_name
        
        try:
            # 加载工具包
            toolkit = await self.load_toolkit(toolkit_name)
            
            # 获取工具函数
            if hasattr(toolkit, function_name):
                function = getattr(toolkit, function_name)
                
                # 创建自定义工具
                tool = CustomTool(
                    name=tool_name,
                    description=tool_config.description,
                    function=function,
                    is_async=asyncio.iscoroutinefunction(function)
                )
                
                # 设置函数定义
                if tool_config.parameters_schema:
                    function_def = {
                        "name": function_name,
                        "description": tool_config.description,
                        "parameters": tool_config.parameters_schema
                    }
                    tool.set_function_def(function_def)
                
                return tool
                
            else:
                logger.error(f"工具包 {toolkit_name} 中不存在函数 {function_name}")
                return None
                
        except Exception as e:
            logger.error(f"获取自定义工具 {tool_name} 失败: {str(e)}")
            return None
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
            
        Raises:
            ValueError: 如果工具不存在或未启用
        """
        # 获取自定义工具
        tool = await self.get_custom_tool(tool_name)
        if not tool:
            raise ValueError(f"工具 '{tool_name}' 不存在或未启用")
        
        # 执行工具
        try:
            result = await tool(**parameters)
            return result
            
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {str(e)}")
            return {
                "status": "error",
                "error": f"执行工具失败: {str(e)}"
            }
