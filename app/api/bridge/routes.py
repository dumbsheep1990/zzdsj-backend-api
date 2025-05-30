"""
统一API桥接路由注册
自动注册所有需要桥接的API路由
"""

from fastapi import APIRouter, FastAPI
import logging

from app.api.bridge.bridge_implementation import bridge_manager

logger = logging.getLogger(__name__)

def register_bridge_routes(app: FastAPI) -> None:
    """
    向FastAPI应用注册所有桥接路由
    
    Args:
        app: FastAPI应用实例
    """
    # 获取所有可用的桥接API
    available_bridges = bridge_manager.list_available_bridges()
    logger.info(f"正在注册 {len(available_bridges)} 个API桥接路由")
    
    # 为每个API创建并注册桥接路由
    for api_name in available_bridges:
        try:
            # 获取桥接路由
            router = bridge_manager.get_bridge(api_name)
            
            # 将路由注册到应用
            # 注意：这里不添加前缀，因为新模块中已经定义了前缀
            app.include_router(router)
            logger.info(f"成功注册API桥接: {api_name}")
            
        except Exception as e:
            logger.error(f"注册API桥接 '{api_name}' 时出错: {str(e)}")
            
    logger.info("所有API桥接路由注册完成")

def create_bridge_router() -> APIRouter:
    """
    创建包含所有桥接路由的主路由
    
    Returns:
        包含所有桥接的APIRouter实例
    """
    main_router = APIRouter()
    
    # 获取所有可用的桥接API
    available_bridges = bridge_manager.list_available_bridges()
    logger.info(f"正在创建 {len(available_bridges)} 个API桥接路由")
    
    # 为每个API创建并添加桥接路由
    for api_name in available_bridges:
        try:
            # 获取桥接路由
            router = bridge_manager.get_bridge(api_name)
            
            # 将所有路由添加到主路由
            for route in router.routes:
                main_router.routes.append(route)
                
            logger.info(f"成功添加API桥接: {api_name}")
            
        except Exception as e:
            logger.error(f"添加API桥接 '{api_name}' 时出错: {str(e)}")
            
    logger.info("所有API桥接路由创建完成")
    return main_router
