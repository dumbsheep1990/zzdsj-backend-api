"""
FastMCP第三方服务集成模块
提供集成第三方MCP服务的能力
"""

# 注册表功能
from .registry import (
    register_external_mcp,
    update_external_mcp,
    unregister_external_mcp,
    get_external_mcp,
    list_external_mcps,
    register_all_providers,
    load_provider_module,
    ExternalMCPService
)

# 配置功能
from .config import (
    get_all_providers,
    get_provider_config,
    add_provider_config,
    update_provider_config,
    delete_provider_config
)

# 客户端类型
from .types.base import BaseMCPClient, ClientCapability
from .types.chat import ChatMCPClient
from .types.image import ImageMCPClient
from .types.map import MapMCPClient
from .types.data import DataMCPClient

# 客户端工厂
from .client_factory import (
    create_mcp_client,
    create_chat_client,
    create_image_client,
    create_map_client,
    create_data_client,
    get_recommended_providers
)

__all__ = [
    # 注册表
    "register_external_mcp",
    "update_external_mcp",
    "unregister_external_mcp",
    "get_external_mcp",
    "list_external_mcps",
    "register_all_providers",
    "load_provider_module",
    "ExternalMCPService",
    
    # 配置
    "get_all_providers",
    "get_provider_config",
    "add_provider_config",
    "update_provider_config",
    "delete_provider_config",
    
    # 客户端类型
    "BaseMCPClient",
    "ClientCapability",
    "ChatMCPClient",
    "ImageMCPClient",
    "MapMCPClient",
    "DataMCPClient",
    
    # 客户端工厂
    "create_mcp_client",
    "create_chat_client",
    "create_image_client",
    "create_map_client",
    "create_data_client",
    "get_recommended_providers"
]

# 自动注册所有配置的提供商
register_all_providers()
