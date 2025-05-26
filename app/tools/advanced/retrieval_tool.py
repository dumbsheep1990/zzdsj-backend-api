"""
高级检索工具 - 支持多数据源混合检索和重排序的统一接口

该工具支持：
1. 多数据源并行检索
2. 数据融合策略(RRF, 简单加权)
3. 重排序功能，支持多种重排序模型
4. 参数精细控制

可以对接:
- MCP工具接口
- OWL框架工具接口
- AGNO框架工具接口
- 内置函数调用接口
"""

from typing import List, Dict, Any, Optional, Union, Callable
import logging
import json
import time
import asyncio
from pydantic import BaseModel, Field

from app.services.advanced_retrieval_service import (
    get_advanced_retrieval_service, 
    AdvancedRetrievalConfig,
    SourceWeight,
    FusionConfig,
    RerankConfig
)

logger = logging.getLogger(__name__)

class RetrievalToolInput(BaseModel):
    """高级检索工具输入"""
    query: str = Field(..., description="检索查询")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="数据源配置，格式: [{'source_id': 'kb_id', 'weight': 1.0, 'max_results': 10}, ...]")
    fusion: Dict[str, Any] = Field(default_factory=dict, description="融合策略配置，格式: {'strategy': 'reciprocal_rank_fusion', 'rrf_k': 60.0, 'normalize': true}")
    rerank: Dict[str, Any] = Field(default_factory=dict, description="重排序配置，格式: {'enabled': true, 'model_name': 'cross_encoder_miniLM', 'top_n': 50}")
    max_results: int = Field(10, description="最大返回结果数")

class RetrievalToolOutput(BaseModel):
    """高级检索工具输出"""
    results: List[Dict[str, Any]] = Field(..., description="检索结果")
    total: int = Field(..., description="结果总数")
    source_distribution: Dict[str, int] = Field(..., description="数据源分布")
    search_time_ms: float = Field(..., description="检索耗时(毫秒)")

class AdvancedRetrievalTool:
    """高级检索工具 - 可以被各种框架适配"""
    
    def __init__(self, name: str = "advanced_retrieval"):
        """初始化工具"""
        self.name = name
        self.service = get_advanced_retrieval_service()
        
    async def execute(self, params: Union[Dict[str, Any], RetrievalToolInput]) -> Dict[str, Any]:
        """执行工具调用 - 通用接口"""
        try:
            # 处理输入参数
            if isinstance(params, dict):
                query = params.get("query", "")
                if not query:
                    return {"error": "查询字符串不能为空"}
                
                sources = params.get("sources", [])
                fusion = params.get("fusion", {})
                rerank = params.get("rerank", {})
                max_results = params.get("max_results", 10)
            else:
                query = params.query
                sources = params.sources
                fusion = params.fusion
                rerank = params.rerank
                max_results = params.max_results
            
            # 构建配置
            config = AdvancedRetrievalConfig()
            
            # 设置数据源
            if sources:
                config.sources = [SourceWeight(**source) for source in sources]
            
            # 设置融合配置
            if fusion:
                config.fusion = FusionConfig(**fusion)
            
            # 设置重排序配置
            if rerank:
                config.rerank = RerankConfig(**rerank)
            
            # 设置最大结果数
            config.max_results = max_results
            
            # 执行检索
            result = await self.service.retrieve(query, config)
            
            return result
            
        except Exception as e:
            logger.error(f"高级检索工具执行失败: {str(e)}")
            return {
                "error": str(e),
                "query": query if 'query' in locals() else "",
                "results": [],
                "total": 0
            }

    # OWL框架工具接口
    async def run_owl_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """OWL框架工具接口"""
        return await self.execute(params)
    
    # AGNO框架工具接口
    async def run_agno_tool(self, **kwargs) -> Dict[str, Any]:
        """AGNO框架工具接口"""
        return await self.execute(kwargs)
    
    # MCP工具接口
    async def run_mcp_tool(self, query: str, **kwargs) -> Dict[str, Any]:
        """MCP工具接口"""
        params = {"query": query, **kwargs}
        return await self.execute(params)
    
    # 获取工具元数据 (用于动态注册)
    def get_tool_metadata(self) -> Dict[str, Any]:
        """获取工具元数据，用于工具注册"""
        return {
            "name": self.name,
            "description": "高级检索工具，支持多数据源混合检索和重排序",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索查询"
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_id": {"type": "string"},
                                "weight": {"type": "number"},
                                "max_results": {"type": "integer"}
                            }
                        },
                        "description": "数据源配置"
                    },
                    "fusion": {
                        "type": "object",
                        "properties": {
                            "strategy": {"type": "string"},
                            "rrf_k": {"type": "number"},
                            "normalize": {"type": "boolean"}
                        },
                        "description": "融合策略配置"
                    },
                    "rerank": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "model_name": {"type": "string"},
                            "top_n": {"type": "integer"}
                        },
                        "description": "重排序配置"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数"
                    }
                },
                "required": ["query"]
            }
        }

# 创建单例实例
_advanced_retrieval_tool = None

def get_advanced_retrieval_tool() -> AdvancedRetrievalTool:
    """获取高级检索工具实例"""
    global _advanced_retrieval_tool
    if _advanced_retrieval_tool is None:
        _advanced_retrieval_tool = AdvancedRetrievalTool()
    return _advanced_retrieval_tool
