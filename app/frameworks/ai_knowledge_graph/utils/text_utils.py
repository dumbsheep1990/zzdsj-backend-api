"""文本处理工具
提供文本分块、清理等功能
"""

from typing import List
import re


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """将文本分块处理
    
    Args:
        text: 输入文本
        chunk_size: 块大小（词数）
        overlap: 重叠词数
        
    Returns:
        文本块列表
    """
    if not text or not text.strip():
        return []
    
    # 按词分割文本
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        # 确定当前块的结束位置
        end = min(start + chunk_size, len(words))
        
        # 提取当前块
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)
        chunks.append(chunk_text)
        
        # 如果这是最后一块，退出
        if end >= len(words):
            break
        
        # 下一块的开始位置（考虑重叠）
        start = end - overlap
        
        # 确保start不小于当前结束位置（避免无限循环）
        if start <= end - chunk_size:
            start = end
    
    return chunks


def clean_text(text: str) -> str:
    """清理文本
    
    Args:
        text: 输入文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符（保留基本标点）
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
    
    # 去除首尾空白
    text = text.strip()
    
    return text


def normalize_entity(entity: str) -> str:
    """标准化实体名称
    
    Args:
        entity: 实体名称
        
    Returns:
        标准化后的实体名称
    """
    if not entity:
        return ""
    
    # 转换为小写
    entity = entity.lower()
    
    # 移除多余空白
    entity = re.sub(r'\s+', ' ', entity)
    
    # 去除首尾空白
    entity = entity.strip()
    
    return entity


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """提取关键词
    
    Args:
        text: 输入文本
        min_length: 最小词长度
        
    Returns:
        关键词列表
    """
    if not text:
        return []
    
    # 提取词汇
    words = re.findall(r'\b\w+\b', text.lower())
    
    # 过滤长度和停用词
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
    }
    
    keywords = [
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    ]
    
    return list(set(keywords))  # 去重 