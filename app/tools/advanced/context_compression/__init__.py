"""
上下文压缩工具模块
提供TreeSummarize和CompactAndRefine压缩方法的统一接口
"""

from app.tools.advanced.context_compression.context_compressor import (
    ContextCompressor, 
    CompressionConfig,
    get_context_compressor
)
from app.tools.advanced.context_compression.decorators import (
    compress_retrieval_results,
    compress_final_context
)

# 导出所有类和函数
__all__ = [
    'ContextCompressor', 
    'CompressionConfig', 
    'get_context_compressor',
    'compress_retrieval_results',
    'compress_final_context'
]
