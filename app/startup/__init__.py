"""
应用启动模块
管理应用程序启动时需要执行的任务和服务
"""

from app.startup.searxng_service import register_searxng_startup

__all__ = ["register_searxng_startup"]
