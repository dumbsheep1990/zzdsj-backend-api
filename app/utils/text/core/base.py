"""
文本处理抽象基类和接口定义
提供统一的文本处理接口和配置管理
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

class TextLanguage(Enum):
    """支持的文本语言"""
    AUTO = "auto"
    ENGLISH = "en"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    ARABIC = "ar"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"

@dataclass
class TextProcessingConfig:
    """文本处理配置"""
    language: Optional[TextLanguage] = None
    encoding: str = "utf-8"
    normalize_whitespace: bool = True
    remove_extra_spaces: bool = True
    preserve_line_breaks: bool = False
    max_length: Optional[int] = None

@dataclass 
class ChunkConfig:
    """文本分块配置"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    respect_boundaries: bool = True
    boundary_chars: str = ' \n.!?;:-'
    min_chunk_size: int = 100

@dataclass
class TokenConfig:
    """令牌计数配置"""
    model: str = "gpt-3.5-turbo"
    encoding_name: Optional[str] = None
    cache_encodings: bool = True

@dataclass
class AnalysisResult:
    """文本分析结果"""
    language: str
    token_count: int
    char_count: int
    word_count: int
    line_count: int
    metadata: Dict[str, Any]

class TextProcessor(ABC):
    """文本处理器抽象基类"""
    
    def __init__(self, config: Optional[TextProcessingConfig] = None):
        self.config = config or TextProcessingConfig()
    
    @abstractmethod
    def process(self, text: str) -> str:
        """处理文本的核心方法"""
        pass
    
    def clean_text(self, text: str) -> str:
        """清理文本（默认实现）"""
        if not text:
            return ""
        
        # 标准化空白字符
        if self.config.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        # 移除多余空格
        if self.config.remove_extra_spaces:
            text = self._remove_extra_spaces(text)
        
        # 长度限制
        if self.config.max_length and len(text) > self.config.max_length:
            text = text[:self.config.max_length]
        
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """标准化空白字符"""
        import re
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # 移除制表符
        text = text.replace('\t', ' ')
        return text
    
    def _remove_extra_spaces(self, text: str) -> str:
        """移除多余空格"""
        import re
        if self.config.preserve_line_breaks:
            # 保留换行符，只处理空格
            return re.sub(r' +', ' ', text)
        else:
            # 移除多余的空白字符
            return re.sub(r'\s+', ' ', text)

class TextAnalyzer(ABC):
    """文本分析器抽象基类"""
    
    @abstractmethod
    def analyze(self, text: str) -> AnalysisResult:
        """分析文本并返回分析结果"""
        pass
    
    def get_basic_stats(self, text: str) -> Dict[str, int]:
        """获取基本统计信息"""
        import re
        return {
            "char_count": len(text),
            "word_count": len(re.findall(r'\S+', text)),
            "line_count": len(text.split('\n')),
            "paragraph_count": len([p for p in text.split('\n\n') if p.strip()])
        }

class TextChunker(ABC):
    """文本分块器抽象基类"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
    
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        """将文本分割为块"""
        pass
    
    def validate_chunks(self, chunks: List[str]) -> List[str]:
        """验证和过滤块"""
        valid_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) >= self.config.min_chunk_size:
                valid_chunks.append(chunk)
        return valid_chunks

class TokenCounter(ABC):
    """令牌计数器抽象基类"""
    
    def __init__(self, config: Optional[TokenConfig] = None):
        self.config = config or TokenConfig()
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """计算令牌数量"""
        pass
    
    @abstractmethod
    def estimate_cost(self, text: str, cost_per_token: float = 0.0001) -> float:
        """估算成本"""
        pass

class LanguageDetector(ABC):
    """语言检测器抽象基类"""
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        pass
    
    @abstractmethod
    def get_confidence(self, text: str) -> Dict[str, float]:
        """获取语言检测置信度"""
        pass

class KeywordExtractor(ABC):
    """关键词提取器抽象基类"""
    
    @abstractmethod
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        pass
    
    @abstractmethod
    def extract_with_scores(self, text: str, max_keywords: int = 10) -> List[tuple]:
        """提取关键词及其分数"""
        pass

class TextNormalizer(ABC):
    """文本标准化器抽象基类"""
    
    @abstractmethod
    def normalize(self, text: str) -> str:
        """标准化文本"""
        pass
    
    def remove_special_chars(self, text: str, keep_chars: str = "") -> str:
        """移除特殊字符（保留指定字符）"""
        import re
        pattern = f"[^\\w\\s{re.escape(keep_chars)}]"
        return re.sub(pattern, "", text)
    
    def to_lowercase(self, text: str) -> str:
        """转换为小写"""
        return text.lower()
    
    def remove_punctuation(self, text: str) -> str:
        """移除标点符号"""
        import string
        return text.translate(str.maketrans("", "", string.punctuation))

# 工厂类
class TextProcessorFactory:
    """文本处理器工厂"""
    
    _processors = {}
    
    @classmethod
    def register(cls, name: str, processor_class: type):
        """注册处理器"""
        cls._processors[name] = processor_class
    
    @classmethod
    def create(cls, name: str, config: Optional[TextProcessingConfig] = None) -> TextProcessor:
        """创建处理器实例"""
        if name not in cls._processors:
            raise ValueError(f"未知的处理器: {name}")
        return cls._processors[name](config)
    
    @classmethod
    def get_available_processors(cls) -> List[str]:
        """获取可用处理器列表"""
        return list(cls._processors.keys())

# 异常定义
class TextProcessingError(Exception):
    """文本处理异常基类"""
    pass

class InvalidTextError(TextProcessingError):
    """无效文本异常"""
    pass

class ProcessingTimeoutError(TextProcessingError):
    """处理超时异常"""
    pass

class UnsupportedLanguageError(TextProcessingError):
    """不支持的语言异常"""
    pass 