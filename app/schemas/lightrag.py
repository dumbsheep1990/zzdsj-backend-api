"""
LightRAG数据模型
定义与LightRAG知识图谱交互的数据模型
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class LightRAGMode(str, Enum):
    """LightRAG查询模式"""
    HYBRID = "hybrid"
    LOCAL = "local"
    GLOBAL = "global"
    NAIVE = "naive"
    MIX = "mix"


class GraphReference(BaseModel):
    """知识图谱引用"""
    graph_id: str = Field(..., description="图谱ID")
    priority: int = Field(0, description="优先级")
    config: Optional[Dict[str, Any]] = Field(None, description="配置参数")


class LightRAGQueryRequest(BaseModel):
    """LightRAG知识图谱查询请求"""
    query: str = Field(..., description="查询内容")
    graph_ids: List[str] = Field(..., description="图谱ID列表")
    model_name: Optional[str] = Field(None, description="用于生成回答的模型名称")
    stream: bool = Field(False, description="是否使用流式响应")


class LightRAGModeQueryRequest(BaseModel):
    """LightRAG知识图谱指定模式查询请求"""
    query: str = Field(..., description="查询内容")
    graph_ids: List[str] = Field(..., description="图谱ID列表")
    mode: LightRAGMode = Field(LightRAGMode.HYBRID, description="查询模式")
    return_context_only: bool = Field(False, description="是否只返回上下文")
    bypass_rag: bool = Field(False, description="是否跳过RAG直接查询LLM")
    model_name: Optional[str] = Field(None, description="用于生成回答的模型名称")
    stream: bool = Field(False, description="是否使用流式响应")


class LightRAGResponse(BaseModel):
    """LightRAG知识图谱查询响应"""
    success: bool = Field(..., description="是否成功")
    answer: Optional[str] = Field(None, description="回答内容")
    context: Optional[str] = Field(None, description="上下文信息")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="来源信息")
    error: Optional[str] = Field(None, description="错误信息")


class GraphStatistics(BaseModel):
    """知识图谱统计信息"""
    node_count: int = Field(..., description="节点数量")
    edge_count: int = Field(..., description="边数量")
    document_count: int = Field(..., description="文档数量")
    chunk_count: int = Field(..., description="块数量")
    embedding_model: Optional[str] = Field(None, description="嵌入模型")
    last_updated: Optional[str] = Field(None, description="最后更新时间")
