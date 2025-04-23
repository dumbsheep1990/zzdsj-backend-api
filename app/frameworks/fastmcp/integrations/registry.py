"""
第三方MCP服务注册表模块
管理和跟踪已注册的第三方MCP服务
"""

import importlib
import logging
from typing import Dict, Any, Optional, List, Union, Type
from pydantic import BaseModel

from .config import get_all_providers, get_provider_config, add_provider_config, update_provider_config, delete_provider_config
from .types.base import BaseMCPClient

logger = logging.getLogger(__name__)

# 第三方MCP服务模型
class ExternalMCPService(BaseModel):
    """第三方MCP服务模型"""
    id: str  # 服务唯一标识符
    name: str  # 服务显示名称
    description: Optional[str] = None  # 服务描述
    provider: str  # 服务提供商
    api_url: str  # API地址
    api_key: Optional[str] = None  # API密钥（如果需要）
    auth_type: str = "api_key"  # 认证类型（api_key, oauth, none）
    auth_headers: Optional[Dict[str, str]] = None  # 认证头部信息
    capabilities: List[str] = []  # 服务支持的能力列表
    status: str = "active"  # 服务状态
    metadata: Optional[Dict[str, Any]] = None  # 其他元数据

# 服务注册表
_external_mcp_registry: Dict[str, ExternalMCPService] = {}

def load_provider_module(provider_id: str) -> Optional[Any]:
    """
    动态加载提供商模块
    
    参数:
        provider_id: 提供商ID
        
    返回:
        提供商模块或None
    """
    config = get_provider_config(provider_id)
    if not config:
        return None
    
    provider = config.get("provider", "")
    if not provider:
        return None
    
    try:
        # 尝试导入提供商特定模块
        module_path = f"app.frameworks.fastmcp.integrations.providers.{provider}"
        return importlib.import_module(module_path)
    except ImportError:
        try:
            # 尝试导入通用模块
            return importlib.import_module("app.frameworks.fastmcp.integrations.providers.generic")
        except ImportError:
            logger.warning(f"无法加载提供商模块: {provider}")
            return None

def register_external_mcp(
    id: str,
    name: str,
    provider: str,
    api_url: str,
    description: Optional[str] = None,
    api_key: Optional[str] = None,
    auth_type: str = "api_key",
    auth_headers: Optional[Dict[str, str]] = None,
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ExternalMCPService:
    """
    注册外部MCP服务
    
    参数:
        id: 服务唯一标识符
        name: 服务显示名称
        provider: 服务提供商
        api_url: API地址
        description: 服务描述
        api_key: API密钥（如果需要）
        auth_type: 认证类型（api_key, oauth, none）
        auth_headers: 认证头部信息
        capabilities: 支持的能力列表
        metadata: 其他元数据
        
    返回:
        注册的服务实例
    """
    # 创建服务实例
    service = ExternalMCPService(
        id=id,
        name=name,
        description=description,
        provider=provider,
        api_url=api_url,
        api_key=api_key,
        auth_type=auth_type,
        auth_headers=auth_headers or {},
        capabilities=capabilities or [],
        metadata=metadata or {}
    )
    
    # 添加到注册表
    _external_mcp_registry[id] = service
    
    logger.info(f"注册外部MCP服务: {name} (ID: {id})")
    return service

def update_external_mcp(
    id: str,
    **kwargs
) -> Optional[ExternalMCPService]:
    """
    更新已注册的外部MCP服务
    
    参数:
        id: 服务唯一标识符
        **kwargs: 要更新的字段和值
        
    返回:
        更新后的服务实例，如果不存在则返回None
    """
    if id not in _external_mcp_registry:
        logger.warning(f"尝试更新不存在的MCP服务: {id}")
        return None
    
    # 获取现有服务
    service = _external_mcp_registry[id]
    
    # 更新服务属性
    for key, value in kwargs.items():
        if hasattr(service, key):
            setattr(service, key, value)
    
    logger.info(f"更新外部MCP服务: {service.name} (ID: {id})")
    return service

def unregister_external_mcp(id: str) -> bool:
    """
    注销外部MCP服务
    
    参数:
        id: 服务唯一标识符
        
    返回:
        成功注销返回True，否则返回False
    """
    if id not in _external_mcp_registry:
        logger.warning(f"尝试注销不存在的MCP服务: {id}")
        return False
    
    # 从注册表中移除
    service = _external_mcp_registry.pop(id)
    
    logger.info(f"注销外部MCP服务: {service.name} (ID: {id})")
    return True

def get_external_mcp(id: str) -> Optional[ExternalMCPService]:
    """
    获取指定ID的外部MCP服务
    
    参数:
        id: 服务唯一标识符
        
    返回:
        服务实例，如果不存在则返回None
    """
    return _external_mcp_registry.get(id)

def list_external_mcps(
    provider: Optional[str] = None,
    capability: Optional[str] = None,
    status: str = "active"
) -> List[ExternalMCPService]:
    """
    列出注册的外部MCP服务
    
    参数:
        provider: 可选，按提供商筛选
        capability: 可选，按能力筛选
        status: 按状态筛选，默认只返回活跃的服务
        
    返回:
        服务列表
    """
    services = []
    
    for service in _external_mcp_registry.values():
        # 按状态筛选
        if status and service.status != status:
            continue
            
        # 按提供商筛选
        if provider and service.provider != provider:
            continue
            
        # 按能力筛选
        if capability and capability not in service.capabilities:
            continue
            
        services.append(service)
    
    return services

def get_client_class(provider_id: str, client_type: Optional[str] = None) -> Optional[Type[BaseMCPClient]]:
    """
    获取客户端类
    
    参数:
        provider_id: 提供商ID
        client_type: 客户端类型 (chat, image, map, data)
        
    返回:
        客户端类，如果不存在则返回None
    """
    module = load_provider_module(provider_id)
    if not module:
        return None
    
    # 检查特定类型的客户端类
    if client_type:
        class_name = f"{client_type.title()}MCPClient"
        if hasattr(module, class_name):
            return getattr(module, class_name)
    
    # 检查通用客户端类
    if hasattr(module, "MCPClient"):
        return getattr(module, "MCPClient")
    
    return None

def register_all_providers():
    """注册所有配置的提供商"""
    from app.config import settings
    
    providers = get_all_providers()
    for provider_id, config in providers.items():
        # 获取API密钥
        api_key = None
        if config.get("provider"):
            provider_upper = config["provider"].upper()
            api_key_attr = f"{provider_upper}_API_KEY"
            if hasattr(settings, api_key_attr):
                api_key = getattr(settings, api_key_attr)
        
        # 注册提供商
        register_external_mcp(
            id=provider_id,
            name=config["name"],
            description=config.get("description"),
            provider=config["provider"],
            api_url=config["api_url"],
            api_key=api_key,
            capabilities=config.get("capabilities", []),
            metadata=config.get("metadata", {})
        )
