"""
智能体记忆系统 - 启动初始化

提供记忆系统的启动初始化功能。
"""

from fastapi import FastAPI
from app.memory.manager import get_memory_manager
import logging

logger = logging.getLogger(__name__)

async def init_memory_system(app: FastAPI):
    """初始化记忆系统"""
    logger.info("正在初始化记忆系统...")
    
    # 获取记忆管理器
    memory_manager = get_memory_manager()
    
    # 启动定期清理任务
    from app.config import settings
    cleanup_interval = getattr(settings, "MEMORY_CLEANUP_INTERVAL", 3600)
    await memory_manager.start_cleanup_task(cleanup_interval)
    
    # 注册关闭事件
    @app.on_event("shutdown")
    async def shutdown_memory_system():
        logger.info("正在关闭记忆系统...")
        await memory_manager.stop_cleanup_task()
    
    logger.info(f"记忆系统初始化完成，清理间隔: {cleanup_interval}秒")
    
    return memory_manager
