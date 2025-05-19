"""
OWL智能体工具管理器
负责工具的注册、初始化和执行管理
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Type, Callable, Set
from sqlalchemy.orm import Session

from .config import owl_tools_settings, is_tool_enabled
from .toolkits.base import BaseTool

logger = logging.getLogger(__name__)


class OwlToolManager:
    """OWL工具管理器
    
    负责OWL框架中所有工具的生命周期管理，包括：
    1. 工具注册与发现
    2. 工具配置加载
    3. 工具初始化与实例化
    4. 工具执行与并发控制
    5. 工具结果收集与错误处理
    """
    
    def __init__(self):
        """初始化工具管理器"""
        self.tools: Dict[str, BaseTool] = {}
        self.tool_classes: Dict[str, Type[BaseTool]] = {}
        self.settings = owl_tools_settings
        self._semaphore = asyncio.Semaphore(self.settings.max_concurrent)
        
    def register_tool_class(self, tool_name: str, tool_class: Type[BaseTool]) -> None:
        """注册工具类
        
        Args:
            tool_name (str): 工具名称
            tool_class (Type[BaseTool]): 工具类
        """
        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"工具类 {tool_class.__name__} 必须继承自 BaseTool")
            
        self.tool_classes[tool_name] = tool_class
        logger.info(f"已注册工具类: {tool_name}")
        
    async def initialize_tool(self, tool_name: str, db: Session) -> Optional[BaseTool]:
        """初始化并获取工具实例
        
        Args:
            tool_name (str): 工具名称
            db (Session): 数据库会话
            
        Returns:
            Optional[BaseTool]: 工具实例，如果工具未启用或不存在则返回None
        """
        # 检查工具是否启用
        if not is_tool_enabled(tool_name):
            logger.warning(f"工具 {tool_name} 未启用")
            return None
            
        # 如果工具已初始化，直接返回
        if tool_name in self.tools:
            return self.tools[tool_name]
            
        # 获取工具类并实例化
        tool_class = self.tool_classes.get(tool_name)
        if not tool_class:
            logger.error(f"未找到工具类: {tool_name}")
            return None
            
        try:
            # 实例化工具
            tool_instance = tool_class()
            
            # 初始化工具
            if hasattr(tool_instance, 'initialize'):
                await tool_instance.initialize(db)
                
            # 注册工具实例
            self.tools[tool_name] = tool_instance
            logger.info(f"已初始化工具: {tool_name}")
            
            return tool_instance
        except Exception as e:
            logger.error(f"初始化工具 {tool_name} 失败: {str(e)}")
            return None
    
    async def initialize_all_tools(self, db: Session) -> Dict[str, BaseTool]:
        """初始化所有已注册的工具
        
        Args:
            db (Session): 数据库会话
            
        Returns:
            Dict[str, BaseTool]: 初始化成功的工具实例字典
        """
        if not self.settings.enabled:
            logger.warning("OWL工具系统未启用")
            return {}
            
        initialized_tools = {}
        
        for tool_name in self.tool_classes.keys():
            tool = await self.initialize_tool(tool_name, db)
            if tool:
                initialized_tools[tool_name] = tool
                
        return initialized_tools
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例
        
        Args:
            tool_name (str): 工具名称
            
        Returns:
            Optional[BaseTool]: 工具实例，如果不存在则返回None
        """
        return self.tools.get(tool_name)
    
    def list_available_tools(self) -> List[str]:
        """列出所有可用工具
        
        Returns:
            List[str]: 可用工具名称列表
        """
        return list(self.tools.keys())
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具
        
        Args:
            tool_name (str): 工具名称
            **kwargs: 传递给工具的参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        if not self.settings.enabled:
            return {"status": "error", "message": "OWL工具系统未启用"}
            
        tool = self.get_tool(tool_name)
        if not tool:
            return {"status": "error", "message": f"未找到工具: {tool_name}"}
        
        # 使用信号量控制并发
        async with self._semaphore:
            try:
                # 创建执行任务并添加超时控制
                result = await asyncio.wait_for(
                    tool.execute(**kwargs),
                    timeout=self.settings.timeout_seconds
                )
                return {"status": "success", "data": result}
            except asyncio.TimeoutError:
                logger.error(f"工具 {tool_name} 执行超时")
                return {"status": "error", "message": f"工具执行超时 (>{self.settings.timeout_seconds}秒)"}
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行错误: {str(e)}")
                return {"status": "error", "message": f"工具执行错误: {str(e)}"}
    
    def reset(self) -> None:
        """重置工具管理器，清空所有工具实例"""
        self.tools = {}
        
        
# 全局工具管理器实例
tool_manager = OwlToolManager()


# 工具注册装饰器
def register_tool(tool_name: str):
    """工具注册装饰器
    
    用于简化工具类的注册过程
    
    Args:
        tool_name (str): 工具名称
        
    Example:
        @register_tool("search")
        class SearchTool(BaseTool):
            pass
    """
    def decorator(cls):
        tool_manager.register_tool_class(tool_name, cls)
        return cls
    return decorator
