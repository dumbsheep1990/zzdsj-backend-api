"""
MCP服务类型模块
定义不同类型MCP服务的基础类和接口
"""

from .base import BaseMCPClient, ClientCapability
from .chat import ChatMCPClient
from .image import ImageMCPClient
from .map import MapMCPClient
from .data import DataMCPClient

__all__ = [
    "BaseMCPClient",
    "ClientCapability",
    "ChatMCPClient",
    "ImageMCPClient",
    "MapMCPClient",
    "DataMCPClient"
]
