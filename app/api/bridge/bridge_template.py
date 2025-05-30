"""
标准API桥接模板
用于为旧API创建到新路径的桥接逻辑
"""

from fastapi import APIRouter
import logging

def create_bridge(
    old_file_name: str, 
    new_module_path: str, 
    description: str
) -> APIRouter:
    """
    创建API桥接路由
    
    Args:
        old_file_name: 旧文件名
        new_module_path: 新模块路径
        description: API功能描述
        
    Returns:
        配置好的APIRouter实例
    """
    # 导入新的API模块
    module_path = f"app.api.frontend.{new_module_path}"
    import_path = f"from {module_path} import router as new_router"
    exec(import_path, globals())
    
    # 创建路由
    router = APIRouter()
    logger = logging.getLogger(__name__)
    
    # 记录迁移警告
    warning_message = f"使用已弃用的app/api/{old_file_name}，该文件已迁移至{module_path}"
    logger.warning(warning_message)
    
    # 将所有请求转发到新的路由处理器
    for route in globals()["new_router"].routes:
        router.routes.append(route)
        
    return router
