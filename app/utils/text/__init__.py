"""
Text 模块 - 文本处理工具集
提供统一的文本处理、分析、分块和令牌计数功能

重构后的模块结构：
- core/: 核心组件 (base, tokenizer, chunker, analyzer)
- embedding/: 嵌入向量处理 (待重构)
- templating/: 模板渲染 (待重构)
- keywords/: 关键词提取 (待重构)
- utils/: 工具函数 (待添加)
"""

# 核心基类和配置
from .core.base import (
    # 枚举和配置
    TextLanguage,
    TextProcessingConfig,
    ChunkConfig,
    TokenConfig,
    AnalysisResult,
    
    # 抽象基类
    TextProcessor,
    TextAnalyzer,
    TextChunker,
    TokenCounter,
    LanguageDetector,
    KeywordExtractor,
    TextNormalizer,
    
    # 工厂
    TextProcessorFactory,
    
    # 异常
    TextProcessingError,
    InvalidTextError,
    ProcessingTimeoutError,
    UnsupportedLanguageError,
)

# 令牌计数器
from .core.tokenizer import (
    TikTokenCounter,
    SimpleTokenCounter,
    create_token_counter,
    count_tokens,  # 向后兼容
)

# 文本分块器
from .core.chunker import (
    SmartTextChunker,
    SemanticChunker,
    FixedSizeChunker,
    create_chunker,
    chunk_text,  # 向后兼容
)

# 文本分析器
from .core.analyzer import (
    ComprehensiveTextAnalyzer,
    SimpleLanguageDetector,
    create_text_analyzer,
    create_language_detector,
    detect_language,  # 向后兼容
    extract_metadata_from_text,  # 向后兼容
)

# 原有模块 (待重构)
from .embedding_utils import (
    get_embedding,
    batch_get_embeddings,
)

from .template_renderer import (
    render_assistant_page,
)

# 原有处理器的向后兼容接口
from .processor import (
    # 只导入实际存在的函数
    count_tokens as processor_count_tokens,
    chunk_text as processor_chunk_text,
    detect_language as processor_detect_language,
    extract_metadata_from_text as processor_extract_metadata_from_text,
    extract_keywords as processor_extract_keywords,
)

# 添加缺失的向后兼容函数
def clean_text(text: str) -> str:
    """向后兼容的文本清理函数"""
    from .core.base import TextProcessingConfig, TextProcessor
    
    class SimpleTextProcessor(TextProcessor):
        def process(self, text: str) -> str:
            return self.clean_text(text)
    
    processor = SimpleTextProcessor()
    return processor.clean_text(text)

def tokenize_text(text: str) -> list:
    """向后兼容的文本分词函数"""
    import re
    # 简单的分词实现
    return re.findall(r'\S+', text)

# 统一接口函数
def process_text(
    text: str,
    operation: str = "analyze",
    config: dict = None
) -> dict:
    """
    统一的文本处理接口
    
    Args:
        text: 输入文本
        operation: 操作类型 ("analyze", "chunk", "count_tokens", "detect_language")
        config: 配置参数
    
    Returns:
        处理结果字典
    """
    config = config or {}
    
    if operation == "analyze":
        analyzer = create_text_analyzer()
        result = analyzer.analyze(text)
        return {
            "language": result.language,
            "token_count": result.token_count,
            "char_count": result.char_count,
            "word_count": result.word_count,
            "line_count": result.line_count,
            "metadata": result.metadata,
        }
    
    elif operation == "chunk":
        chunk_config = ChunkConfig(**config)
        chunker = create_chunker("smart", chunk_config)
        chunks = chunker.chunk(text)
        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "total_length": sum(len(chunk) for chunk in chunks),
        }
    
    elif operation == "count_tokens":
        token_config = TokenConfig(**config)
        counter = create_token_counter(config=token_config)
        token_count = counter.count_tokens(text)
        cost = counter.estimate_cost(text)
        return {
            "token_count": token_count,
            "estimated_cost": cost,
            "model": token_config.model,
        }
    
    elif operation == "detect_language":
        detector = create_language_detector()
        language = detector.detect_language(text)
        confidence = detector.get_confidence(text)
        return {
            "language": language,
            "confidence": confidence,
        }
    
    else:
        raise ValueError(f"不支持的操作类型: {operation}")

# 批处理接口
def batch_process_texts(
    texts: list,
    operation: str = "analyze",
    config: dict = None
) -> list:
    """
    批量文本处理接口
    
    Args:
        texts: 文本列表
        operation: 操作类型
        config: 配置参数
    
    Returns:
        处理结果列表
    """
    return [process_text(text, operation, config) for text in texts]

# 高级分析接口
def analyze_text_comprehensive(text: str) -> dict:
    """
    综合文本分析（包含所有信息）
    
    Args:
        text: 输入文本
    
    Returns:
        完整的分析结果
    """
    analyzer = create_text_analyzer()
    result = analyzer.analyze(text)
    
    # 添加分块信息
    chunker = create_chunker("smart")
    chunks = chunker.chunk(text)
    
    # 添加令牌信息
    counter = create_token_counter()
    
    return {
        "basic_stats": {
            "language": result.language,
            "char_count": result.char_count,
            "word_count": result.word_count,
            "line_count": result.line_count,
            "token_count": result.token_count,
        },
        "metadata": result.metadata,
        "chunking": {
            "chunk_count": len(chunks),
            "chunks": chunks[:5],  # 只返回前5个块作为示例
            "avg_chunk_length": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
        },
        "cost_estimation": {
            "estimated_cost": counter.estimate_cost(text),
            "model": counter.config.model,
        }
    }

# 导出所有公共接口
__all__ = [
    # 配置和枚举
    "TextLanguage",
    "TextProcessingConfig", 
    "ChunkConfig",
    "TokenConfig",
    "AnalysisResult",
    
    # 核心组件
    "TikTokenCounter",
    "SimpleTokenCounter", 
    "SmartTextChunker",
    "SemanticChunker",
    "FixedSizeChunker",
    "ComprehensiveTextAnalyzer",
    "SimpleLanguageDetector",
    
    # 工厂函数
    "create_token_counter",
    "create_chunker",
    "create_text_analyzer",
    "create_language_detector",
    
    # 统一接口
    "process_text",
    "batch_process_texts", 
    "analyze_text_comprehensive",
    
    # 向后兼容接口
    "count_tokens",
    "chunk_text",
    "detect_language",
    "extract_metadata_from_text",
    "clean_text",
    "extract_keywords",
    "tokenize_text",
    "get_embedding",
    "batch_get_embeddings",
    "render_assistant_page",
    
    # 异常
    "TextProcessingError",
    "InvalidTextError",
    "ProcessingTimeoutError",
    "UnsupportedLanguageError",
]

# 向后兼容的函数别名
# 使用重构后的实现，但保持原有接口
extract_keywords = processor_extract_keywords
