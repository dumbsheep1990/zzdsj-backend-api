"""
LlamaIndex适配器：基于现有LlamaIndex组件实现统一文本处理接口
复用系统中已有的成熟文档处理组件，避免重复开发
"""

import logging
from typing import List, Dict, Any, Optional, Union, Callable
import asyncio
import time
from datetime import datetime

from app.utils.text.core.base import (
    TextChunker, 
    TokenCounter,
    ChunkConfig, 
    TokenConfig,
    TextProcessingError
)

# 导入现有的LlamaIndex组件
from app.tools.base.document_chunking import (
    DocumentChunkingTool,
    ChunkingConfig,
    ChunkingResult,
    DocumentChunk
)
from app.frameworks.llamaindex.document_processor import (
    DocumentSplitterFactory,
    SplitterType
)

logger = logging.getLogger(__name__)


class LlamaIndexTextChunker(TextChunker):
    """
    基于LlamaIndex的文本分块器适配器
    复用现有的DocumentChunkingTool，提供统一接口
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        初始化LlamaIndex文本分块器
        
        参数:
            config: 文本分块配置
        """
        super().__init__(config)
        self.chunking_tool = DocumentChunkingTool()
        self.progress_callback: Optional[Callable[[str, float], None]] = None
        
        logger.info(f"初始化LlamaIndex文本分块器，块大小: {self.config.chunk_size}")
    
    def chunk(self, text: str) -> List[str]:
        """
        将文本分割为块
        
        参数:
            text: 要分割的文本
            
        返回:
            文本块列表
        """
        if not text or not text.strip():
            return []
        
        try:
            # 转换配置格式
            chunking_config = self._convert_config()
            
            # 执行分块
            result = self.chunking_tool.chunk_document(text, chunking_config)
            
            # 提取文本内容
            chunks = [chunk.content for chunk in result.chunks]
            
            # 应用基类验证
            validated_chunks = self.validate_chunks(chunks)
            
            logger.info(f"文本分块完成: {len(validated_chunks)}个块, 策略: {chunking_config.strategy}")
            
            return validated_chunks
            
        except Exception as e:
            logger.error(f"LlamaIndex文本分块失败: {str(e)}")
            raise TextProcessingError(f"文本分块失败: {str(e)}") from e
    
    async def chunk_async(
        self, 
        text: str, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> List[str]:
        """
        异步文本分块
        
        参数:
            text: 要分割的文本
            progress_callback: 进度回调函数
            
        返回:
            文本块列表
        """
        if not text or not text.strip():
            return []
        
        try:
            # 设置进度回调
            if progress_callback:
                self.chunking_tool.set_progress_callback(progress_callback)
            
            # 转换配置
            chunking_config = self._convert_config()
            
            # 启动异步分块
            task_id = await self.chunking_tool.chunk_document_async(text, chunking_config)
            
            # 等待完成并获取结果（这里需要根据实际实现调整）
            # 注意：这是一个简化的实现，实际可能需要轮询任务状态
            await asyncio.sleep(0.1)  # 简单等待
            
            # 执行同步分块作为后备
            return self.chunk(text)
            
        except Exception as e:
            logger.error(f"异步文本分块失败: {str(e)}")
            raise TextProcessingError(f"异步文本分块失败: {str(e)}") from e
    
    def chunk_with_metadata(self, text: str) -> List[Dict[str, Any]]:
        """
        分块文本并返回详细元数据
        
        参数:
            text: 要分割的文本
            
        返回:
            包含文本和元数据的字典列表
        """
        if not text or not text.strip():
            return []
        
        try:
            # 转换配置
            chunking_config = self._convert_config()
            
            # 执行分块
            result = self.chunking_tool.chunk_document(text, chunking_config)
            
            # 转换为详细格式
            chunks_with_meta = []
            for i, chunk in enumerate(result.chunks):
                chunk_dict = chunk.to_dict()
                chunk_dict.update({
                    "index": i,
                    "strategy_used": result.strategy_used,
                    "processing_time": result.processing_time,
                    "config_used": {
                        "chunk_size": chunking_config.chunk_size,
                        "chunk_overlap": chunking_config.chunk_overlap,
                        "strategy": chunking_config.strategy
                    }
                })
                chunks_with_meta.append(chunk_dict)
            
            return chunks_with_meta
            
        except Exception as e:
            logger.error(f"文本分块（含元数据）失败: {str(e)}")
            raise TextProcessingError(f"文本分块失败: {str(e)}") from e
    
    def get_optimal_chunk_size(self, text: str, target_chunks: int = 10) -> int:
        """
        根据文本长度和目标块数计算最优块大小
        
        参数:
            text: 源文本
            target_chunks: 目标块数量
            
        返回:
            建议的块大小
        """
        if not text:
            return self.config.chunk_size
        
        text_length = len(text)
        estimated_chunk_size = text_length // target_chunks
        
        # 考虑重叠
        if self.config.chunk_overlap > 0:
            estimated_chunk_size = int(estimated_chunk_size * 1.2)
        
        # 限制在合理范围内
        min_size = max(self.config.min_chunk_size, 200)
        max_size = min(self.config.max_chunk_size or 5000, 5000)
        
        optimal_size = max(min_size, min(estimated_chunk_size, max_size))
        
        logger.info(f"计算最优块大小: {optimal_size} (文本长度: {text_length}, 目标块数: {target_chunks})")
        
        return optimal_size
    
    def _convert_config(self) -> ChunkingConfig:
        """
        将标准ChunkConfig转换为LlamaIndex的ChunkingConfig
        
        返回:
            LlamaIndex的切分配置
        """
        # 映射切分策略
        strategy_mapping = {
            "sentence": "sentence",
            "token": "token", 
            "semantic": "semantic",
            "window": "window",
            "recursive": "recursive",
            "hybrid": "hybrid"
        }
        
        # 默认策略
        strategy = "sentence"
        if hasattr(self.config, 'strategy'):
            strategy = strategy_mapping.get(getattr(self.config, 'strategy', 'sentence'), 'sentence')
        
        return ChunkingConfig(
            strategy=strategy,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            min_chunk_size=self.config.min_chunk_size,
            preserve_structure=self.config.respect_boundaries,
            language="zh",  # 可以根据需要动态检测
            include_metadata=True,
            include_prev_next_rel=True
        )
    
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
        self.chunking_tool.set_progress_callback(callback)
    
    def get_supported_strategies(self) -> List[str]:
        """获取支持的分块策略列表"""
        return ["sentence", "token", "semantic", "window", "recursive", "hybrid"]


class LlamaIndexTokenCounter(TokenCounter):
    """
    基于LlamaIndex和tiktoken的令牌计数器
    提供精确的令牌计数和成本估算
    """
    
    def __init__(self, config: Optional[TokenConfig] = None):
        """
        初始化令牌计数器
        
        参数:
            config: 令牌计数配置
        """
        super().__init__(config)
        self._encodings_cache = {} if config and config.cache_encodings else None
        
        logger.info(f"初始化LlamaIndex令牌计数器，模型: {self.config.model}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算令牌数量
        
        参数:
            text: 要计算的文本
            
        返回:
            令牌数量
        """
        if not text:
            return 0
        
        try:
            # 尝试使用tiktoken进行精确计数
            import tiktoken
            
            encoding = self._get_encoding()
            tokens = encoding.encode(text)
            
            return len(tokens)
            
        except ImportError:
            logger.warning("tiktoken未安装，使用近似计数")
            return self._approximate_count(text)
        except Exception as e:
            logger.error(f"令牌计数失败: {str(e)}")
            return self._approximate_count(text)
    
    def estimate_cost(self, text: str, cost_per_token: float = 0.0001) -> float:
        """
        估算处理成本
        
        参数:
            text: 要处理的文本
            cost_per_token: 每个令牌的成本
            
        返回:
            估算成本
        """
        token_count = self.count_tokens(text)
        cost = token_count * cost_per_token
        
        logger.debug(f"成本估算: {token_count}个令牌 × {cost_per_token} = ${cost:.6f}")
        
        return cost
    
    def batch_count_tokens(self, texts: List[str]) -> List[int]:
        """
        批量计算令牌数量
        
        参数:
            texts: 文本列表
            
        返回:
            令牌数量列表
        """
        if not texts:
            return []
        
        try:
            import tiktoken
            
            encoding = self._get_encoding()
            token_counts = []
            
            for text in texts:
                if text:
                    tokens = encoding.encode(text)
                    token_counts.append(len(tokens))
                else:
                    token_counts.append(0)
            
            return token_counts
            
        except ImportError:
            logger.warning("tiktoken未安装，使用近似计数")
            return [self._approximate_count(text) for text in texts]
        except Exception as e:
            logger.error(f"批量令牌计数失败: {str(e)}")
            return [self._approximate_count(text) for text in texts]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        返回:
            模型信息字典
        """
        try:
            import tiktoken
            
            encoding = self._get_encoding()
            
            return {
                "model": self.config.model,
                "encoding_name": encoding.name,
                "max_tokens": self._get_model_max_tokens(),
                "supports_tiktoken": True
            }
            
        except ImportError:
            return {
                "model": self.config.model,
                "encoding_name": "approximate",
                "max_tokens": self._get_model_max_tokens(),
                "supports_tiktoken": False
            }
    
    def _get_encoding(self):
        """获取编码器"""
        import tiktoken
        
        if self._encodings_cache and self.config.model in self._encodings_cache:
            return self._encodings_cache[self.config.model]
        
        try:
            # 尝试使用模型特定的编码
            encoding = tiktoken.encoding_for_model(self.config.model)
        except KeyError:
            # 如果模型不支持，使用默认编码
            if self.config.encoding_name:
                encoding = tiktoken.get_encoding(self.config.encoding_name)
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
        
        # 缓存编码器
        if self._encodings_cache is not None:
            self._encodings_cache[self.config.model] = encoding
        
        return encoding
    
    def _approximate_count(self, text: str) -> int:
        """近似令牌计数（tiktoken不可用时的后备方案）"""
        import re
        
        # 分别处理中文和英文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        
        # 中文字符通常1个字符≈1个令牌
        # 英文文本平均4个字符≈1个令牌
        estimated_tokens = chinese_chars + (other_chars // 4)
        
        return max(estimated_tokens, len(text.split()) // 1.3)
    
    def _get_model_max_tokens(self) -> int:
        """获取模型最大令牌数"""
        model_limits = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "text-davinci-003": 4097,
            "text-curie-001": 2049,
            "text-babbage-001": 2049,
            "text-ada-001": 2049
        }
        
        # 检查完整匹配
        if self.config.model in model_limits:
            return model_limits[self.config.model]
        
        # 检查前缀匹配
        for model_prefix, limit in model_limits.items():
            if self.config.model.startswith(model_prefix):
                return limit
        
        # 默认值
        return 4096 