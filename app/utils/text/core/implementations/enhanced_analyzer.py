"""
增强文本分析器：提供全面的文本质量分析和内容理解
集成多种NLP技术，提供深度文本洞察
"""

import logging
import re
import unicodedata
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import Counter
from dataclasses import dataclass
import math

from app.utils.text.core.base import TextAnalyzer, AnalysisConfig, TextProcessingError

logger = logging.getLogger(__name__)


@dataclass
class TextStatistics:
    """文本统计信息"""
    char_count: int
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_word_length: float
    avg_sentence_length: float
    readability_score: float
    complexity_score: float


@dataclass
class LanguageDistribution:
    """语言分布信息"""
    primary_language: str
    confidence: float
    language_ratios: Dict[str, float]
    mixed_language: bool


class EnhancedTextAnalyzer(TextAnalyzer):
    """
    增强文本分析器
    提供文本质量、复杂度、可读性等多维度分析
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        初始化文本分析器
        
        参数:
            config: 分析配置
        """
        super().__init__(config)
        self._init_patterns()
        
        logger.info("初始化增强文本分析器")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        全面分析文本
        
        参数:
            text: 要分析的文本
            
        返回:
            分析结果字典
        """
        if not text or not text.strip():
            return self._empty_analysis()
        
        try:
            analysis = {
                "basic_stats": self._analyze_basic_stats(text),
                "language_analysis": self._analyze_language(text),
                "quality_metrics": self._analyze_quality(text),
                "structure_analysis": self._analyze_structure(text),
                "content_features": self._analyze_content_features(text),
                "readability": self._analyze_readability(text),
                "sentiment_hints": self._analyze_sentiment_hints(text)
            }
            
            # 计算综合评分
            analysis["overall_score"] = self._calculate_overall_score(analysis)
            
            logger.debug(f"文本分析完成: {len(text)}字符, 综合评分: {analysis['overall_score']:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"文本分析失败: {str(e)}")
            raise TextProcessingError(f"文本分析失败: {str(e)}") from e
    
    def get_text_statistics(self, text: str) -> TextStatistics:
        """
        获取文本统计信息
        
        参数:
            text: 要分析的文本
            
        返回:
            文本统计对象
        """
        if not text:
            return TextStatistics(0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0)
        
        # 基础计数
        char_count = len(text)
        words = self._extract_words(text)
        word_count = len(words)
        sentences = self._extract_sentences(text)
        sentence_count = len(sentences)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # 计算平均值
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # 计算复杂度和可读性
        readability_score = self._calculate_readability_score(text, words, sentences)
        complexity_score = self._calculate_complexity_score(text, words)
        
        return TextStatistics(
            char_count=char_count,
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            readability_score=readability_score,
            complexity_score=complexity_score
        )
    
    def detect_language_distribution(self, text: str) -> LanguageDistribution:
        """
        检测文本语言分布
        
        参数:
            text: 要分析的文本
            
        返回:
            语言分布信息
        """
        if not text:
            return LanguageDistribution("unknown", 0.0, {}, False)
        
        # 字符集分析
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        
        total_chars = chinese_chars + english_chars + japanese_chars + korean_chars
        
        if total_chars == 0:
            return LanguageDistribution("unknown", 0.0, {}, False)
        
        # 计算比例
        ratios = {
            "chinese": chinese_chars / total_chars,
            "english": english_chars / total_chars,
            "japanese": japanese_chars / total_chars,
            "korean": korean_chars / total_chars
        }
        
        # 确定主要语言
        primary_language = max(ratios.keys(), key=lambda k: ratios[k])
        confidence = ratios[primary_language]
        
        # 判断是否为混合语言
        significant_langs = [lang for lang, ratio in ratios.items() if ratio > 0.1]
        mixed_language = len(significant_langs) > 1
        
        return LanguageDistribution(
            primary_language=primary_language,
            confidence=confidence,
            language_ratios=ratios,
            mixed_language=mixed_language
        )
    
    def extract_key_phrases(self, text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        提取关键短语
        
        参数:
            text: 源文本
            top_k: 返回的短语数量
            
        返回:
            关键短语列表，包含短语和权重
        """
        if not text:
            return []
        
        # 简单的关键短语提取（基于频率和长度）
        words = self._extract_words(text)
        
        # 创建n-gram短语（1-3词）
        phrases = []
        
        # 单词
        for word in words:
            if len(word) >= 2 and not self._is_stop_word(word):
                phrases.append(word)
        
        # 双词短语
        for i in range(len(words) - 1):
            if (not self._is_stop_word(words[i]) and 
                not self._is_stop_word(words[i + 1])):
                phrase = f"{words[i]} {words[i + 1]}"
                phrases.append(phrase)
        
        # 三词短语
        for i in range(len(words) - 2):
            if (not any(self._is_stop_word(words[i + j]) for j in range(3))):
                phrase = f"{words[i]} {words[i + 1]} {words[i + 2]}"
                phrases.append(phrase)
        
        # 计算频率和权重
        phrase_counts = Counter(phrases)
        
        # 计算TF-IDF类似的权重
        key_phrases = []
        total_phrases = len(phrases)
        
        for phrase, count in phrase_counts.most_common():
            tf = count / total_phrases
            # 简化的IDF计算（基于短语长度奖励）
            length_bonus = len(phrase.split()) * 0.5
            weight = tf * (1 + length_bonus)
            
            key_phrases.append({
                "phrase": phrase,
                "frequency": count,
                "weight": weight,
                "tf_score": tf
            })
        
        # 按权重排序并返回top_k
        key_phrases.sort(key=lambda x: x["weight"], reverse=True)
        
        return key_phrases[:top_k]
    
    def _analyze_basic_stats(self, text: str) -> Dict[str, Any]:
        """分析基础统计信息"""
        stats = self.get_text_statistics(text)
        
        return {
            "character_count": stats.char_count,
            "word_count": stats.word_count,
            "sentence_count": stats.sentence_count,
            "paragraph_count": stats.paragraph_count,
            "average_word_length": round(stats.avg_word_length, 2),
            "average_sentence_length": round(stats.avg_sentence_length, 2),
            "words_per_paragraph": round(stats.word_count / max(stats.paragraph_count, 1), 2)
        }
    
    def _analyze_language(self, text: str) -> Dict[str, Any]:
        """分析语言特征"""
        lang_dist = self.detect_language_distribution(text)
        
        return {
            "primary_language": lang_dist.primary_language,
            "confidence": round(lang_dist.confidence, 3),
            "language_distribution": {
                k: round(v, 3) for k, v in lang_dist.language_ratios.items()
            },
            "is_multilingual": lang_dist.mixed_language,
            "character_encoding": "UTF-8",  # 简化处理
            "text_direction": "ltr"  # 简化处理
        }
    
    def _analyze_quality(self, text: str) -> Dict[str, Any]:
        """分析文本质量"""
        # 检查各种质量指标
        punctuation_ratio = len(re.findall(r'[。！？，；：""''（）【】]', text)) / len(text)
        digit_ratio = len(re.findall(r'\d', text)) / len(text)
        
        # 检查重复内容
        sentences = self._extract_sentences(text)
        unique_sentences = len(set(sentences))
        repetition_ratio = 1 - (unique_sentences / max(len(sentences), 1))
        
        # 拼写错误检查（简化版）
        words = self._extract_words(text)
        suspicious_words = [w for w in words if self._is_suspicious_word(w)]
        error_ratio = len(suspicious_words) / max(len(words), 1)
        
        # 格式一致性检查
        format_score = self._check_format_consistency(text)
        
        return {
            "punctuation_ratio": round(punctuation_ratio, 3),
            "digit_ratio": round(digit_ratio, 3),
            "repetition_ratio": round(repetition_ratio, 3),
            "estimated_error_ratio": round(error_ratio, 3),
            "format_consistency_score": round(format_score, 3),
            "overall_quality_score": round((1 - repetition_ratio) * (1 - error_ratio) * format_score, 3)
        }
    
    def _analyze_structure(self, text: str) -> Dict[str, Any]:
        """分析文本结构"""
        # 段落分析
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_lengths = [len(p) for p in paragraphs]
        
        # 标题检测（简化版）
        lines = text.split('\n')
        potential_titles = []
        for line in lines:
            line = line.strip()
            if line and len(line) < 100 and not line.endswith(('。', '！', '？')):
                potential_titles.append(line)
        
        # 列表和编号检测
        list_items = len(re.findall(r'^\s*[•\-\*\d+\.]\s+', text, re.MULTILINE))
        
        return {
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": round(sum(paragraph_lengths) / max(len(paragraphs), 1), 2),
            "paragraph_length_variance": round(self._calculate_variance(paragraph_lengths), 2),
            "potential_titles": len(potential_titles),
            "list_items": list_items,
            "has_clear_structure": len(paragraphs) > 1 and len(potential_titles) > 0
        }
    
    def _analyze_content_features(self, text: str) -> Dict[str, Any]:
        """分析内容特征"""
        # 数字和日期
        numbers = len(re.findall(r'\b\d+\b', text))
        dates = len(re.findall(r'\b\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\b', text))
        
        # URL和邮箱
        urls = len(re.findall(r'https?://[^\s]+', text))
        emails = len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        
        # 引用和代码
        quotes = len(re.findall(r'[""]([^""]+)[""]', text))
        code_blocks = len(re.findall(r'```[^`]*```|`[^`]+`', text))
        
        # 问题和感叹句
        questions = len(re.findall(r'[？?]', text))
        exclamations = len(re.findall(r'[！!]', text))
        
        return {
            "numbers_count": numbers,
            "dates_count": dates,
            "urls_count": urls,
            "emails_count": emails,
            "quotes_count": quotes,
            "code_blocks_count": code_blocks,
            "questions_count": questions,
            "exclamations_count": exclamations,
            "has_technical_content": code_blocks > 0 or urls > 0,
            "emotional_indicators": questions + exclamations
        }
    
    def _analyze_readability(self, text: str) -> Dict[str, Any]:
        """分析可读性"""
        words = self._extract_words(text)
        sentences = self._extract_sentences(text)
        
        if not words or not sentences:
            return {"readability_score": 0, "reading_level": "unknown"}
        
        # 计算各种可读性指标
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # 简化的可读性评分（类似Flesch Reading Ease）
        readability_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_word_length)
        readability_score = max(0, min(100, readability_score))  # 限制在0-100范围
        
        # 确定阅读等级
        if readability_score >= 90:
            reading_level = "很容易"
        elif readability_score >= 80:
            reading_level = "容易"
        elif readability_score >= 70:
            reading_level = "较容易"
        elif readability_score >= 60:
            reading_level = "标准"
        elif readability_score >= 50:
            reading_level = "较难"
        elif readability_score >= 30:
            reading_level = "难"
        else:
            reading_level = "很难"
        
        return {
            "readability_score": round(readability_score, 2),
            "reading_level": reading_level,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "avg_word_length": round(avg_word_length, 2),
            "complexity_factors": {
                "long_sentences": sum(1 for s in sentences if len(s.split()) > 20),
                "complex_words": sum(1 for w in words if len(w) > 8),
                "passive_voice_hints": len(re.findall(r'被|由.+来', text))
            }
        }
    
    def _analyze_sentiment_hints(self, text: str) -> Dict[str, Any]:
        """分析情感倾向（简化版）"""
        # 积极词汇
        positive_words = ['好', '棒', '优秀', '成功', '喜欢', '高兴', '满意', '赞', '推荐']
        # 消极词汇
        negative_words = ['坏', '差', '失败', '不好', '讨厌', '生气', '不满', '批评', '反对']
        # 中性词汇
        neutral_words = ['普通', '一般', '还行', '可以', '正常', '标准']
        
        positive_count = sum(text.count(word) for word in positive_words)
        negative_count = sum(text.count(word) for word in negative_words)
        neutral_count = sum(text.count(word) for word in neutral_words)
        
        total_sentiment_words = positive_count + negative_count + neutral_count
        
        if total_sentiment_words == 0:
            sentiment_polarity = 0.0
            sentiment_label = "中性"
        else:
            sentiment_polarity = (positive_count - negative_count) / total_sentiment_words
            
            if sentiment_polarity > 0.2:
                sentiment_label = "积极"
            elif sentiment_polarity < -0.2:
                sentiment_label = "消极"
            else:
                sentiment_label = "中性"
        
        return {
            "sentiment_polarity": round(sentiment_polarity, 3),
            "sentiment_label": sentiment_label,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "neutral_indicators": neutral_count,
            "sentiment_strength": round(abs(sentiment_polarity), 3)
        }
    
    def _calculate_overall_score(self, analysis: Dict[str, Any]) -> float:
        """计算综合评分"""
        try:
            quality_score = analysis["quality_metrics"]["overall_quality_score"]
            readability_score = analysis["readability"]["readability_score"] / 100
            structure_score = 1.0 if analysis["structure_analysis"]["has_clear_structure"] else 0.5
            
            # 加权平均
            overall_score = (
                quality_score * 0.4 +
                readability_score * 0.4 +
                structure_score * 0.2
            )
            
            return min(1.0, max(0.0, overall_score))
            
        except Exception:
            return 0.5  # 默认中等评分
    
    def _init_patterns(self):
        """初始化正则表达式模式"""
        self.word_pattern = re.compile(r'[\u4e00-\u9fff]+|[a-zA-Z]+')
        self.sentence_pattern = re.compile(r'[。！？.!?]+')
        
    def _extract_words(self, text: str) -> List[str]:
        """提取单词"""
        return [word for word in self.word_pattern.findall(text) if len(word) > 0]
    
    def _extract_sentences(self, text: str) -> List[str]:
        """提取句子"""
        sentences = self.sentence_pattern.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_stop_word(self, word: str) -> bool:
        """检查是否为停用词（简化版）"""
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'
        }
        return word.lower() in stop_words
    
    def _is_suspicious_word(self, word: str) -> bool:
        """检查是否为可疑单词（可能的拼写错误）"""
        # 简化的拼写检查
        if len(word) < 2:
            return False
        
        # 检查是否包含过多重复字符
        char_counts = Counter(word)
        max_repeat = max(char_counts.values())
        
        return max_repeat > len(word) * 0.6
    
    def _check_format_consistency(self, text: str) -> float:
        """检查格式一致性"""
        lines = text.split('\n')
        
        # 检查标点使用一致性
        chinese_punct = len(re.findall(r'[，。！？；：]', text))
        english_punct = len(re.findall(r'[,.!?;:]', text))
        
        if chinese_punct + english_punct == 0:
            punct_consistency = 1.0
        else:
            punct_consistency = max(chinese_punct, english_punct) / (chinese_punct + english_punct)
        
        # 检查引号使用一致性
        chinese_quotes = len(re.findall(r'[""''【】（）]', text))
        english_quotes = len(re.findall(r'["\'\(\)\[\]]', text))
        
        if chinese_quotes + english_quotes == 0:
            quote_consistency = 1.0
        else:
            quote_consistency = max(chinese_quotes, english_quotes) / (chinese_quotes + english_quotes)
        
        return (punct_consistency + quote_consistency) / 2
    
    def _calculate_variance(self, values: List[float]) -> float:
        """计算方差"""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance
    
    def _calculate_readability_score(self, text: str, words: List[str], sentences: List[str]) -> float:
        """计算可读性评分"""
        if not words or not sentences:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # 简化的可读性公式
        score = 100 - (1.5 * avg_sentence_length) - (50 * avg_word_length / 10)
        
        return max(0.0, min(100.0, score))
    
    def _calculate_complexity_score(self, text: str, words: List[str]) -> float:
        """计算复杂度评分"""
        if not words:
            return 0.0
        
        # 复杂词汇比例
        complex_words = sum(1 for word in words if len(word) > 6)
        complexity_ratio = complex_words / len(words)
        
        # 技术术语检测
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # 缩写
            r'\d+[.]\d+',      # 版本号
            r'[a-zA-Z]+_[a-zA-Z]+',  # 下划线命名
        ]
        
        technical_count = sum(len(re.findall(pattern, text)) for pattern in technical_patterns)
        technical_ratio = technical_count / len(words)
        
        # 综合复杂度
        complexity_score = (complexity_ratio * 0.7 + technical_ratio * 0.3) * 100
        
        return min(100.0, complexity_score)
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """返回空文本的分析结果"""
        return {
            "basic_stats": {
                "character_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "average_word_length": 0.0,
                "average_sentence_length": 0.0
            },
            "language_analysis": {
                "primary_language": "unknown",
                "confidence": 0.0,
                "language_distribution": {},
                "is_multilingual": False
            },
            "quality_metrics": {
                "overall_quality_score": 0.0
            },
            "structure_analysis": {
                "has_clear_structure": False
            },
            "content_features": {},
            "readability": {
                "readability_score": 0.0,
                "reading_level": "unknown"
            },
            "sentiment_hints": {
                "sentiment_label": "中性",
                "sentiment_polarity": 0.0
            },
            "overall_score": 0.0
        } 