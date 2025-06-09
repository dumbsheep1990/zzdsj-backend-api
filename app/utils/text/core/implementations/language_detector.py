"""
高级语言检测器：准确识别文本语言和编码
支持多语言混合文本的检测和分析
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from dataclasses import dataclass

from app.utils.text.core.base import LanguageDetector, DetectionConfig, TextProcessingError

logger = logging.getLogger(__name__)


@dataclass
class LanguageResult:
    """语言检测结果"""
    language: str
    confidence: float
    script: str
    encoding: str


@dataclass
class DetailedLanguageInfo:
    """详细语言信息"""
    primary_language: str
    secondary_languages: List[Tuple[str, float]]
    script_distribution: Dict[str, float]
    is_mixed: bool
    confidence: float
    encoding_info: Dict[str, Any]


class AdvancedLanguageDetector(LanguageDetector):
    """
    高级语言检测器
    基于字符集、N-gram、统计特征等多种方法进行语言检测
    """
    
    def __init__(self, config: Optional[DetectionConfig] = None):
        """
        初始化语言检测器
        
        参数:
            config: 检测配置
        """
        super().__init__(config)
        self._init_language_patterns()
        self._init_character_sets()
        
        logger.info("初始化高级语言检测器")
    
    def detect_language(self, text: str) -> str:
        """
        检测文本的主要语言
        
        参数:
            text: 要检测的文本
            
        返回:
            语言代码（如：zh, en, ja等）
        """
        if not text or not text.strip():
            return "unknown"
        
        try:
            result = self.detect_with_confidence(text)
            return result.language
            
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            return "unknown"
    
    def detect_with_confidence(self, text: str) -> LanguageResult:
        """
        检测语言并返回置信度
        
        参数:
            text: 要检测的文本
            
        返回:
            语言检测结果对象
        """
        if not text or not text.strip():
            return LanguageResult("unknown", 0.0, "unknown", "utf-8")
        
        try:
            # 基于字符集的快速检测
            char_based_result = self._detect_by_characters(text)
            
            # 基于N-gram的精确检测
            ngram_based_result = self._detect_by_ngrams(text)
            
            # 基于统计特征的检测
            stats_based_result = self._detect_by_statistics(text)
            
            # 融合多种检测结果
            final_result = self._fuse_detection_results([
                char_based_result,
                ngram_based_result,
                stats_based_result
            ])
            
            logger.debug(f"语言检测完成: {final_result.language} (置信度: {final_result.confidence:.3f})")
            
            return final_result
            
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            raise TextProcessingError(f"语言检测失败: {str(e)}") from e
    
    def detect_multiple_languages(self, text: str) -> DetailedLanguageInfo:
        """
        检测文本中的多种语言
        
        参数:
            text: 要检测的文本
            
        返回:
            详细语言信息
        """
        if not text or not text.strip():
            return DetailedLanguageInfo("unknown", [], {}, False, 0.0, {})
        
        try:
            # 分析字符分布
            char_distribution = self._analyze_character_distribution(text)
            
            # 分析脚本分布
            script_distribution = self._analyze_script_distribution(text)
            
            # 检测各种可能的语言
            language_candidates = self._detect_language_candidates(text)
            
            # 确定主要语言
            if language_candidates:
                primary_language = language_candidates[0][0]
                secondary_languages = language_candidates[1:]
                confidence = language_candidates[0][1]
            else:
                primary_language = "unknown"
                secondary_languages = []
                confidence = 0.0
            
            # 判断是否为混合语言
            significant_langs = [lang for lang, conf in language_candidates if conf > 0.1]
            is_mixed = len(significant_langs) > 1
            
            # 编码信息
            encoding_info = self._analyze_encoding(text)
            
            return DetailedLanguageInfo(
                primary_language=primary_language,
                secondary_languages=secondary_languages,
                script_distribution=script_distribution,
                is_mixed=is_mixed,
                confidence=confidence,
                encoding_info=encoding_info
            )
            
        except Exception as e:
            logger.error(f"多语言检测失败: {str(e)}")
            raise TextProcessingError(f"多语言检测失败: {str(e)}") from e
    
    def detect_encoding(self, text: str) -> Dict[str, Any]:
        """
        检测文本编码信息
        
        参数:
            text: 要检测的文本
            
        返回:
            编码信息字典
        """
        return self._analyze_encoding(text)
    
    def _detect_by_characters(self, text: str) -> LanguageResult:
        """基于字符集的语言检测"""
        char_counts = {
            'chinese': 0,
            'japanese_hiragana': 0,
            'japanese_katakana': 0,
            'korean': 0,
            'latin': 0,
            'cyrillic': 0,
            'arabic': 0,
            'thai': 0,
            'hindi': 0
        }
        
        for char in text:
            code_point = ord(char)
            
            # 中文字符
            if 0x4E00 <= code_point <= 0x9FFF:
                char_counts['chinese'] += 1
            # 日文平假名
            elif 0x3040 <= code_point <= 0x309F:
                char_counts['japanese_hiragana'] += 1
            # 日文片假名
            elif 0x30A0 <= code_point <= 0x30FF:
                char_counts['japanese_katakana'] += 1
            # 韩文
            elif 0xAC00 <= code_point <= 0xD7AF:
                char_counts['korean'] += 1
            # 拉丁字母
            elif (0x0041 <= code_point <= 0x005A) or (0x0061 <= code_point <= 0x007A):
                char_counts['latin'] += 1
            # 西里尔字母
            elif 0x0400 <= code_point <= 0x04FF:
                char_counts['cyrillic'] += 1
            # 阿拉伯字母
            elif 0x0600 <= code_point <= 0x06FF:
                char_counts['arabic'] += 1
            # 泰文
            elif 0x0E00 <= code_point <= 0x0E7F:
                char_counts['thai'] += 1
            # 印地文
            elif 0x0900 <= code_point <= 0x097F:
                char_counts['hindi'] += 1
        
        total_chars = sum(char_counts.values())
        
        if total_chars == 0:
            return LanguageResult("unknown", 0.0, "unknown", "utf-8")
        
        # 计算各字符集比例
        ratios = {k: v / total_chars for k, v in char_counts.items()}
        
        # 根据字符集确定语言
        max_script = max(ratios.keys(), key=lambda k: ratios[k])
        confidence = ratios[max_script]
        
        # 映射到语言代码
        script_to_language = {
            'chinese': 'zh',
            'japanese_hiragana': 'ja',
            'japanese_katakana': 'ja',
            'korean': 'ko',
            'latin': 'en',  # 简化处理，实际需要进一步区分
            'cyrillic': 'ru',
            'arabic': 'ar',
            'thai': 'th',
            'hindi': 'hi'
        }
        
        language = script_to_language.get(max_script, 'unknown')
        script = max_script
        
        # 特殊处理：中日韩字符可能混用
        if language == 'zh' and (ratios['japanese_hiragana'] > 0.1 or ratios['japanese_katakana'] > 0.1):
            language = 'ja'
            confidence = ratios['japanese_hiragana'] + ratios['japanese_katakana'] + ratios['chinese']
        
        return LanguageResult(language, confidence, script, "utf-8")
    
    def _detect_by_ngrams(self, text: str) -> LanguageResult:
        """基于N-gram特征的语言检测"""
        # 提取2-gram和3-gram
        bigrams = self._extract_ngrams(text, 2)
        trigrams = self._extract_ngrams(text, 3)
        
        # 计算各语言的特征匹配度
        language_scores = {}
        
        for lang, patterns in self.language_patterns.items():
            score = 0
            
            # 匹配2-gram模式
            for bigram in bigrams:
                if bigram in patterns.get('bigrams', set()):
                    score += 2
            
            # 匹配3-gram模式
            for trigram in trigrams:
                if trigram in patterns.get('trigrams', set()):
                    score += 3
            
            # 匹配字符模式
            for char in text:
                if char in patterns.get('chars', set()):
                    score += 1
            
            language_scores[lang] = score
        
        # 找到最高得分的语言
        if not language_scores:
            return LanguageResult("unknown", 0.0, "unknown", "utf-8")
        
        best_language = max(language_scores.keys(), key=lambda k: language_scores[k])
        max_score = language_scores[best_language]
        total_score = sum(language_scores.values())
        
        confidence = max_score / max(total_score, 1)
        
        return LanguageResult(best_language, confidence, "mixed", "utf-8")
    
    def _detect_by_statistics(self, text: str) -> LanguageResult:
        """基于统计特征的语言检测"""
        # 计算各种统计特征
        features = {
            'avg_word_length': self._calculate_avg_word_length(text),
            'vowel_ratio': self._calculate_vowel_ratio(text),
            'consonant_clusters': self._count_consonant_clusters(text),
            'punctuation_style': self._analyze_punctuation_style(text),
            'space_frequency': text.count(' ') / max(len(text), 1)
        }
        
        # 基于统计特征的简单规则
        if features['space_frequency'] < 0.1:  # 很少空格，可能是中日韩
            if '。' in text or '，' in text:
                return LanguageResult("zh", 0.7, "cjk", "utf-8")
            elif 'の' in text or 'を' in text:
                return LanguageResult("ja", 0.7, "cjk", "utf-8")
            elif '이' in text or '가' in text:
                return LanguageResult("ko", 0.7, "cjk", "utf-8")
        
        # 拉丁文字语言的进一步区分
        if features['space_frequency'] > 0.1:
            if features['avg_word_length'] > 6:  # 德语单词较长
                return LanguageResult("de", 0.6, "latin", "utf-8")
            elif features['vowel_ratio'] > 0.5:  # 西班牙语元音较多
                return LanguageResult("es", 0.6, "latin", "utf-8")
            else:
                return LanguageResult("en", 0.6, "latin", "utf-8")
        
        return LanguageResult("unknown", 0.0, "unknown", "utf-8")
    
    def _fuse_detection_results(self, results: List[LanguageResult]) -> LanguageResult:
        """融合多种检测结果"""
        if not results:
            return LanguageResult("unknown", 0.0, "unknown", "utf-8")
        
        # 加权融合
        weights = [0.5, 0.3, 0.2]  # 字符集检测权重最高
        
        language_scores = {}
        
        for i, result in enumerate(results):
            weight = weights[i] if i < len(weights) else 0.1
            
            if result.language not in language_scores:
                language_scores[result.language] = 0
            
            language_scores[result.language] += result.confidence * weight
        
        # 选择得分最高的语言
        best_language = max(language_scores.keys(), key=lambda k: language_scores[k])
        final_confidence = language_scores[best_language]
        
        # 确定脚本类型
        script = self._determine_script(best_language)
        
        return LanguageResult(best_language, final_confidence, script, "utf-8")
    
    def _analyze_character_distribution(self, text: str) -> Dict[str, float]:
        """分析字符分布"""
        char_categories = {
            'chinese': 0,
            'japanese': 0,
            'korean': 0,
            'latin': 0,
            'digit': 0,
            'punctuation': 0,
            'whitespace': 0,
            'other': 0
        }
        
        for char in text:
            code_point = ord(char)
            
            if 0x4E00 <= code_point <= 0x9FFF:
                char_categories['chinese'] += 1
            elif 0x3040 <= code_point <= 0x30FF:
                char_categories['japanese'] += 1
            elif 0xAC00 <= code_point <= 0xD7AF:
                char_categories['korean'] += 1
            elif char.isalpha():
                char_categories['latin'] += 1
            elif char.isdigit():
                char_categories['digit'] += 1
            elif char in '.,!?;:':
                char_categories['punctuation'] += 1
            elif char.isspace():
                char_categories['whitespace'] += 1
            else:
                char_categories['other'] += 1
        
        total = len(text)
        return {k: v / max(total, 1) for k, v in char_categories.items()}
    
    def _analyze_script_distribution(self, text: str) -> Dict[str, float]:
        """分析文字系统分布"""
        script_counts = {
            'Han': 0,        # 汉字
            'Hiragana': 0,   # 平假名
            'Katakana': 0,   # 片假名
            'Hangul': 0,     # 韩文
            'Latin': 0,      # 拉丁文
            'Cyrillic': 0,   # 西里尔文
            'Arabic': 0      # 阿拉伯文
        }
        
        for char in text:
            code_point = ord(char)
            
            if 0x4E00 <= code_point <= 0x9FFF:
                script_counts['Han'] += 1
            elif 0x3040 <= code_point <= 0x309F:
                script_counts['Hiragana'] += 1
            elif 0x30A0 <= code_point <= 0x30FF:
                script_counts['Katakana'] += 1
            elif 0xAC00 <= code_point <= 0xD7AF:
                script_counts['Hangul'] += 1
            elif ((0x0041 <= code_point <= 0x005A) or 
                  (0x0061 <= code_point <= 0x007A)):
                script_counts['Latin'] += 1
            elif 0x0400 <= code_point <= 0x04FF:
                script_counts['Cyrillic'] += 1
            elif 0x0600 <= code_point <= 0x06FF:
                script_counts['Arabic'] += 1
        
        total = sum(script_counts.values())
        return {k: v / max(total, 1) for k, v in script_counts.items()}
    
    def _detect_language_candidates(self, text: str) -> List[Tuple[str, float]]:
        """检测所有可能的语言候选"""
        candidates = []
        
        # 基于字符集检测
        char_result = self._detect_by_characters(text)
        if char_result.confidence > 0.1:
            candidates.append((char_result.language, char_result.confidence))
        
        # 基于N-gram检测
        ngram_result = self._detect_by_ngrams(text)
        if ngram_result.confidence > 0.1:
            candidates.append((ngram_result.language, ngram_result.confidence))
        
        # 去重并排序
        candidate_dict = {}
        for lang, conf in candidates:
            if lang in candidate_dict:
                candidate_dict[lang] = max(candidate_dict[lang], conf)
            else:
                candidate_dict[lang] = conf
        
        # 按置信度排序
        sorted_candidates = sorted(candidate_dict.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_candidates
    
    def _analyze_encoding(self, text: str) -> Dict[str, Any]:
        """分析文本编码信息"""
        # 检测是否包含非ASCII字符
        ascii_chars = sum(1 for char in text if ord(char) < 128)
        non_ascii_chars = len(text) - ascii_chars
        
        # 检测UTF-8特征
        utf8_indicators = {
            'multibyte_chars': non_ascii_chars,
            'ascii_ratio': ascii_chars / max(len(text), 1),
            'bom_present': text.startswith('\ufeff'),
            'encoding_confidence': 1.0 if non_ascii_chars > 0 else 0.8
        }
        
        return {
            'detected_encoding': 'utf-8',
            'ascii_percentage': round(utf8_indicators['ascii_ratio'] * 100, 2),
            'multibyte_chars': utf8_indicators['multibyte_chars'],
            'bom_present': utf8_indicators['bom_present'],
            'confidence': utf8_indicators['encoding_confidence']
        }
    
    def _init_language_patterns(self):
        """初始化语言特征模式"""
        self.language_patterns = {
            'zh': {
                'chars': set('的了在是我有和就不人都一个上来为会可你'),
                'bigrams': set(['的是', '了一', '在这', '我们', '有的', '和我']),
                'trigrams': set(['我们的', '这个是', '有一个', '不会有'])
            },
            'en': {
                'chars': set('theandtoofinallywhichthiswithforhave'),
                'bigrams': set(['th', 'he', 'in', 'er', 'an', 're']),
                'trigrams': set(['the', 'and', 'ing', 'ion', 'tio'])
            },
            'ja': {
                'chars': set('のをにがはでとも'),
                'bigrams': set(['の', 'を', 'に', 'が', 'は', 'で']),
                'trigrams': set(['です', 'ます', 'した', 'する'])
            },
            'ko': {
                'chars': set('이가을를에서의도와'),
                'bigrams': set(['이다', '가다', '하다', '있다']),
                'trigrams': set(['입니다', '습니다', '합니다'])
            }
        }
    
    def _init_character_sets(self):
        """初始化字符集范围"""
        self.character_sets = {
            'CJK_Unified': (0x4E00, 0x9FFF),
            'Hiragana': (0x3040, 0x309F),
            'Katakana': (0x30A0, 0x30FF),
            'Hangul': (0xAC00, 0xD7AF),
            'Latin_Basic': (0x0041, 0x007A),
            'Cyrillic': (0x0400, 0x04FF),
            'Arabic': (0x0600, 0x06FF)
        }
    
    def _extract_ngrams(self, text: str, n: int) -> List[str]:
        """提取N-gram"""
        if len(text) < n:
            return []
        
        ngrams = []
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            if not ngram.isspace():
                ngrams.append(ngram)
        
        return ngrams
    
    def _calculate_avg_word_length(self, text: str) -> float:
        """计算平均单词长度"""
        words = re.findall(r'\b\w+\b', text)
        if not words:
            return 0.0
        
        return sum(len(word) for word in words) / len(words)
    
    def _calculate_vowel_ratio(self, text: str) -> float:
        """计算元音比例"""
        vowels = 'aeiouAEIOU'
        vowel_count = sum(1 for char in text if char in vowels)
        letter_count = sum(1 for char in text if char.isalpha())
        
        return vowel_count / max(letter_count, 1)
    
    def _count_consonant_clusters(self, text: str) -> int:
        """计算辅音簇数量"""
        consonant_clusters = re.findall(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{2,}', text)
        return len(consonant_clusters)
    
    def _analyze_punctuation_style(self, text: str) -> str:
        """分析标点符号风格"""
        chinese_punct = len(re.findall(r'[，。！？；：""''（）【】]', text))
        western_punct = len(re.findall(r'[,.!?;:"\'()\[\]]', text))
        
        if chinese_punct > western_punct:
            return 'chinese'
        elif western_punct > chinese_punct:
            return 'western'
        else:
            return 'mixed'
    
    def _determine_script(self, language: str) -> str:
        """根据语言确定文字系统"""
        script_mapping = {
            'zh': 'Han',
            'ja': 'Japanese',
            'ko': 'Hangul',
            'en': 'Latin',
            'es': 'Latin',
            'fr': 'Latin',
            'de': 'Latin',
            'ru': 'Cyrillic',
            'ar': 'Arabic',
            'th': 'Thai',
            'hi': 'Devanagari'
        }
        
        return script_mapping.get(language, 'unknown') 