"""
OWL框架初始化模块
在系统启动时初始化OWL框架及其工具集成
"""

import logging
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.core.owl_controller import OwlController
from app.startup.owl_toolkit_init import initialize_owl_toolkits

logger = logging.getLogger(__name__)

def register_owl_init(app: FastAPI) -> None:
    """
    注册OWL框架初始化事件
    
    Args:
        app: FastAPI应用实例
    """
    @app.on_event("startup")
    async def init_owl_framework():
        """初始化OWL框架"""
        try:
            logger.info("正在初始化OWL框架...")
            
            # 获取数据库会话
            db = next(get_db())
            
            # 初始化OWL控制器
            controller = OwlController(db)
            await controller.initialize()
            
            # 初始化OWL工具包
            await initialize_owl_toolkits(db)
            
            logger.info("OWL框架初始化完成")
        except Exception as e:
            logger.error(f"初始化OWL框架时出错: {str(e)}", exc_info=True)
