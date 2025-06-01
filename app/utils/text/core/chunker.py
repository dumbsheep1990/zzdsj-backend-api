"""
文本分块器实现
从原始processor.py重构而来，优化了分块算法和性能
"""

import re
import logging
from typing import List, Optional, Set, Tuple

# 修复导入问题
try:
    from .base import TextChunker, ChunkConfig, TextProcessingError
except ImportError:
    # 如果相对导入失败，尝试直接导入
    from base import TextChunker, ChunkConfig, TextProcessingError

logger = logging.getLogger(__name__)

class SmartTextChunker(TextChunker):
    """智能文本分块器"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        super().__init__(config)
        # 预编译边界字符的正则表达式
        self._boundary_pattern = self._compile_boundary_pattern()
        # 缓存句子边界
        self._sentence_boundaries: Set[str] = {'.', '!', '?', '。', '！', '？'}
    
    def _compile_boundary_pattern(self) -> re.Pattern:
        """编译边界字符的正则表达式"""
        escaped_chars = re.escape(self.config.boundary_chars)
        return re.compile(f'[{escaped_chars}]')
    
    def chunk(self, text: str) -> List[str]:
        """智能文本分块"""
        if not text or self.config.chunk_size <= 0:
            return []
        
        # 预处理文本
        text = text.strip()
        if len(text) <= self.config.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # 计算当前块的结束位置
            end = min(start + self.config.chunk_size, text_len)
            
            # 如果不是最后一块且需要考虑边界，寻找最佳分割点
            if end < text_len and self.config.respect_boundaries:
                end = self._find_best_split_point(text, start, end)
            
            # 提取块
            chunk = text[start:end].strip()
            if chunk and len(chunk) >= self.config.min_chunk_size:
                chunks.append(chunk)
            
            # 计算下一个起始位置，考虑重叠
            start = self._calculate_next_start(end, start)
            
            # 防止无限循环
            if start >= end:
                if end < text_len:
                    start = end + 1
                else:
                    break
        
        return self.validate_chunks(chunks)
    
    def _find_best_split_point(self, text: str, start: int, initial_end: int) -> int:
        """寻找最佳分割点"""
        # 在chunk_size的80%-100%范围内寻找最佳分割点
        min_search_pos = start + int(self.config.chunk_size * 0.8)
        max_search_pos = min(initial_end, len(text))
        
        # 优先级：句子边界 > 段落边界 > 其他边界字符
        best_split = initial_end
        
        # 搜索范围
        search_range = text[min_search_pos:max_search_pos]
        
        # 1. 首先寻找句子边界
        sentence_pos = self._find_last_sentence_boundary(search_range)
        if sentence_pos != -1:
            return min_search_pos + sentence_pos + 1
        
        # 2. 寻找段落边界
        paragraph_pos = search_range.rfind('\n\n')
        if paragraph_pos != -1:
            return min_search_pos + paragraph_pos
        
        # 3. 寻找行边界
        line_pos = search_range.rfind('\n')
        if line_pos != -1:
            return min_search_pos + line_pos
        
        # 4. 寻找单词边界
        word_pos = search_range.rfind(' ')
        if word_pos != -1:
            return min_search_pos + word_pos
        
        # 5. 寻找其他边界字符
        boundary_match = None
        for match in self._boundary_pattern.finditer(search_range):
            boundary_match = match
        
        if boundary_match:
            return min_search_pos + boundary_match.end()
        
        # 如果都找不到，使用原始位置
        return initial_end
    
    def _find_last_sentence_boundary(self, text: str) -> int:
        """寻找最后一个句子边界"""
        last_pos = -1
        for boundary in self._sentence_boundaries:
            pos = text.rfind(boundary)
            if pos > last_pos:
                last_pos = pos
        return last_pos
    
    def _calculate_next_start(self, current_end: int, current_start: int) -> int:
        """计算下一个起始位置"""
        if self.config.chunk_overlap <= 0:
            return current_end
        
        next_start = current_end - self.config.chunk_overlap
        
        # 确保有进展
        if next_start <= current_start:
            return current_start + 1
        
        return next_start

class SemanticChunker(TextChunker):
    """语义感知的文本分块器"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        super().__init__(config)
    
    def chunk(self, text: str) -> List[str]:
        """基于语义的文本分块"""
        if not text:
            return []
        
        # 首先按段落分割
        paragraphs = self._split_by_paragraphs(text)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 如果当前段落本身就很长，需要进一步分割
            if len(paragraph) > self.config.chunk_size:
                # 保存当前块（如果有内容）
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 分割长段落
                sub_chunks = self._split_long_paragraph(paragraph)
                chunks.extend(sub_chunks)
            else:
                # 检查加入当前段落后是否超过大小限制
                potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
                
                if len(potential_chunk) <= self.config.chunk_size:
                    current_chunk = potential_chunk
                else:
                    # 保存当前块并开始新块
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return self.validate_chunks(chunks)
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        # 标准化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 按双换行符分割段落
        paragraphs = text.split('\n\n')
        
        # 清理并过滤空段落
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """分割过长的段落"""
        # 如果段落不是太长，直接返回
        if len(paragraph) <= self.config.chunk_size:
            return [paragraph]
        
        # 尝试按句子分割
        sentences = self._split_by_sentences(paragraph)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(sentence) > self.config.chunk_size:
                # 单个句子就超过限制，使用基本分块器
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                basic_chunker = SmartTextChunker(self.config)
                chunks.extend(basic_chunker.chunk(sentence))
            else:
                potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
                
                if len(potential_chunk) <= self.config.chunk_size:
                    current_chunk = potential_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        # 简单的句子分割（可以后续优化为更复杂的NLP分割）
        sentence_endings = r'[.!?。！？]'
        sentences = re.split(f'({sentence_endings})', text)
        
        # 重新组合句子和标点
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                sentence = sentence.strip()
                if sentence:
                    result.append(sentence)
        
        # 处理最后一个句子（如果没有标点结尾）
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        return result

class FixedSizeChunker(TextChunker):
    """固定大小分块器（简单且快速）"""
    
    def chunk(self, text: str) -> List[str]:
        """固定大小分块"""
        if not text:
            return []
        
        chunks = []
        text_len = len(text)
        start = 0
        
        while start < text_len:
            end = min(start + self.config.chunk_size, text_len)
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - self.config.chunk_overlap if self.config.chunk_overlap > 0 else end
            
            # 防止无限循环
            if start >= end:
                break
        
        return self.validate_chunks(chunks)

# 工厂函数
def create_chunker(chunker_type: str = "smart", config: Optional[ChunkConfig] = None) -> TextChunker:
    """创建文本分块器"""
    chunkers = {
        "smart": SmartTextChunker,
        "semantic": SemanticChunker,
        "fixed": FixedSizeChunker
    }
    
    if chunker_type not in chunkers:
        raise ValueError(f"未知的分块器类型: {chunker_type}")
    
    return chunkers[chunker_type](config)

# 便捷函数（向后兼容）
def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """向后兼容的文本分块函数"""
    config = ChunkConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunker = create_chunker("smart", config)
    return chunker.chunk(text) 