"""LightRAG框架集成模块
提供基于知识图谱的文档处理和检索增强生成功能
"""

from typing import List, Dict, Any, Optional, Union, Callable
import logging

# 尝试导入LightRAG依赖
try:
    import lightrag
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

# 导入配置
from app.config import settings

# 初始化日志
logger = logging.getLogger(__name__)

# 导出核心组件
from app.frameworks.lightrag.client import get_lightrag_client
from app.frameworks.lightrag.graph import get_graph_manager
from app.frameworks.lightrag.document_processor import get_document_processor
from app.frameworks.lightrag.query_engine import create_lightrag_query_engine
from app.frameworks.lightrag.integration import get_lightrag_integration, register_lightrag_tools
from app.frameworks.lightrag.config import lightrag_config

# 检查是否可用
is_available = LIGHTRAG_AVAILABLE and settings.LIGHTRAG_ENABLED

# 打印状态信息
if not LIGHTRAG_AVAILABLE:
    logger.warning("LightRAG依赖未安装, 请安装lightrag-hku包启用知识图谱功能")
elif not settings.LIGHTRAG_ENABLED:
    logger.info("LightRAG功能已禁用, 可在配置中启用")
else:
    logger.info(f"LightRAG功能已启用, 存储类型: {settings.LIGHTRAG_GRAPH_DB_TYPE}")


# 方便的工具函数
def get_client() -> Any:
    """获取LightRAG客户端实例"""
    return get_lightrag_client()


def register_tools(knowledge_base_id: Optional[int] = None) -> None:
    """注册LightRAG工具到全局工具注册表"""
    if is_available:
        register_lightrag_tools(knowledge_base_id)


def get_status() -> Dict[str, Any]:
    """获取LightRAG状态信息"""
    client = get_client()
    status = {
        "available": is_available,
        "installed": LIGHTRAG_AVAILABLE,
        "enabled": settings.LIGHTRAG_ENABLED
    }
    
    if is_available:
        status.update({
            "config": client.get_config(),
            "graphs": client.list_graphs()
        })
        
    return status