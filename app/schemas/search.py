"""
搜索功能相关的Pydantic模型
定义了搜索请求和响应的数据结构
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
import uuid

class SearchStrategy(str, Enum):
    """混合搜索策略枚举"""
    WEIGHTED_SUM = "weighted_sum"  # 加权求和
    RANK_FUSION = "rank_fusion"    # 排名融合
    CASCADE = "cascade"            # 级联搜索
    VECTOR_ONLY = "vector_only"    # 仅向量搜索
    TEXT_ONLY = "text_only"        # 仅文本搜索

class SearchConfig(BaseModel):
    """搜索配置"""
    query_text: str = Field(..., description="搜索查询文本")
    knowledge_base_ids: Optional[List[str]] = Field(None, description="要搜索的知识库ID列表，为空则搜索所有")
    page: int = Field(1, description="页码，从1开始")
    page_size: int = Field(10, description="每页结果数量")
    vector_weight: float = Field(0.5, description="向量搜索权重，范围0-1")
    text_weight: float = Field(0.5, description="文本搜索权重，范围0-1")
    strategy: SearchStrategy = Field(SearchStrategy.WEIGHTED_SUM, description="混合搜索策略")
    include_metadata: bool = Field(True, description="是否包含元数据")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    score_threshold: Optional[float] = Field(None, description="相似度分数阈值，低于此分数的结果将被过滤")
    
    @validator("vector_weight", "text_weight")
    def validate_weights(cls, v):
        """验证权重范围"""
        if v < 0 or v > 1:
            raise ValueError("权重必须在0到1之间")
        return v

    @validator("page", "page_size")
    def validate_pagination(cls, v):
        """验证分页参数"""
        if v < 1:
            raise ValueError("分页参数必须大于0")
        return v

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询文本")
    knowledge_base_ids: Optional[List[str]] = Field(None, description="知识库ID列表")
    top_k: int = Field(10, description="返回结果的数量")
    strategy: SearchStrategy = Field(SearchStrategy.WEIGHTED_SUM, description="混合搜索策略")
    vector_weight: float = Field(0.5, description="向量搜索权重")
    text_weight: float = Field(0.5, description="文本搜索权重")
    include_content: bool = Field(True, description="是否包含文档内容")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "智能制造的主要应用领域",
                "knowledge_base_ids": ["kb_123", "kb_456"],
                "top_k": 5,
                "strategy": "weighted_sum",
                "vector_weight": 0.7,
                "text_weight": 0.3,
                "include_content": True,
                "filter_metadata": {"category": "manufacturing"}
            }
        }

class SearchResultItem(BaseModel):
    """搜索结果项"""
    id: str = Field(..., description="文档片段ID")
    document_id: str = Field(..., description="文档ID")
    knowledge_base_id: str = Field(..., description="知识库ID")
    content: Optional[str] = Field(None, description="文档内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文档元数据")
    score: float = Field(..., description="相似度分数")
    vector_score: Optional[float] = Field(None, description="向量相似度分数")
    text_score: Optional[float] = Field(None, description="文本相似度分数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "chunk_789",
                "document_id": "doc_123", 
                "knowledge_base_id": "kb_456",
                "content": "智能制造主要应用于汽车、电子、航空航天等领域...",
                "metadata": {"filename": "智能制造白皮书.pdf", "page": 15},
                "score": 0.85,
                "vector_score": 0.82,
                "text_score": 0.91
            }
        }

class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[SearchResultItem] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="结果总数")
    query: str = Field(..., description="原始查询")
    strategy_used: str = Field(..., description="使用的搜索策略")
    search_time_ms: float = Field(..., description="搜索用时（毫秒）")
    knowledge_base_ids: List[str] = Field(..., description="搜索的知识库ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "id": "chunk_789",
                        "document_id": "doc_123",
                        "knowledge_base_id": "kb_456",
                        "content": "智能制造主要应用于汽车、电子、航空航天等领域...",
                        "metadata": {"filename": "智能制造白皮书.pdf", "page": 15},
                        "score": 0.85,
                        "vector_score": 0.82,
                        "text_score": 0.91
                    }
                ],
                "total": 25,
                "query": "智能制造的主要应用领域",
                "strategy_used": "weighted_sum",
                "search_time_ms": 156.32,
                "knowledge_base_ids": ["kb_123", "kb_456"]
            }
        }
