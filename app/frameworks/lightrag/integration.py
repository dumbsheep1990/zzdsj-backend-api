"""LightRAG集成模块
提供与LlamaIndex框架的集成功能，包括工具注册和路由集成
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import logging
from pathlib import Path

try:
    import lightrag
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

# LlamaIndex工具与路由支持
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import BaseQueryEngine

# 内部组件
from app.config import settings
from app.frameworks.lightrag.graph import get_graph_manager
from app.frameworks.lightrag.query_engine import create_lightrag_query_engine
from app.frameworks.llamaindex.adapters.tool_registry import global_tool_registry

logger = logging.getLogger(__name__)


class LightRAGIntegration:
    """集成LightRAG到LlamaIndex路由系统"""
    
    def __init__(self):
        """初始化集成模块"""
        if not LIGHTRAG_AVAILABLE:
            logger.warning("LightRAG依赖未安装，集成功能不可用")
            self.enabled = False
            return
            
        self.enabled = settings.LIGHTRAG_ENABLED
        if not self.enabled:
            logger.info("LightRAG功能已禁用")
            return
            
        self.graph_manager = get_graph_manager()
        logger.info("LightRAG集成模块初始化完成")
    
    def register_tools(self, knowledge_base_id: Optional[int] = None) -> None:
        """注册工具到全局工具注册表
        
        参数:
            knowledge_base_id: 知识库ID，用于生成图谱ID
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            return
            
        # 列出所有图谱
        graph_ids = self.graph_manager.list_graphs()
        
        if knowledge_base_id is not None:
            # 如果指定了知识库ID，添加对应的图谱ID
            kb_graph_id = f"kb_{knowledge_base_id}"
            if kb_graph_id not in graph_ids:
                # 如果图谱不存在，尝试查询KB_前缀的图谱
                kb_alt_graph_id = f"KB_{knowledge_base_id}"
                if kb_alt_graph_id not in graph_ids:
                    # 如果也不存在，则不添加
                    return
                else:
                    kb_graph_id = kb_alt_graph_id
            
            # 添加指定知识库的图谱工具
            self._register_graph_tool(kb_graph_id, knowledge_base_id)
        else:
            # 如果没有指定知识库ID，注册所有图谱工具
            for graph_id in graph_ids:
                # 从图谱ID提取知识库ID（如果可能）
                try:
                    if graph_id.startswith("kb_") or graph_id.startswith("KB_"):
                        kb_id = int(graph_id.split("_")[1])
                    else:
                        kb_id = None
                except:
                    kb_id = None
                    
                self._register_graph_tool(graph_id, kb_id)
    
    def _register_graph_tool(self, graph_id: str, knowledge_base_id: Optional[int] = None) -> None:
        """注册单个图谱的查询工具
        
        参数:
            graph_id: 图谱ID
            knowledge_base_id: 知识库ID，用于工具元数据
        """
        try:
            # 创建查询引擎
            query_engine = create_lightrag_query_engine(
                graph_id=graph_id,
                top_k=5,
                use_graph_relations=True
            )
            
            # 设置工具名称和描述
            if knowledge_base_id is not None:
                tool_name = f"lightrag_kb_{knowledge_base_id}"
                tool_description = f"使用LightRAG知识图谱技术搜索知识库 #{knowledge_base_id} 的文档。该工具利用图谱结构提供更全面的上下文信息。"
            else:
                tool_name = f"lightrag_{graph_id}"
                tool_description = f"使用LightRAG知识图谱技术搜索图谱 '{graph_id}' 中的文档。该工具利用图谱结构提供更全面的上下文信息。"
            
            # 创建工具元数据
            tool_metadata = ToolMetadata(
                name=tool_name,
                description=tool_description
            )
            
            # 创建并注册查询引擎工具
            query_engine_tool = QueryEngineTool(
                query_engine=query_engine,
                metadata=tool_metadata
            )
            
            # 注册到全局工具注册表
            global_tool_registry.register_query_engine_tool(query_engine_tool)
            logger.info(f"注册LightRAG查询工具成功: {tool_name}")
            
        except Exception as e:
            logger.error(f"注册LightRAG查询工具失败: {graph_id}, 错误: {str(e)}")


# 全局单例
_integration_instance = None


def get_lightrag_integration() -> LightRAGIntegration:
    """获取LightRAG集成模块单例"""
    global _integration_instance
    
    if _integration_instance is None:
        _integration_instance = LightRAGIntegration()
        
    return _integration_instance


def register_lightrag_tools(knowledge_base_id: Optional[int] = None) -> None:
    """注册LightRAG工具到全局工具注册表
    
    参数:
        knowledge_base_id: 知识库ID，用于生成图谱ID
    """
    integration = get_lightrag_integration()
    integration.register_tools(knowledge_base_id)