"""
文本分析器实现
从原始processor.py重构而来，提供语言检测和元数据提取功能
"""

import re
import logging
from typing import Dict, Any, Optional, List

# 修复导入问题
try:
    from .base import TextAnalyzer, AnalysisResult, TextLanguage, TextProcessingError
except ImportError:
    from base import TextAnalyzer, AnalysisResult, TextLanguage, TextProcessingError

logger = logging.getLogger(__name__)

class ComprehensiveTextAnalyzer(TextAnalyzer):
    """综合文本分析器"""
    
    def __init__(self):
        self._langdetect_available = self._check_langdetect_availability()
    
    def _check_langdetect_availability(self) -> bool:
        """检查langdetect是否可用"""
        try:
            import langdetect
            return True
        except ImportError:
            logger.warning("langdetect库不可用，将使用简单语言检测")
            return False
    
    def analyze(self, text: str) -> AnalysisResult:
        """综合分析文本"""
        if not text:
            return AnalysisResult(
                language="unknown",
                token_count=0,
                char_count=0,
                word_count=0,
                line_count=0,
                metadata={}
            )
        
        # 基本统计
        stats = self.get_basic_stats(text)
        
        # 语言检测
        language = self.detect_language(text)
        
        # 令牌计数估算
        token_count = self._estimate_tokens(text, language)
        
        # 提取元数据
        metadata = self.extract_metadata(text)
        
        return AnalysisResult(
            language=language,
            token_count=token_count,
            char_count=stats["char_count"],
            word_count=stats["word_count"],
            line_count=stats["line_count"],
            metadata=metadata
        )
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        if not text.strip():
            return "unknown"
        
        # 尝试使用langdetect库
        if self._langdetect_available:
            try:
                import langdetect
                detected = langdetect.detect(text)
                return detected
            except Exception as e:
                logger.warning(f"langdetect检测失败: {e}")
        
        # 回退到简单检测
        return self._simple_language_detection(text)
    
    def _simple_language_detection(self, text: str) -> str:
        """简单的语言检测"""
        text_lower = text.lower()
        
        # 统计不同语言的字符
        char_counts = {
            'zh': 0,  # 中文
            'ja': 0,  # 日文
            'ko': 0,  # 韩文
            'ar': 0,  # 阿拉伯文
            'ru': 0,  # 俄文
            'en': 0   # 英文/拉丁文
        }
        
        for char in text:
            # 中文字符 (包括标点)
            if '\u4e00' <= char <= '\u9fff':
                char_counts['zh'] += 1
            # 日文字符
            elif '\u3040' <= char <= '\u30ff':
                char_counts['ja'] += 1
            # 韩文字符
            elif '\uac00' <= char <= '\ud7a3':
                char_counts['ko'] += 1
            # 阿拉伯文字符
            elif '\u0600' <= char <= '\u06ff':
                char_counts['ar'] += 1
            # 西里尔字符 (俄文)
            elif '\u0400' <= char <= '\u04ff':
                char_counts['ru'] += 1
            # 拉丁字符 (英文等)
            elif 'a' <= char.lower() <= 'z':
                char_counts['en'] += 1
        
        # 找到最多的字符类型
        max_lang = max(char_counts, key=char_counts.get)
        max_count = char_counts[max_lang]
        
        # 如果检测到的字符数量太少，返回unknown
        if max_count < len(text) * 0.1:
            return "unknown"
        
        return max_lang
    
    def _estimate_tokens(self, text: str, language: str) -> int:
        """基于语言估算令牌数"""
        # 不同语言的字符到令牌比率
        ratios = {
            'zh': 2.0,
            'ja': 2.5,
            'ko': 2.5,
            'ar': 3.0,
            'ru': 3.5,
            'en': 4.0,
            'unknown': 3.5
        }
        
        ratio = ratios.get(language, 3.5)
        
        # 计算单词数
        words = len(re.findall(r'\S+', text))
        
        # 基于字符数估算
        char_tokens = len(text) / ratio
        
        # 综合估算
        return int((words + char_tokens) / 2)
    
    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """提取文本元数据"""
        metadata = {}
        
        # 文本长度信息
        metadata["length_stats"] = {
            "characters": len(text),
            "characters_no_spaces": len(text.replace(" ", "")),
            "words": len(re.findall(r'\S+', text)),
            "sentences": len(re.findall(r'[.!?。！？]+', text)),
            "paragraphs": len([p for p in text.split('\n\n') if p.strip()])
        }
        
        # 字符类型统计
        metadata["character_types"] = self._analyze_character_types(text)
        
        # 文本结构分析
        metadata["structure"] = self._analyze_text_structure(text)
        
        # 语言特征
        metadata["language_features"] = self._analyze_language_features(text)
        
        return metadata
    
    def _analyze_character_types(self, text: str) -> Dict[str, int]:
        """分析字符类型"""
        counts = {
            "letters": 0,
            "digits": 0,
            "spaces": 0,
            "punctuation": 0,
            "chinese": 0,
            "other": 0
        }
        
        for char in text:
            if char.isalpha():
                if '\u4e00' <= char <= '\u9fff':
                    counts["chinese"] += 1
                else:
                    counts["letters"] += 1
            elif char.isdigit():
                counts["digits"] += 1
            elif char.isspace():
                counts["spaces"] += 1
            elif char in '.,!?;:()[]{}"\'-。，！？；：（）【】{}""''':
                counts["punctuation"] += 1
            else:
                counts["other"] += 1
        
        return counts
    
    def _analyze_text_structure(self, text: str) -> Dict[str, Any]:
        """分析文本结构"""
        lines = text.split('\n')
        
        structure = {
            "total_lines": len(lines),
            "empty_lines": sum(1 for line in lines if not line.strip()),
            "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
            "max_line_length": max(len(line) for line in lines) if lines else 0,
            "has_headers": self._detect_headers(text),
            "has_lists": self._detect_lists(text),
            "has_code": self._detect_code_blocks(text)
        }
        
        return structure
    
    def _detect_headers(self, text: str) -> bool:
        """检测是否包含标题"""
        # 简单的标题检测：以#开头或全大写短行
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#') or (line.isupper() and len(line.split()) <= 5 and len(line) > 0):
                return True
        return False
    
    def _detect_lists(self, text: str) -> bool:
        """检测是否包含列表"""
        list_patterns = [
            r'^\s*[-*+]\s+',  # 无序列表
            r'^\s*\d+\.\s+',  # 有序列表
            r'^\s*[a-zA-Z]\.\s+'  # 字母列表
        ]
        
        lines = text.split('\n')
        for line in lines:
            for pattern in list_patterns:
                if re.match(pattern, line):
                    return True
        return False
    
    def _detect_code_blocks(self, text: str) -> bool:
        """检测是否包含代码块"""
        # 检测代码块标记或缩进代码
        code_indicators = [
            '```',  # Markdown代码块
            '    ',  # 缩进代码
            '\t',   # Tab缩进
            'def ',  # Python函数
            'function ',  # JavaScript函数
            'class ',  # 类定义
            'import ',  # 导入语句
        ]
        
        for indicator in code_indicators:
            if indicator in text:
                return True
        return False
    
    def _analyze_language_features(self, text: str) -> Dict[str, Any]:
        """分析语言特征"""
        features = {
            "has_urls": bool(re.search(r'https?://\S+', text)),
            "has_emails": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
            "has_phone_numbers": bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)),
            "has_dates": bool(re.search(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', text)),
            "has_numbers": bool(re.search(r'\b\d+\b', text)),
            "complexity_score": self._calculate_complexity_score(text)
        }
        
        return features
    
    def _calculate_complexity_score(self, text: str) -> float:
        """计算文本复杂度分数"""
        if not text:
            return 0.0
        
        # 基于多个因素计算复杂度
        factors = {
            "avg_word_length": sum(len(word) for word in re.findall(r'\S+', text)) / max(len(re.findall(r'\S+', text)), 1),
            "sentence_length_variance": self._calculate_sentence_variance(text),
            "vocabulary_richness": self._calculate_vocabulary_richness(text),
            "punctuation_density": len(re.findall(r'[^\w\s]', text)) / len(text),
        }
        
        # 加权平均
        weights = {"avg_word_length": 0.3, "sentence_length_variance": 0.2, 
                  "vocabulary_richness": 0.3, "punctuation_density": 0.2}
        
        score = sum(factors[key] * weights[key] for key in factors)
        return min(score, 1.0)  # 限制在0-1范围
    
    def _calculate_sentence_variance(self, text: str) -> float:
        """计算句子长度方差"""
        sentences = re.split(r'[.!?。！？]+', text)
        lengths = [len(s.strip()) for s in sentences if s.strip()]
        
        if len(lengths) < 2:
            return 0.0
        
        avg_length = sum(lengths) / len(lengths)
        variance = sum((length - avg_length) ** 2 for length in lengths) / len(lengths)
        
        return min(variance / 100, 1.0)  # 归一化
    
    def _calculate_vocabulary_richness(self, text: str) -> float:
        """计算词汇丰富度"""
        words = re.findall(r'\S+', text.lower())
        
        if not words:
            return 0.0
        
        unique_words = set(words)
        richness = len(unique_words) / len(words)
        
        return richness

class SimpleLanguageDetector:
    """简单的语言检测器（独立组件）"""
    
    def __init__(self):
        self.analyzer = ComprehensiveTextAnalyzer()
    
    def detect_language(self, text: str) -> str:
        """检测语言"""
        return self.analyzer.detect_language(text)
    
    def get_confidence(self, text: str) -> Dict[str, float]:
        """获取语言检测置信度（简化版本）"""
        detected = self.detect_language(text)
        
        # 简单的置信度估算
        if detected == "unknown":
            return {"unknown": 1.0}
        else:
            return {detected: 0.8, "unknown": 0.2}

# 工厂函数
def create_text_analyzer() -> TextAnalyzer:
    """创建文本分析器"""
    return ComprehensiveTextAnalyzer()

def create_language_detector() -> SimpleLanguageDetector:
    """创建语言检测器"""
    return SimpleLanguageDetector()

# 便捷函数（向后兼容）
def detect_language(text: str) -> str:
    """向后兼容的语言检测函数"""
    detector = create_language_detector()
    return detector.detect_language(text)

def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """向后兼容的元数据提取函数"""
    analyzer = create_text_analyzer()
    result = analyzer.analyze(text)
    return result.metadata 