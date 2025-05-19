"""
服务注册模块 - 负责发现和注册服务到Nacos
"""
import importlib
import inspect
import logging
import json
import pkgutil
from typing import List, Type, Dict, Any

from app.utils.service_discovery import get_nacos_client
from app.utils.service_decorators import get_registered_services
from app.config import settings

logger = logging.getLogger(__name__)

def discover_decorated_services() -> List[Type]:
    """
    发现所有用@register_service装饰的服务类
    
    Returns:
        装饰了register_service的服务类列表
    """
    # 首先尝试导入所有服务模块，确保装饰器被执行
    import app.services
    
    # 遍历services包下的所有模块
    for _, module_name, is_pkg in pkgutil.iter_modules(app.services.__path__, app.services.__name__ + "."):
        if is_pkg:
            continue
            
        try:
            # 导入模块以触发装饰器执行
            importlib.import_module(module_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"导入服务模块 {module_name} 时出错: {str(e)}")
    
    # 获取已通过装饰器注册的服务
    decorated_services = get_registered_services()
    logger.info(f"发现了 {len(decorated_services)} 个装饰的服务类")
    
    return decorated_services

def register_decorated_services():
    """
    注册所有用装饰器标记的服务到Nacos
    
    Returns:
        成功注册的服务数量
    """
    nacos_client = get_nacos_client()
    services = discover_decorated_services()
    
    success_count = 0
    for service_cls in services:
        try:
            service_name = getattr(service_cls, '__service_name__')
            metadata = getattr(service_cls, '__service_metadata__', {})
            
            # 添加基本元数据
            metadata.update({
                "type": "application-service",
                "app": "zz-backend-lite",
                "class": service_cls.__name__
            })
            
            # 服务名称处理
            # 如果服务名已经包含service前缀，则不再添加
            prefixed_service_name = service_name
            if not service_name.startswith("service-"):
                prefixed_service_name = f"service-{service_name}"
            
            # 注册服务到Nacos
            success = nacos_client.add_instance(
                service_name=prefixed_service_name,
                ip=settings.SERVICE_IP,
                port=settings.SERVICE_PORT,
                weight=1.0,
                ephemeral=True,
                metadata=json.dumps(metadata),
                group_name=settings.NACOS_GROUP
            )
            
            if success:
                logger.info(f"服务 {prefixed_service_name} 注册成功")
                success_count += 1
            else:
                logger.error(f"服务 {prefixed_service_name} 注册失败")
                
        except Exception as e:
            service_name = getattr(service_cls, '__service_name__', service_cls.__name__)
            logger.error(f"注册服务 {service_name} 时出错: {str(e)}", exc_info=True)
    
    logger.info(f"服务注册完成: {success_count}/{len(services)} 个服务注册成功")
    return success_count

def deregister_decorated_services():
    """
    从Nacos注销所有已注册的服务
    
    Returns:
        成功注销的服务数量
    """
    nacos_client = get_nacos_client()
    services = discover_decorated_services()
    
    success_count = 0
    for service_cls in services:
        try:
            service_name = getattr(service_cls, '__service_name__')
            
            # 处理服务名称前缀
            prefixed_service_name = service_name
            if not service_name.startswith("service-"):
                prefixed_service_name = f"service-{service_name}"
            
            # 从Nacos注销服务
            success = nacos_client.remove_instance(
                service_name=prefixed_service_name,
                ip=settings.SERVICE_IP,
                port=settings.SERVICE_PORT,
                group_name=settings.NACOS_GROUP
            )
            
            if success:
                logger.info(f"服务 {prefixed_service_name} 已从Nacos注销")
                success_count += 1
            else:
                logger.error(f"无法从Nacos注销服务 {prefixed_service_name}")
                
        except Exception as e:
            service_name = getattr(service_cls, '__service_name__', service_cls.__name__)
            logger.error(f"注销服务 {service_name} 时出错: {str(e)}", exc_info=True)
    
    logger.info(f"服务注销完成: {success_count}/{len(services)} 个服务注销成功")
    return success_count
