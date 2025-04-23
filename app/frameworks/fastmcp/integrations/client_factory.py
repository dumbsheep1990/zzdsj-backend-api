"""
MCP客户端工厂模块
提供统一的接口来创建各种类型的MCP客户端
"""

import logging
from typing import Dict, Any, Optional, List, Union

from .registry import get_external_mcp, load_provider_module
from .types.base import BaseMCPClient, ClientCapability
from .types.chat import ChatMCPClient
from .types.image import ImageMCPClient
from .types.map import MapMCPClient
from .types.data import DataMCPClient

logger = logging.getLogger(__name__)

async def create_mcp_client(
    provider_id: str,
    client_type: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> Union[BaseMCPClient, ChatMCPClient, ImageMCPClient, MapMCPClient, DataMCPClient]:
    """
    创建MCP客户端实例
    
    参数:
        provider_id: 提供商ID
        client_type: 客户端类型，如"chat", "image", "map", "data"
        api_key: API密钥，如果提供则覆盖配置中的密钥
        **kwargs: 其他参数传递给客户端构造函数
        
    返回:
        MCP客户端实例
    """
    # 检查提供商是否存在
    service = get_external_mcp(provider_id)
    if not service:
        raise ValueError(f"未找到MCP服务: {provider_id}")
    
    # 加载提供商模块
    provider_module = load_provider_module(provider_id)
    
    if provider_module:
        # 检查是否有特定类型的客户端工厂
        if client_type and hasattr(provider_module, f"create_{client_type}_client"):
            factory = getattr(provider_module, f"create_{client_type}_client")
            return await factory(provider_id, api_key, **kwargs)
        
        # 检查是否有通用客户端工厂
        if hasattr(provider_module, "create_client"):
            return await provider_module.create_client(provider_id, api_key, client_type=client_type, **kwargs)
    
    # 如果没有特定的模块实现，使用通用客户端
    from .providers.generic import create_client as create_generic_client
    return await create_generic_client(provider_id, api_key, client_type=client_type, **kwargs)

async def create_chat_client(
    provider_id: str,
    api_key: Optional[str] = None,
    **kwargs
) -> ChatMCPClient:
    """
    创建聊天MCP客户端
    
    参数:
        provider_id: 提供商ID
        api_key: API密钥
        **kwargs: 其他参数
        
    返回:
        聊天MCP客户端
    """
    return await create_mcp_client(provider_id, "chat", api_key, **kwargs)

async def create_image_client(
    provider_id: str,
    api_key: Optional[str] = None,
    **kwargs
) -> ImageMCPClient:
    """
    创建图像MCP客户端
    
    参数:
        provider_id: 提供商ID
        api_key: API密钥
        **kwargs: 其他参数
        
    返回:
        图像MCP客户端
    """
    return await create_mcp_client(provider_id, "image", api_key, **kwargs)

async def create_map_client(
    provider_id: str,
    api_key: Optional[str] = None,
    **kwargs
) -> MapMCPClient:
    """
    创建地图MCP客户端
    
    参数:
        provider_id: 提供商ID
        api_key: API密钥
        **kwargs: 其他参数
        
    返回:
        地图MCP客户端
    """
    return await create_mcp_client(provider_id, "map", api_key, **kwargs)

async def create_data_client(
    provider_id: str,
    api_key: Optional[str] = None,
    **kwargs
) -> DataMCPClient:
    """
    创建数据MCP客户端
    
    参数:
        provider_id: 提供商ID
        api_key: API密钥
        **kwargs: 其他参数
        
    返回:
        数据MCP客户端
    """
    return await create_mcp_client(provider_id, "data", api_key, **kwargs)

def get_recommended_providers(capability: Optional[Union[str, ClientCapability]] = None) -> List[Dict[str, Any]]:
    """
    获取推荐的提供商列表
    
    参数:
        capability: 筛选特定能力的提供商
        
    返回:
        推荐的提供商信息列表
    """
    from .registry import list_external_mcps
    
    # 转换能力类型
    cap_str = None
    if capability:
        if isinstance(capability, ClientCapability):
            cap_str = capability.value
        else:
            cap_str = capability
    
    # 获取所有活跃的提供商
    all_providers = list_external_mcps(capability=cap_str)
    
    # 转换为前端友好格式
    recommended = []
    for provider in all_providers:
        recommended.append({
            "id": provider.id,
            "name": provider.name,
            "description": provider.description,
            "provider": provider.provider,
            "capabilities": provider.capabilities,
            "requires_auth": provider.auth_type != "none",
            "metadata": provider.metadata or {}
        })
    
    return recommended
