"""
服务装饰器模块 - 用于注册和发现服务
"""
import functools
from typing import Type, Optional, Dict, Any, List, Callable

# 存储所有被注册的服务
_REGISTERED_SERVICES: List[Type] = []

def register_service(service_name: Optional[str] = None, **metadata):
    """
    服务注册装饰器
    用于标记需要注册到Nacos的服务类
    
    Args:
        service_name: 可选，服务名称，默认使用类名
        **metadata: 可选，服务元数据
    
    Returns:
        装饰后的类
    
    Example:
        ```python
        @register_service(service_type="knowledge-service", priority="high")
        class KnowledgeService:
            pass
        ```
    """
    def decorator(cls):
        # 存储服务名称和元数据
        cls.__service_name__ = service_name or cls.__name__.replace('Service', '').lower()
        cls.__service_metadata__ = metadata or {}
        cls.__register_to_nacos__ = True
        
        # 将服务添加到注册列表
        if cls not in _REGISTERED_SERVICES:
            _REGISTERED_SERVICES.append(cls)
        
        return cls
    
    return decorator

def get_registered_services() -> List[Type]:
    """
    获取所有通过装饰器注册的服务类
    
    Returns:
        已注册的服务类列表
    """
    return _REGISTERED_SERVICES
