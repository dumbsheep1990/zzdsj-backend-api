"""
应用启动模块
管理应用程序启动时需要执行的任务和服务
"""

from app.startup.searxng_service import register_searxng_startup
from app.startup.context_compression import register_context_compression

__all__ = ["register_searxng_startup", "register_context_compression"]
