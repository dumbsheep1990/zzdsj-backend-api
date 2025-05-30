"""
API桥接主入口
用于集成到FastAPI应用中的主模块
"""

from fastapi import FastAPI, APIRouter
import logging
import importlib.util
import os
import sys
from typing import List, Dict, Any, Optional

from app.api.bridge.api_bridge_mapping import API_BRIDGE_MAPPING

logger = logging.getLogger(__name__)

def create_api_bridges() -> Dict[str, APIRouter]:
    """
    创建所有API的桥接路由
    
    Returns:
        字典，键为API名称，值为对应的桥接路由
    """
    bridges = {}
    
    for api_name, config in API_BRIDGE_MAPPING.items():
        try:
            new_module_path = config["path"]
            description = config["description"]
            
            # 创建路由
            router = APIRouter()
            
            # 导入新的API模块
            module_path = f"app.api.frontend.{new_module_path}"
            try:
                new_module = importlib.import_module(module_path)
                new_router = getattr(new_module, "router")
                
                # 记录迁移警告
                warning_message = f"使用已弃用的app/api/{api_name}.py，该文件已迁移至{module_path}"
                logger.warning(warning_message)
                
                # 将所有请求转发到新的路由处理器
                for route in new_router.routes:
                    router.routes.append(route)
                
                bridges[api_name] = router
                logger.info(f"成功创建API桥接: {api_name} -> {module_path}")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"导入模块 '{module_path}' 失败: {str(e)}")
                continue
                
        except Exception as e:
            logger.error(f"为API '{api_name}' 创建桥接时出错: {str(e)}")
            continue
            
    return bridges

def register_bridges_to_app(app: FastAPI) -> None:
    """
    将所有API桥接注册到FastAPI应用
    
    Args:
        app: FastAPI应用实例
    """
    bridges = create_api_bridges()
    logger.info(f"正在注册 {len(bridges)} 个API桥接路由")
    
    for api_name, router in bridges.items():
        app.include_router(router)
        logger.info(f"已注册API桥接: {api_name}")
        
    logger.info("所有API桥接路由注册完成")
