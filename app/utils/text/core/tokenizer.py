"""
令牌计数器实现
从原始processor.py重构而来，优化了性能和缓存机制
"""

import logging
from typing import Dict, Optional, List

# 修复导入问题
try:
    from .base import TokenCounter, TokenConfig, TextProcessingError
except ImportError:
    # 如果相对导入失败，尝试直接导入
    from base import TokenCounter, TokenConfig, TextProcessingError

logger = logging.getLogger(__name__)

class TikTokenCounter(TokenCounter):
    """基于tiktoken的令牌计数器"""
    
    def __init__(self, config: Optional[TokenConfig] = None):
        super().__init__(config)
        self._encoding_cache: Dict[str, any] = {}
        self._tiktoken_available = self._check_tiktoken_availability()
    
    def _check_tiktoken_availability(self) -> bool:
        """检查tiktoken是否可用"""
        try:
            import tiktoken
            return True
        except ImportError:
            logger.warning("tiktoken库不可用，将使用近似计数方法")
            return False
    
    def _get_encoding(self, model: str):
        """获取或缓存编码器"""
        if not self._tiktoken_available:
            return None
        
        if model in self._encoding_cache:
            return self._encoding_cache[model]
        
        try:
            import tiktoken
            
            # 根据模型选择编码
            if model.startswith("gpt-4"):
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif model.startswith("gpt-3.5"):
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            elif self.config.encoding_name:
                encoding = tiktoken.get_encoding(self.config.encoding_name)
            else:
                # 默认使用cl100k_base
                encoding = tiktoken.get_encoding("cl100k_base")
            
            if self.config.cache_encodings:
                self._encoding_cache[model] = encoding
            
            return encoding
        except Exception as e:
            logger.error(f"获取编码器失败: {e}")
            return None
    
    def count_tokens(self, text: str) -> int:
        """计算令牌数量"""
        if not text:
            return 0
        
        # 尝试使用tiktoken进行精确计数
        encoding = self._get_encoding(self.config.model)
        if encoding:
            try:
                return len(encoding.encode(text))
            except Exception as e:
                logger.error(f"tiktoken计数失败: {e}")
        
        # 回退到近似计数
        return self._approximate_count(text)
    
    def _approximate_count(self, text: str) -> int:
        """近似令牌计数（当tiktoken不可用时）"""
        import re
        
        # 计算单词数
        words = len(re.findall(r'\S+', text))
        
        # 计算字符数（每4个字符约等于1个令牌）
        char_tokens = len(text) // 4
        
        # 取较大值作为保守估计
        return max(words, char_tokens)
    
    def estimate_cost(self, text: str, cost_per_token: float = 0.0001) -> float:
        """估算API调用成本"""
        token_count = self.count_tokens(text)
        return token_count * cost_per_token
    
    def batch_count_tokens(self, texts: List[str]) -> List[int]:
        """批量计算令牌数量"""
        return [self.count_tokens(text) for text in texts]
    
    def get_model_limits(self) -> Dict[str, int]:
        """获取模型的令牌限制"""
        limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "text-embedding-ada-002": 8191,
            "text-embedding-3-small": 8191,
            "text-embedding-3-large": 8191,
        }
        return limits.get(self.config.model, 4096)
    
    def check_text_length(self, text: str, max_tokens: Optional[int] = None) -> Dict[str, any]:
        """检查文本长度是否超过模型限制"""
        token_count = self.count_tokens(text)
        model_limit = max_tokens or self.get_model_limits()
        
        return {
            "token_count": token_count,
            "model_limit": model_limit,
            "is_within_limit": token_count <= model_limit,
            "excess_tokens": max(0, token_count - model_limit),
            "utilization_ratio": token_count / model_limit
        }

class SimpleTokenCounter(TokenCounter):
    """简单的令牌计数器（不依赖外部库）"""
    
    def __init__(self, config: Optional[TokenConfig] = None):
        super().__init__(config)
        # 不同语言的平均字符到令牌比率
        self._char_to_token_ratios = {
            "en": 4.0,  # 英文
            "zh": 2.0,  # 中文
            "ja": 2.5,  # 日文
            "ko": 2.5,  # 韩文
            "ar": 3.0,  # 阿拉伯文
            "default": 3.5
        }
    
    def count_tokens(self, text: str) -> int:
        """基于启发式方法计算令牌数量"""
        if not text:
            return 0
        
        # 检测语言并选择合适的比率
        language = self._detect_simple_language(text)
        ratio = self._char_to_token_ratios.get(language, self._char_to_token_ratios["default"])
        
        # 计算单词数
        import re
        words = len(re.findall(r'\S+', text))
        
        # 基于字符数估算
        char_tokens = len(text) / ratio
        
        # 考虑标点符号和特殊字符
        special_chars = len(re.findall(r'[^\w\s]', text))
        
        # 综合估算
        estimated_tokens = int((words + char_tokens + special_chars * 0.5) / 2)
        
        return max(estimated_tokens, 1)
    
    def batch_count_tokens(self, texts: List[str]) -> List[int]:
        """批量计算令牌数量"""
        return [self.count_tokens(text) for text in texts]
    
    def _detect_simple_language(self, text: str) -> str:
        """简单的语言检测"""
        text = text.lower()
        
        # 中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh'
        # 日文字符
        elif any('\u3040' <= char <= '\u30ff' for char in text):
            return 'ja'
        # 韩文字符
        elif any('\uac00' <= char <= '\ud7a3' for char in text):
            return 'ko'
        # 西里尔字符（俄语）
        elif any('\u0400' <= char <= '\u04ff' for char in text):
            return 'ru'
        # 阿拉伯字符
        elif any('\u0600' <= char <= '\u06ff' for char in text):
            return 'ar'
        # 默认为英语
        else:
            return 'en'
    
    def estimate_cost(self, text: str, cost_per_token: float = 0.0001) -> float:
        """估算成本"""
        token_count = self.count_tokens(text)
        return token_count * cost_per_token

# 工厂函数
def create_token_counter(use_tiktoken: bool = True, config: Optional[TokenConfig] = None) -> TokenCounter:
    """创建令牌计数器"""
    if use_tiktoken:
        try:
            import tiktoken
            return TikTokenCounter(config)
        except ImportError:
            logger.warning("tiktoken不可用，使用简单计数器")
            return SimpleTokenCounter(config)
    else:
        return SimpleTokenCounter(config)

# 便捷函数（向后兼容）
def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """向后兼容的令牌计数函数"""
    config = TokenConfig(model=model)
    counter = create_token_counter(config=config)
    return counter.count_tokens(text) 