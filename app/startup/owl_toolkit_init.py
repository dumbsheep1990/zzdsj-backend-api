"""
OWL框架工具包初始化模块
系统启动时初始化OWL框架的工具包集成
"""

import logging
import asyncio
from typing import Optional
from sqlalchemy.orm import Session

from app.services.owl_tool_service import OwlToolService
from app.frameworks.owl.toolkit_integrator import OwlToolkitIntegrator
from app.frameworks.owl.toolkits.base import OwlToolkitManager

logger = logging.getLogger(__name__)

async def initialize_owl_toolkits(db: Session) -> Optional[OwlToolkitIntegrator]:
    """初始化OWL框架工具包
    
    Args:
        db: 数据库会话
        
    Returns:
        Optional[OwlToolkitIntegrator]: 工具包集成器实例
    """
    try:
        # 获取服务和管理器实例
        tool_service = OwlToolService(db)
        toolkit_manager = OwlToolkitManager()
        
        # 创建集成器
        integrator = OwlToolkitIntegrator(tool_service, toolkit_manager)
        
        # 初始化集成器
        await integrator.initialize()
        
        # 预加载常用工具包
        common_toolkits = [
            "MathToolkit",
            "SearchToolkit",
            "MemoryToolkit"
        ]
        
        for toolkit_name in common_toolkits:
            try:
                await integrator.load_toolkit(toolkit_name)
                logger.info(f"已预加载工具包: {toolkit_name}")
            except Exception as e:
                logger.warning(f"预加载工具包 {toolkit_name} 失败: {str(e)}")
        
        logger.info("OWL框架工具包初始化完成")
        return integrator
        
    except Exception as e:
        logger.error(f"初始化OWL框架工具包时出错: {str(e)}")
        return None
