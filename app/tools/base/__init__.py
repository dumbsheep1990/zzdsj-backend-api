"""
基础工具包

提供系统级别的基础工具实现，包括子问题拆分和问答路由绑定等功能。
"""

from app.tools.base.subquestion_decomposer import SubQuestionDecomposer
from app.tools.base.qa_router import QARouter
from app.tools.base.register import register_base_tools

from .document_chunking import (
    ChunkingConfig,
    DocumentChunk,
    ChunkingResult,
    DocumentChunker,
    create_chunker,
    chunk_text
)

from .agno_document_chunking import (
    AgnoChunkingConfig,
    AgnoDocumentChunk, 
    AgnoChunkingResult,
    AgnoDocumentChunker,
    AgnoChunkingStrategy,
    agno_chunk_text,
    create_agno_chunker,
    get_agno_chunker
)

__all__ = [
    # 原始版本（保持向后兼容）
    "ChunkingConfig",
    "DocumentChunk", 
    "ChunkingResult",
    "DocumentChunker",
    "create_chunker",
    "chunk_text",
    
    # Agno原生版本（推荐使用）
    "AgnoChunkingConfig",
    "AgnoDocumentChunk",
    "AgnoChunkingResult", 
    "AgnoDocumentChunker",
    "AgnoChunkingStrategy",
    "agno_chunk_text",
    "create_agno_chunker",
    "get_agno_chunker",
]
