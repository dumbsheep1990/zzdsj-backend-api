"""
SearxNG服务启动模块
负责在应用启动时自动部署和注册SearxNG搜索引擎服务
"""

import asyncio
import logging
from fastapi import FastAPI
from app.core.searxng_manager import get_searxng_manager
from app.config import settings

logger = logging.getLogger(__name__)

async def deploy_searxng():
    """部署SearxNG搜索引擎服务"""
    if not settings.searxng.enabled:
        logger.info("SearxNG搜索引擎服务已在配置中禁用")
        return
    
    if not settings.searxng.auto_deploy:
        logger.info("SearxNG搜索引擎自动部署已在配置中禁用")
        return
    
    logger.info("开始自动部署SearxNG搜索引擎服务...")
    searxng_manager = get_searxng_manager()
    
    # 异步部署SearxNG
    deployment_success = await searxng_manager.deploy()
    
    if deployment_success:
        logger.info("SearxNG搜索引擎服务已成功部署")
    else:
        logger.error("SearxNG搜索引擎服务部署失败")
    
    return deployment_success

async def start_heartbeat_task():
    """启动心跳任务，定期向Nacos发送心跳"""
    if not settings.searxng.enabled:
        return
    
    searxng_manager = get_searxng_manager()
    
    while True:
        try:
            await searxng_manager.send_heartbeat()
        except Exception as e:
            logger.error(f"发送SearxNG心跳时出错: {str(e)}")
        finally:
            # 每30秒发送一次心跳
            await asyncio.sleep(30)

def register_searxng_startup(app: FastAPI):
    """
    注册SearxNG服务启动事件处理器
    
    参数:
        app: FastAPI应用实例
    """
    @app.on_event("startup")
    async def startup_searxng_service():
        """应用启动时部署SearxNG服务"""
        if settings.searxng.enabled:
            # 部署SearxNG服务
            await deploy_searxng()
            
            # 启动心跳任务
            asyncio.create_task(start_heartbeat_task())
    
    @app.on_event("shutdown")
    async def shutdown_searxng_service():
        """应用关闭时停止SearxNG服务"""
        if settings.searxng.enabled:
            logger.info("应用关闭，停止SearxNG服务...")
            searxng_manager = get_searxng_manager()
            await searxng_manager.stop()
