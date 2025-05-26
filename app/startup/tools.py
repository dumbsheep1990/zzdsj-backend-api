"""
工具系统启动配置

初始化和注册系统工具。
"""

import logging
from fastapi import FastAPI
from typing import Dict, Any

logger = logging.getLogger(__name__)

def init_tools(app: FastAPI, settings: Dict[str, Any]) -> None:
    """初始化工具系统
    
    Args:
        app: FastAPI应用实例
        settings: 系统设置
    """
    logger.info("正在初始化工具系统...")
    
    # 注册基础工具
    try:
        from app.tools.base.register import register_base_tools
        register_base_tools(app, settings)
        logger.info("基础工具注册完成")
    except Exception as e:
        logger.error(f"基础工具注册失败: {str(e)}")
    
    # 在这里可以添加其他工具的初始化代码
    
    logger.info("工具系统初始化完成")
