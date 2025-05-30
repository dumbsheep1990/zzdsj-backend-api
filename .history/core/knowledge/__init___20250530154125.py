"""
Knowledge Core Layer - 知识库核心业务逻辑层

本模块提供知识库管理的核心业务逻辑，包括：
- 知识库管理 (KnowledgeBaseManager)
- 文档处理 (DocumentProcessor) 
- 文档分块 (ChunkingManager)
- 向量存储管理 (VectorManager)
- 检索管理 (RetrievalManager)

遵循分层架构原则：
- 封装核心业务逻辑
- 不直接依赖外部框架
- 提供统一的接口
- 支持依赖注入
"""

from .knowledge_manager import KnowledgeBaseManager
from .document_processor import DocumentProcessor
from .chunking_manager import ChunkingManager
from .vector_manager import VectorManager
from .retrieval_manager import RetrievalManager

__all__ = [
    "KnowledgeBaseManager",
    "DocumentProcessor", 
    "ChunkingManager",
    "VectorManager",
    "RetrievalManager"
] 