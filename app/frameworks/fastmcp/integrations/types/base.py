"""
MCP客户端基类模块
定义所有MCP客户端的基础接口
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Union

class ClientCapability(Enum):
    """客户端能力枚举"""
    CHAT = "chat"
    TOOLS = "tools"
    EMBEDDINGS = "embeddings"
    RETRIEVAL = "retrieval"
    IMAGE_GENERATION = "image_generation"
    MAPS = "maps"
    GEOCODING = "geocoding"
    FILE_OPERATIONS = "file_operations"
    DATABASE = "database"
    WEB_SEARCH = "web_search"
    WEB_SCRAPING = "web_scraping"
    CODE = "code"
    EMAIL = "email"
    STORAGE = "storage"

class BaseMCPClient(ABC):
    """MCP客户端基类"""
    
    @property
    @abstractmethod
    def capabilities(self) -> List[ClientCapability]:
        """获取客户端支持的能力"""
        pass
    
    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用工具
        
        参数:
            tool_name: 工具名称
            parameters: 工具参数
            timeout: 调用超时时间
            context: 上下文信息
            
        返回:
            工具返回结果
        """
        pass
    
    @abstractmethod
    async def get_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        参数:
            force_refresh: 是否强制刷新缓存
            
        返回:
            工具描述列表
        """
        pass
    
    @abstractmethod
    async def close(self):
        """关闭客户端连接"""
        pass
    
    def has_capability(self, capability: ClientCapability) -> bool:
        """
        检查客户端是否支持指定能力
        
        参数:
            capability: 要检查的能力
            
        返回:
            如果支持则为True，否则为False
        """
        return capability in self.capabilities
