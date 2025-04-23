"""
第三方MCP服务配置模块
管理MCP服务提供商的配置
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from app.config import settings

logger = logging.getLogger(__name__)

# 默认MCP服务提供商配置
DEFAULT_MCP_PROVIDERS = {
    "anthropic-claude": {
        "name": "Anthropic Claude",
        "description": "Anthropic的Claude模型MCP服务",
        "provider": "anthropic",
        "api_url": settings.ANTHROPIC_API_BASE,
        "capabilities": ["chat", "tools", "retrieval"],
        "metadata": {
            "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        }
    },
    "openai-gpt": {
        "name": "OpenAI GPT",
        "description": "OpenAI的GPT模型MCP服务",
        "provider": "openai",
        "api_url": settings.OPENAI_API_BASE,
        "capabilities": ["chat", "tools", "embeddings", "retrieval"],
        "metadata": {
            "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        }
    },
    "baidu-map": {
        "name": "Baidu Map",
        "description": "百度地图接入API即可全面覆盖MCP协议，是国内首家索引完MCP协议的地图服务商",
        "provider": "baidu",
        "api_url": "https://api.map.baidu.com/mcp",
        "capabilities": ["map", "location", "geocoding", "search"],
        "metadata": {
            "requires_api_key": True
        }
    },
    "github": {
        "name": "GitHub",
        "description": "Repository management, file operations, and GitHub API integration",
        "provider": "github",
        "api_url": "https://api.github.com",
        "capabilities": ["file_operations", "repository", "issue_tracking"],
        "metadata": {
            "requires_auth": True
        }
    },
    "aws-kb": {
        "name": "AWS KB Retrieval Server",
        "description": "An MCP server implementation for retrieving information from the AWS Knowledge Base",
        "provider": "aws",
        "api_url": "https://mcp.aws.amazon.com/kb",
        "capabilities": ["retrieval", "knowledge_base"],
        "metadata": {
            "requires_api_key": True
        }
    },
    "tavily-mcp": {
        "name": "Tavily MCP Server",
        "description": "MCP服务用于网络搜索和信息检索",
        "provider": "tavily",
        "api_url": "https://api.tavily.com/mcp",
        "capabilities": ["web_search", "retrieval"],
        "metadata": {
            "requires_api_key": True
        }
    },
    "edgeone-pages": {
        "name": "EdgeOne Pages MCP",
        "description": "An MCP service designed for deploying HTML content to EdgeOne Pages",
        "provider": "edgeone",
        "api_url": "https://api.edgeone.dev/mcp",
        "capabilities": ["file_operations", "deployment"],
        "metadata": {
            "requires_auth": True
        }
    },
    "perplexity-ask": {
        "name": "Perplexity Ask MCP Server",
        "description": "A Model Context Protocol Server connector for Perplexity API",
        "provider": "perplexity",
        "api_url": "https://api.perplexity.ai/mcp",
        "capabilities": ["chat", "web_search", "retrieval"],
        "metadata": {
            "requires_api_key": True
        }
    },
    "minimax-mcp": {
        "name": "MiniMax MCP",
        "description": "Official MiniMax Model Context Protocol server",
        "provider": "minimax",
        "api_url": "https://api.minimax.chat/mcp",
        "capabilities": ["chat", "tools", "image_generation"],
        "metadata": {
            "requires_api_key": True,
            "models": ["abab5.5-chat"]
        }
    },
    "amap-maps": {
        "name": "Amap Maps",
        "description": "高德地图方 MCP Server",
        "provider": "amap",
        "api_url": "https://api.amap.com/mcp",
        "capabilities": ["map", "location", "geocoding", "search"],
        "metadata": {
            "requires_api_key": True
        }
    },
    "firecrawl": {
        "name": "Firecrawl MCP Server",
        "description": "Official Firecrawl MCP Server - Adds powerful web scraping capabilities",
        "provider": "firecrawl",
        "api_url": "https://api.firecrawl.dev/mcp",
        "capabilities": ["web_scraping", "web_crawler"],
        "metadata": {
            "requires_auth": True
        }
    },
    "everart": {
        "name": "EverArt",
        "description": "AI image generation using various models",
        "provider": "everart",
        "api_url": "https://api.everart.ai/mcp",
        "capabilities": ["image_generation"],
        "metadata": {
            "requires_api_key": True,
            "supported_models": ["stable-diffusion-xl", "dalle-3", "midjourney"]
        }
    }
}

# 配置文件路径
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                         "config", "mcp_providers.json")

def load_custom_providers() -> Dict[str, Any]:
    """
    从配置文件加载自定义提供商配置
    
    返回:
        自定义提供商配置
    """
    if not os.path.exists(CONFIG_PATH):
        return {}
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载MCP提供商配置文件时出错: {str(e)}")
        return {}

def save_custom_providers(providers: Dict[str, Any]) -> bool:
    """
    保存自定义提供商配置到文件
    
    参数:
        providers: 提供商配置
        
    返回:
        成功保存返回True，否则返回False
    """
    try:
        # 确保配置目录存在
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(providers, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"保存MCP提供商配置文件时出错: {str(e)}")
        return False

def get_all_providers() -> Dict[str, Any]:
    """
    获取所有提供商配置
    
    返回:
        所有提供商配置
    """
    providers = DEFAULT_MCP_PROVIDERS.copy()
    
    # 合并自定义配置
    custom_providers = load_custom_providers()
    providers.update(custom_providers)
    
    return providers

def get_provider_config(provider_id: str) -> Optional[Dict[str, Any]]:
    """
    获取特定提供商配置
    
    参数:
        provider_id: 提供商ID
        
    返回:
        提供商配置，如果不存在则返回None
    """
    providers = get_all_providers()
    return providers.get(provider_id)

def add_provider_config(
    provider_id: str,
    name: str,
    provider: str,
    api_url: str,
    description: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    添加提供商配置
    
    参数:
        provider_id: 提供商ID
        name: 提供商名称
        provider: 提供商类型
        api_url: API URL
        description: 描述
        capabilities: 能力列表
        metadata: 元数据
        
    返回:
        成功添加返回True，否则返回False
    """
    custom_providers = load_custom_providers()
    
    # 添加新配置
    custom_providers[provider_id] = {
        "name": name,
        "provider": provider,
        "api_url": api_url,
        "description": description or "",
        "capabilities": capabilities or [],
        "metadata": metadata or {}
    }
    
    return save_custom_providers(custom_providers)

def update_provider_config(
    provider_id: str,
    **kwargs
) -> bool:
    """
    更新提供商配置
    
    参数:
        provider_id: 提供商ID
        **kwargs: 要更新的字段
        
    返回:
        成功更新返回True，否则返回False
    """
    custom_providers = load_custom_providers()
    
    # 检查是否为内置提供商
    if provider_id in DEFAULT_MCP_PROVIDERS and provider_id not in custom_providers:
        # 复制内置配置到自定义配置
        custom_providers[provider_id] = DEFAULT_MCP_PROVIDERS[provider_id].copy()
    
    # 检查提供商是否存在
    if provider_id not in custom_providers:
        return False
    
    # 更新配置
    for key, value in kwargs.items():
        if key in custom_providers[provider_id]:
            custom_providers[provider_id][key] = value
    
    return save_custom_providers(custom_providers)

def delete_provider_config(provider_id: str) -> bool:
    """
    删除提供商配置
    
    参数:
        provider_id: 提供商ID
        
    返回:
        成功删除返回True，否则返回False
    """
    custom_providers = load_custom_providers()
    
    # 检查提供商是否存在
    if provider_id not in custom_providers:
        return False
    
    # 删除配置
    del custom_providers[provider_id]
    
    return save_custom_providers(custom_providers)
