"""
上下文压缩功能启动模块
初始化上下文压缩中间件和相关配置
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI

from app.utils.core.database import get_db
from app.utils.core.config import get_config_manager
from app.tools.advanced.context_compression.middleware import ContextCompressionMiddleware

logger = logging.getLogger(__name__)


def register_context_compression(app: FastAPI):
    """
    注册上下文压缩功能
    
    参数:
        app: FastAPI应用实例
    """
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    # 从配置中读取上下文压缩设置
    compression_config = config.get("context_compression", {})
    compression_enabled = compression_config.get("enabled", True)
    
    if compression_enabled:
        try:
            # 初始化中间件
            middleware_config = compression_config.get("middleware", {})
            paths_to_compress = middleware_config.get("paths_to_compress", [
                "/api/v1/owl/agents/{agent_id}/completions",
                "/api/v1/owl/agents/{agent_id}/chat",
                "/api/v1/chat/completions"
            ])
            
            # 创建上下文压缩中间件
            compression_middleware = ContextCompressionMiddleware(
                app=app,
                db_session_getter=get_db,
                enabled=compression_enabled,
                paths_to_compress=paths_to_compress,
                compression_config=middleware_config.get("compression_config", {})
            )
            
            # 添加中间件到应用
            app.middleware("http")(compression_middleware)
            
            logger.info("上下文压缩中间件已启用，将处理以下路径: %s", ", ".join(paths_to_compress))
        except Exception as e:
            logger.error("初始化上下文压缩中间件失败: %s", str(e))
    else:
        logger.info("上下文压缩功能已禁用")
    
    return app
