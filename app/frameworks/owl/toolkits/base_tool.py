"""
OWL框架基础工具类
为所有OWL工具提供统一的接口和基础功能
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.frameworks.owl.config import get_tool_settings, owl_tools_settings

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """OWL基础工具类
    
    所有OWL工具都应该继承这个基类，并实现execute方法
    """
    
    def __init__(self, name: str = None, description: str = None):
        """初始化基础工具
        
        Args:
            name (str, optional): 工具名称，默认为类名
            description (str, optional): 工具描述，默认为类文档字符串
        """
        self.name = name or self.__class__.__name__
        self.description = description or self.__doc__ or f"{self.name}工具"
        self.enabled = True
        self.tool_type = self._extract_tool_type()
        self.config = {}
        
    def _extract_tool_type(self) -> str:
        """从类名中提取工具类型
        
        例如：SearchTool -> search, DocumentProcessorTool -> document_processor
        
        Returns:
            str: 工具类型名称
        """
        name = self.__class__.__name__
        if name.endswith('Tool'):
            name = name[:-4]  # 移除'Tool'后缀
            
        # 驼峰转蛇形命名
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
    async def initialize(self, db: Session) -> None:
        """初始化工具
        
        该方法会在工具首次使用前被调用，用于加载配置、初始化资源等
        
        Args:
            db (Session): 数据库会话
        """
        # 从环境变量加载工具配置
        tool_settings = get_tool_settings(self.tool_type)
        if tool_settings:
            # 将配置对象转换为字典
            self.config = {k: v for k, v in tool_settings.dict().items() 
                         if not k.startswith('_')}
            
            # 应用常见配置
            if hasattr(tool_settings, 'enabled'):
                self.enabled = tool_settings.enabled
                
        # 应用全局超时配置
        self.timeout_seconds = owl_tools_settings.timeout_seconds
        
        logger.info(f"工具[{self.name}]已初始化，配置: {self.config}")
            
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具功能
        
        所有工具子类必须实现这个方法
        
        Args:
            **kwargs: 工具执行参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        raise NotImplementedError("工具子类必须实现execute方法")
    
    def get_description(self) -> str:
        """获取工具描述
        
        Returns:
            str: 工具描述
        """
        return self.description
    
    def get_parameters(self) -> Dict[str, Dict[str, Any]]:
        """获取工具参数说明
        
        子类可以覆盖此方法，提供更具体的参数描述
        
        Returns:
            Dict[str, Dict[str, Any]]: 工具参数说明
        """
        return {
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    
    def __repr__(self) -> str:
        """工具字符串表示
        
        Returns:
            str: 工具描述
        """
        return f"{self.name}: {self.description}"
