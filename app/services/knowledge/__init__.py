"""
知识库服务模块
负责知识库管理、搜索和检索功能
"""

from .unified_service import UnifiedKnowledgeService
from .legacy_service import KnowledgeServiceLegacy
from .adapter_service import KnowledgeServiceAdapter
from .hybrid_search_service import HybridSearchService
from .retrieval_service import AdvancedRetrievalService
from .compression_service import ContextCompressionService
from .base_service import KnowledgeBase

__all__ = [
    "UnifiedKnowledgeService",
    "KnowledgeServiceLegacy", 
    "KnowledgeServiceAdapter",
    "HybridSearchService",
    "AdvancedRetrievalService",
    "ContextCompressionService",
    "KnowledgeBase"
]