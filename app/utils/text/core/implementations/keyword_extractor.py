"""
YAKE关键词提取器：基于YAKE算法的无监督关键词提取
支持中英文混合文本的关键词提取和排序
"""

import logging
import re
import math
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter, defaultdict
from dataclasses import dataclass

from app.utils.text.core.base import KeywordExtractor, ExtractionConfig, TextProcessingError

logger = logging.getLogger(__name__)


@dataclass
class KeywordResult:
    """关键词结果"""
    keyword: str
    score: float
    frequency: int
    positions: List[int]
    context: List[str]


@dataclass
class YakeFeatures:
    """YAKE算法特征"""
    word_case: float
    word_position: float
    word_frequency: float
    word_relatedness: float
    word_different_sentence: float


class YakeKeywordExtractor(KeywordExtractor):
    """
    基于YAKE算法的关键词提取器
    YAKE (Yet Another Keyword Extractor) 是一种轻量级的无监督关键词提取方法
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        初始化关键词提取器
        
        参数:
            config: 提取配置
        """
        super().__init__(config)
        self._init_stopwords()
        self._init_patterns()
        
        logger.info(f"初始化YAKE关键词提取器，最大n-gram: {self.config.max_ngram_size}")
    
    def extract_keywords(self, text: str, top_k: Optional[int] = None) -> List[str]:
        """
        提取关键词
        
        参数:
            text: 源文本
            top_k: 返回的关键词数量
            
        返回:
            关键词列表
        """
        if top_k is None:
            top_k = self.config.max_keywords
        
        results = self.extract_keywords_with_scores(text, top_k)
        return [result.keyword for result in results]
    
    def extract_keywords_with_scores(self, text: str, top_k: Optional[int] = None) -> List[KeywordResult]:
        """
        提取关键词并返回评分
        
        参数:
            text: 源文本
            top_k: 返回的关键词数量
            
        返回:
            关键词结果列表
        """
        if not text or not text.strip():
            return []
        
        if top_k is None:
            top_k = self.config.max_keywords
        
        try:
            # 预处理文本
            preprocessed_text = self._preprocess_text(text)
            
            # 提取候选词
            candidates = self._extract_candidates(preprocessed_text)
            
            if not candidates:
                return []
            
            # 计算YAKE特征
            word_features = self._calculate_word_features(preprocessed_text, candidates)
            
            # 计算候选词得分
            candidate_scores = self._calculate_candidate_scores(candidates, word_features)
            
            # 排序并返回top_k
            sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1])
            
            # 转换为KeywordResult对象
            results = []
            for i, (candidate, score) in enumerate(sorted_candidates[:top_k]):
                keyword_result = self._create_keyword_result(
                    candidate, score, preprocessed_text, text
                )
                results.append(keyword_result)
            
            logger.debug(f"关键词提取完成: {len(results)}个关键词")
            
            return results
            
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            raise TextProcessingError(f"关键词提取失败: {str(e)}") from e
    
    def extract_phrases(self, text: str, min_freq: int = 2) -> List[Dict[str, Any]]:
        """
        提取短语
        
        参数:
            text: 源文本
            min_freq: 最小频率
            
        返回:
            短语列表
        """
        if not text:
            return []
        
        # 提取n-gram短语
        phrases = []
        
        for n in range(2, self.config.max_ngram_size + 1):
            ngrams = self._extract_ngrams(text, n)
            ngram_counts = Counter(ngrams)
            
            for ngram, count in ngram_counts.items():
                if count >= min_freq and not self._is_stopword_phrase(ngram):
                    phrases.append({
                        'phrase': ngram,
                        'frequency': count,
                        'length': n,
                        'score': count * n  # 简单评分：频率×长度
                    })
        
        # 按评分排序
        phrases.sort(key=lambda x: x['score'], reverse=True)
        
        return phrases[:self.config.max_keywords]
    
    def get_keyword_context(self, text: str, keyword: str, window_size: int = 50) -> List[str]:
        """
        获取关键词上下文
        
        参数:
            text: 源文本
            keyword: 关键词
            window_size: 上下文窗口大小
            
        返回:
            上下文列表
        """
        contexts = []
        
        # 查找关键词位置
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        
        for match in pattern.finditer(text):
            start = max(0, match.start() - window_size)
            end = min(len(text), match.end() + window_size)
            
            context = text[start:end].strip()
            if context:
                contexts.append(context)
        
        return contexts
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 句子分割标记
        text = re.sub(r'[。！？.!?]+', ' SENTENCE_BOUNDARY ', text)
        
        return text.strip()
    
    def _extract_candidates(self, text: str) -> List[str]:
        """提取候选关键词"""
        candidates = set()
        
        # 分割句子
        sentences = re.split(r'\s+SENTENCE_BOUNDARY\s+', text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            # 提取1-gram到max_ngram_size的候选词
            for n in range(1, self.config.max_ngram_size + 1):
                ngrams = self._extract_ngrams_from_sentence(sentence, n)
                
                for ngram in ngrams:
                    if self._is_valid_candidate(ngram):
                        candidates.add(ngram)
        
        return list(candidates)
    
    def _extract_ngrams_from_sentence(self, sentence: str, n: int) -> List[str]:
        """从句子中提取n-gram"""
        # 分词（简化版）
        words = self._tokenize_words(sentence)
        
        if len(words) < n:
            return []
        
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram_words = words[i:i+n]
            
            # 检查是否包含停用词
            if any(self._is_stopword(word) for word in ngram_words):
                continue
            
            ngram = ' '.join(ngram_words)
            ngrams.append(ngram)
        
        return ngrams
    
    def _tokenize_words(self, text: str) -> List[str]:
        """分词"""
        # 支持中英文混合分词
        words = []
        
        # 中文字符
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', text)
        for word in chinese_words:
            words.extend(list(word))  # 中文按字符分割
        
        # 英文单词
        english_words = re.findall(r'[a-zA-Z]+', text)
        words.extend(english_words)
        
        # 数字
        numbers = re.findall(r'\d+', text)
        words.extend(numbers)
        
        # 按原文顺序重新排列（简化处理）
        final_words = []
        word_pattern = re.compile(r'[\u4e00-\u9fff]|[a-zA-Z]+|\d+')
        
        for match in word_pattern.finditer(text):
            word = match.group()
            if len(word) >= self.config.min_word_length:
                final_words.append(word.lower())
        
        return final_words
    
    def _is_valid_candidate(self, candidate: str) -> bool:
        """检查候选词是否有效"""
        # 长度检查
        if len(candidate) < self.config.min_word_length:
            return False
        
        # 是否全为数字或标点
        if re.match(r'^[\d\s\W]+$', candidate):
            return False
        
        # 是否为停用词
        if self._is_stopword_phrase(candidate):
            return False
        
        # 检查是否包含至少一个字母或中文字符
        if not re.search(r'[a-zA-Z\u4e00-\u9fff]', candidate):
            return False
        
        return True
    
    def _calculate_word_features(self, text: str, candidates: List[str]) -> Dict[str, YakeFeatures]:
        """计算词汇特征"""
        word_features = {}
        
        # 分词和统计
        words = self._tokenize_words(text)
        word_counts = Counter(words)
        total_words = len(words)
        
        # 句子分割
        sentences = re.split(r'\s+SENTENCE_BOUNDARY\s+', text)
        total_sentences = len(sentences)
        
        for candidate in candidates:
            candidate_words = candidate.split()
            
            # 计算各个特征
            features = YakeFeatures(
                word_case=self._calculate_case_feature(candidate),
                word_position=self._calculate_position_feature(candidate, text),
                word_frequency=self._calculate_frequency_feature(candidate_words, word_counts, total_words),
                word_relatedness=self._calculate_relatedness_feature(candidate_words, words),
                word_different_sentence=self._calculate_sentence_feature(candidate, sentences)
            )
            
            word_features[candidate] = features
        
        return word_features
    
    def _calculate_case_feature(self, candidate: str) -> float:
        """计算大小写特征"""
        # 对于中文，此特征不适用
        if re.search(r'[\u4e00-\u9fff]', candidate):
            return 0.0
        
        uppercase_count = sum(1 for c in candidate if c.isupper())
        total_letters = sum(1 for c in candidate if c.isalpha())
        
        if total_letters == 0:
            return 0.0
        
        # 全大写或首字母大写得到更高分
        if uppercase_count == total_letters:
            return 1.0
        elif candidate[0].isupper() and uppercase_count == 1:
            return 0.5
        else:
            return 0.0
    
    def _calculate_position_feature(self, candidate: str, text: str) -> float:
        """计算位置特征"""
        # 查找候选词在文本中的位置
        positions = []
        
        pattern = re.compile(re.escape(candidate), re.IGNORECASE)
        for match in pattern.finditer(text):
            position = match.start() / len(text)
            positions.append(position)
        
        if not positions:
            return 1.0
        
        # 靠前的位置得分更高
        avg_position = sum(positions) / len(positions)
        return 1.0 - avg_position
    
    def _calculate_frequency_feature(self, words: List[str], word_counts: Counter, total_words: int) -> float:
        """计算频率特征"""
        if not words:
            return 0.0
        
        # 计算平均词频
        total_freq = sum(word_counts.get(word, 0) for word in words)
        avg_freq = total_freq / len(words)
        
        # 归一化频率
        normalized_freq = avg_freq / total_words
        
        return normalized_freq
    
    def _calculate_relatedness_feature(self, candidate_words: List[str], all_words: List[str]) -> float:
        """计算相关性特征"""
        if len(candidate_words) <= 1:
            return 0.0
        
        # 计算词汇间的共现程度
        relatedness_scores = []
        
        for i, word1 in enumerate(candidate_words):
            for word2 in candidate_words[i+1:]:
                # 计算两词的距离
                distances = []
                
                for j, w in enumerate(all_words[:-1]):
                    if w == word1:
                        for k in range(j+1, min(j+10, len(all_words))):  # 检查后续10个词
                            if all_words[k] == word2:
                                distances.append(k - j)
                
                if distances:
                    avg_distance = sum(distances) / len(distances)
                    relatedness = 1.0 / avg_distance
                    relatedness_scores.append(relatedness)
        
        return sum(relatedness_scores) / max(len(relatedness_scores), 1)
    
    def _calculate_sentence_feature(self, candidate: str, sentences: List[str]) -> float:
        """计算句子分布特征"""
        sentence_count = 0
        
        for sentence in sentences:
            if candidate in sentence:
                sentence_count += 1
        
        # 出现在更多句子中的候选词得分更高
        return sentence_count / max(len(sentences), 1)
    
    def _calculate_candidate_scores(self, candidates: List[str], word_features: Dict[str, YakeFeatures]) -> Dict[str, float]:
        """计算候选词得分"""
        candidate_scores = {}
        
        for candidate in candidates:
            features = word_features.get(candidate)
            if not features:
                candidate_scores[candidate] = float('inf')
                continue
            
            # YAKE评分公式：分数越低越好
            score = (
                features.word_case * 0.1 +
                features.word_position * 0.2 +
                features.word_frequency * 0.3 +
                (1.0 - features.word_relatedness) * 0.2 +
                (1.0 - features.word_different_sentence) * 0.2
            )
            
            candidate_scores[candidate] = score
        
        return candidate_scores
    
    def _create_keyword_result(self, keyword: str, score: float, 
                             preprocessed_text: str, original_text: str) -> KeywordResult:
        """创建关键词结果对象"""
        # 计算频率
        frequency = preprocessed_text.lower().count(keyword.lower())
        
        # 查找位置
        positions = []
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        for match in pattern.finditer(original_text):
            positions.append(match.start())
        
        # 获取上下文
        context = self.get_keyword_context(original_text, keyword, 30)
        
        return KeywordResult(
            keyword=keyword,
            score=score,
            frequency=frequency,
            positions=positions,
            context=context[:3]  # 最多返回3个上下文
        )
    
    def _extract_ngrams(self, text: str, n: int) -> List[str]:
        """提取n-gram"""
        words = self._tokenize_words(text)
        
        if len(words) < n:
            return []
        
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        
        return ngrams
    
    def _init_stopwords(self):
        """初始化停用词"""
        self.stopwords = {
            # 中文停用词
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '会', '可', '这', '个', '你', '他', '她', '它', '们',
            '能', '说', '为', '要', '以', '来', '去', '把', '被', '让', '给', '对', '从',
            
            # 英文停用词
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
    
    def _init_patterns(self):
        """初始化正则表达式模式"""
        self.word_pattern = re.compile(r'[\u4e00-\u9fff]|[a-zA-Z]+|\d+')
        self.sentence_pattern = re.compile(r'[。！？.!?]+')
    
    def _is_stopword(self, word: str) -> bool:
        """检查是否为停用词"""
        return word.lower() in self.stopwords
    
    def _is_stopword_phrase(self, phrase: str) -> bool:
        """检查短语是否全为停用词"""
        words = phrase.split()
        return all(self._is_stopword(word) for word in words) 