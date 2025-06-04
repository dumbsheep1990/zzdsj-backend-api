"""
知识管理系统的 API 接口规范 和 数据验证规则。
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class KnowledgeBaseType(str, Enum):
    """知识库类型"""
    TRADITIONAL = "traditional"  # 传统向量知识库
    LIGHTRAG = "lightrag"  # LightRAG知识图谱
    HYBRID = "hybrid"  # 混合模式


class ChunkingStrategy(str, Enum):
    """切分策略"""
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"


class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# 基础请求/响应模型
class BaseRequest(BaseModel):
    """基础请求模型"""

    class Config:
        use_enum_values = True


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# 知识库相关模型
class KnowledgeBaseCreate(BaseRequest):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: KnowledgeBaseType = KnowledgeBaseType.TRADITIONAL
    config: Dict[str, Any] = Field(default_factory=dict)

    # 通用配置
    language: str = Field("zh", regex="^(zh|en)$")
    is_active: bool = True
    public_read: bool = False
    public_write: bool = False

    # 传统知识库配置
    chunking_strategy: Optional[ChunkingStrategy] = ChunkingStrategy.SENTENCE
    chunk_size: Optional[int] = Field(1000, ge=100, le=10000)
    chunk_overlap: Optional[int] = Field(200, ge=0, le=1000)
    embedding_model: Optional[str] = "text-embedding-ada-002"
    vector_store: Optional[str] = "chroma"


class DocumentUpload(BaseRequest):
    """文档上传请求"""
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 处理选项
    auto_chunk: bool = True
    auto_vectorize: bool = True
    auto_extract: bool = True  # 自动提取实体和关系

    @validator('content', 'file_url')
    def validate_content_or_file(cls, v, values):
        if not v and not values.get('content') and not values.get('file_url'):
            raise ValueError('必须提供 content 或 file_url')
        return v


class QueryRequest(BaseRequest):
    """查询请求"""
    query: str = Field(..., min_length=1, max_length=1000)
    knowledge_base_ids: List[str] = Field(..., min_items=1)

    # 查询选项
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.7, ge=0, le=1)
    include_metadata: bool = True

    # 高级选项
    use_reranking: bool = False
    use_graph_relations: bool = True  # 对于LightRAG
    query_mode: str = Field("hybrid", regex="^(vector|graph|hybrid)$")