"""
统一API桥接实现
根据映射配置自动创建所有API的桥接逻辑
"""

from fastapi import APIRouter
import logging
import importlib
import os
import sys

# 导入桥接映射配置
from app.api.bridge.api_bridge_mapping import API_BRIDGE_MAPPING

class BridgeManager:
    """API桥接管理器，负责创建和管理所有API桥接"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bridges = {}
        
    def create_bridge(self, api_name: str) -> APIRouter:
        """
        为指定API创建桥接路由
        
        Args:
            api_name: API名称（不含.py后缀）
            
        Returns:
            配置好的APIRouter实例
        """
        if api_name not in API_BRIDGE_MAPPING:
            self.logger.error(f"未找到API '{api_name}' 的桥接配置")
            raise KeyError(f"未找到API '{api_name}' 的桥接配置")
            
        config = API_BRIDGE_MAPPING[api_name]
        new_module_path = config["path"]
        description = config["description"]
        
        # 创建路由
        router = APIRouter()
        
        try:
            # 导入新的API模块
            module_path = f"app.api.frontend.{new_module_path}"
            new_module = importlib.import_module(module_path)
            new_router = getattr(new_module, "router")
            
            # 记录迁移警告
            warning_message = f"使用已弃用的app/api/{api_name}.py，该文件已迁移至{module_path}"
            self.logger.warning(warning_message)
            
            # 将所有请求转发到新的路由处理器
            for route in new_router.routes:
                router.routes.append(route)
                
            # 缓存创建的桥接
            self.bridges[api_name] = router
            return router
            
        except (ImportError, AttributeError) as e:
            self.logger.error(f"为API '{api_name}' 创建桥接时出错: {str(e)}")
            raise
    
    def get_bridge(self, api_name: str) -> APIRouter:
        """
        获取API的桥接路由，如果不存在则创建
        
        Args:
            api_name: API名称（不含.py后缀）
            
        Returns:
            配置好的APIRouter实例
        """
        if api_name not in self.bridges:
            return self.create_bridge(api_name)
        return self.bridges[api_name]
    
    def list_available_bridges(self) -> list:
        """
        获取所有可用的桥接API名称列表
        
        Returns:
            API名称列表
        """
        return list(API_BRIDGE_MAPPING.keys())

# 创建全局桥接管理器实例
bridge_manager = BridgeManager()

def get_bridge_router(api_name: str) -> APIRouter:
    """
    获取指定API的桥接路由
    
    Args:
        api_name: API名称（不含.py后缀）
        
    Returns:
        配置好的APIRouter实例
    """
    return bridge_manager.get_bridge(api_name)
