"""
文本处理工具: 提供文本处理、令牌计数、
文本分块和其他与文本相关的操作功能
"""

import re
from typing import List, Dict, Any, Tuple, Optional

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    计算文本字符串中的令牌数量
    
    参数:
        text: 需要计算令牌的文本
        model: 用于令牌计数的模型（决定分词策略）
        
    返回:
        令牌数量
    """
    if not text:
        return 0
    
    try:
        # 尝试使用tiktoken进行精确的令牌计数（如果可用）
        import tiktoken
        
        # 根据模型选择编码
        if model.startswith("gpt-4"):
            encoding = tiktoken.encoding_for_model("gpt-4")
        elif model.startswith("gpt-3.5"):
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            # 默认对较新的模型使用cl100k_base
            encoding = tiktoken.get_encoding("cl100k_base")
        
        # 计算令牌
        return len(encoding.encode(text))
    
    except (ImportError, ModuleNotFoundError):
        # 如果tiktoken不可用，回退到近似计数
        # 这是一个非常粗略的近似值
        words = len(re.findall(r'\S+', text))
        # 英文文本中平均每个令牌约4个字符
        char_tokens = len(text) // 4
        # 取最大值作为保守估计
        return max(words, char_tokens)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    将文本分割为重叠的块
    
    参数:
        text: 要分割的文本
        chunk_size: 每个块的最大字符大小
        chunk_overlap: 块之间的重叠字符数
        
    返回:
        文本块列表
    """
    if not text or chunk_size <= 0:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        # 计算结束位置，考虑文本长度
        end = min(start + chunk_size, text_len)
        
        # 如果不在文本末尾且不在一个好的断点，找一个好的断点
        if end < text_len and text[end] not in [' ', '\n', '.', ',', '!', '?', ';', ':', '-']:
            # 寻找一个好的断点（空白或标点符号）
            good_break = max(
                text.rfind(' ', start, end),
                text.rfind('\n', start, end),
                text.rfind('.', start, end),
                text.rfind(',', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end),
                text.rfind(';', start, end),
                text.rfind(':', start, end),
                text.rfind('-', start, end)
            )
            
            # 如果找到好的断点，使用它
            if good_break != -1 and good_break > start:
                end = good_break + 1  # 包括断点字符
        
        # 提取块
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 计算下一个起始位置，考虑重叠
        start = end - chunk_overlap if end - chunk_overlap > start else end
        
        # 如果无法前进，防止无限循环
        if start >= end:
            break
    
    return chunks

def detect_language(text: str) -> str:
    """
    检测文本字符串的语言（简单实现）
    
    参数:
        text: 需要检测语言的文本
        
    返回:
        ISO 639-1 语言代码
    """
    try:
        # 尝试使用langdetect（如果可用）
        from langdetect import detect
        return detect(text)
    except (ImportError, ModuleNotFoundError):
        # 对常见语言的非常简单的后备检测
        # 这只是一个占位符 - 真正的检测会使用适当的库
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

def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """
    从文本内容中提取潜在的元数据
    
    参数:
        text: 要提取元数据的文本
        
    返回:
        元数据字典
    """
    metadata = {}
    
    # 尝试检测语言
    metadata['language'] = detect_language(text)
    
    # 计算令牌数
    metadata['token_count'] = count_tokens(text)
    
    # 字符和单词计数
    metadata['char_count'] = len(text)
    metadata['word_count'] = len(re.findall(r'\S+', text))
    
    # 获取汇总统计
    lines = text.split('\n')
    metadata['line_count'] = len(lines)
    
    # 从第一行提取潜在标题
    if lines and len(lines[0]) < 100:
        metadata['potential_title'] = lines[0].strip()
    
    return metadata

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    从文本中提取潜在关键词
    
    参数:
        text: 要提取关键词的文本
        max_keywords: 提取的最大关键词数量
        
    返回:
        关键词列表
    """
    try:
        # 尝试使用关键词提取库（如果可用）
        import yake
        
        # 简单关键词提取
        kw_extractor = yake.KeywordExtractor(
            lan=detect_language(text),
            n=1,  # 1-gram
            dedupLim=0.9,
            dedupFunc='seqm',
            windowsSize=1,
            top=max_keywords
        )
        
        # 提取关键词
        keywords = kw_extractor.extract_keywords(text)
        return [kw[0] for kw in keywords]
    
    except (ImportError, ModuleNotFoundError):
        # 如果关键词提取库不可用，回退到简单的频率基于提取
        # 这是一个非常简单的方法
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 过滤掉常见的停用词
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                    'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'about', 'from'}
        
        # 计算单词频率
        word_counts = {}
        for word in words:
            if word not in stopwords and len(word) > 2:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # 按频率排序
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前max_keywords个关键词
        return [word for word, count in sorted_words[:max_keywords]]
