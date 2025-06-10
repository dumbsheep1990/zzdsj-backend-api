"""
Agno原生文档切分工具
提供基于Agno框架的文档切分功能，无依赖LlamaIndex
"""

import logging
import re
import hashlib
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class AgnoChunkingStrategy(str, Enum):
    """Agno切分策略"""
    SENTENCE = "sentence"               # 句子级切分
    PARAGRAPH = "paragraph"            # 段落级切分
    SEMANTIC = "semantic"              # 语义切分 
    FIXED_SIZE = "fixed_size"          # 固定大小切分
    RECURSIVE = "recursive"            # 递归切分
    MARKDOWN = "markdown"              # Markdown结构化切分
    CODE = "code"                      # 代码切分
    CONVERSATIONAL = "conversational" # 对话切分

@dataclass
class AgnoChunkingConfig:
    """Agno切分配置"""
    strategy: AgnoChunkingStrategy = AgnoChunkingStrategy.SENTENCE
    chunk_size: int = 1000            # 目标块大小（字符数）
    chunk_overlap: int = 200          # 重叠字符数
    min_chunk_size: int = 50          # 最小块大小
    max_chunk_size: int = 5000        # 最大块大小
    separator: str = "\n\n"           # 分隔符
    language: str = "zh"              # 文档语言
    preserve_metadata: bool = True    # 保留元数据
    
    # 高级配置
    respect_sentence_boundary: bool = True  # 尊重句子边界
    respect_word_boundary: bool = True      # 尊重词边界
    trim_whitespace: bool = True            # 去除空白字符
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy": self.strategy.value,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "min_chunk_size": self.min_chunk_size,
            "max_chunk_size": self.max_chunk_size,
            "separator": self.separator,
            "language": self.language,
            "preserve_metadata": self.preserve_metadata,
            "respect_sentence_boundary": self.respect_sentence_boundary,
            "respect_word_boundary": self.respect_word_boundary,
            "trim_whitespace": self.trim_whitespace
        }

@dataclass
class AgnoDocumentChunk:
    """Agno文档块"""
    id: str                                 # 块ID
    content: str                           # 块内容
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    start_char_idx: Optional[int] = None   # 起始字符索引
    end_char_idx: Optional[int] = None     # 结束字符索引
    chunk_index: int = 0                   # 块索引
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            # 生成内容哈希作为ID
            content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
            self.id = f"chunk_{content_hash}_{self.chunk_index}"
        
        # 计算字符索引
        if self.start_char_idx is None:
            self.start_char_idx = 0
        if self.end_char_idx is None:
            self.end_char_idx = len(self.content)
    
    @property
    def length(self) -> int:
        """获取块长度"""
        return len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "start_char_idx": self.start_char_idx,
            "end_char_idx": self.end_char_idx,
            "chunk_index": self.chunk_index,
            "length": self.length
        }

@dataclass 
class AgnoChunkingResult:
    """Agno切分结果"""
    chunks: List[AgnoDocumentChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        self._calculate_stats()
    
    def _calculate_stats(self):
        """计算统计信息"""
        if not self.chunks:
            self.stats = {
                "total_chunks": 0,
                "total_characters": 0,
                "average_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0
            }
            return
        
        chunk_sizes = [chunk.length for chunk in self.chunks]
        
        self.stats = {
            "total_chunks": len(self.chunks),
            "total_characters": sum(chunk_sizes),
            "average_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "metadata": self.metadata,
            "stats": self.stats
        }

class AgnoDocumentChunker:
    """Agno文档切分器"""
    
    def __init__(self, config: AgnoChunkingConfig = None):
        """
        初始化Agno文档切分器
        
        Args:
            config: 切分配置
        """
        self.config = config or AgnoChunkingConfig()
        logger.info(f"初始化Agno文档切分器: {self.config.strategy.value}")
    
    def chunk_text(self, 
                  text: str, 
                  metadata: Optional[Dict[str, Any]] = None) -> AgnoChunkingResult:
        """
        切分文本
        
        Args:
            text: 待切分文本
            metadata: 文档元数据
            
        Returns:
            切分结果
        """
        if not text or not text.strip():
            return AgnoChunkingResult(
                chunks=[],
                metadata=metadata or {},
                stats={}
            )
        
        # 预处理文本
        processed_text = self._preprocess_text(text)
        
        # 根据策略选择切分方法
        if self.config.strategy == AgnoChunkingStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.SEMANTIC:
            chunks = self._chunk_by_semantic(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.FIXED_SIZE:
            chunks = self._chunk_by_fixed_size(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.RECURSIVE:
            chunks = self._chunk_recursively(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.MARKDOWN:
            chunks = self._chunk_markdown(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.CODE:
            chunks = self._chunk_code(processed_text)
        elif self.config.strategy == AgnoChunkingStrategy.CONVERSATIONAL:
            chunks = self._chunk_conversational(processed_text)
        else:
            # 默认使用句子切分
            chunks = self._chunk_by_sentence(processed_text)
        
        # 后处理
        chunks = self._post_process_chunks(chunks, processed_text)
        
        # 创建结果
        result = AgnoChunkingResult(
            chunks=chunks,
            metadata={
                **(metadata or {}),
                "chunking_strategy": self.config.strategy.value,
                "chunking_config": self.config.to_dict(),
                "original_text_length": len(text),
                "processed_text_length": len(processed_text),
                "chunking_time": datetime.now().isoformat()
            }
        )
        
        logger.info(f"文档切分完成: {len(chunks)} 个块")
        return result
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 去除多余空白
        if self.config.trim_whitespace:
            text = re.sub(r'\s+', ' ', text.strip())
        
        # 规范化换行
        text = re.sub(r'\r\n|\r', '\n', text)
        
        return text
    
    def _chunk_by_sentence(self, text: str) -> List[AgnoDocumentChunk]:
        """按句子切分"""
        # 中英文句子分割模式
        if self.config.language == "zh":
            sentence_pattern = r'[。！？；]+'
        else:
            sentence_pattern = r'[.!?;]+'
        
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        start_idx = 0
        
        for sentence in sentences:
            # 检查添加这个句子是否会超过大小限制
            potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(potential_chunk) <= self.config.chunk_size or not current_chunk:
                current_chunk = potential_chunk
            else:
                # 创建当前块
                if current_chunk:
                    chunk = AgnoDocumentChunk(
                        id="",
                        content=current_chunk,
                        chunk_index=chunk_index,
                        start_char_idx=start_idx,
                        end_char_idx=start_idx + len(current_chunk)
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    start_idx += len(current_chunk)
                
                # 开始新块
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunk = AgnoDocumentChunk(
                id="",
                content=current_chunk,
                chunk_index=chunk_index,
                start_char_idx=start_idx,
                end_char_idx=start_idx + len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str) -> List[AgnoDocumentChunk]:
        """按段落切分"""
        paragraphs = text.split(self.config.separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        start_idx = 0
        
        for paragraph in paragraphs:
            potential_chunk = current_chunk + (self.config.separator if current_chunk else "") + paragraph
            
            if len(potential_chunk) <= self.config.chunk_size or not current_chunk:
                current_chunk = potential_chunk
            else:
                # 创建当前块
                if current_chunk:
                    chunk = AgnoDocumentChunk(
                        id="",
                        content=current_chunk,
                        chunk_index=chunk_index,
                        start_char_idx=start_idx,
                        end_char_idx=start_idx + len(current_chunk)
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    start_idx += len(current_chunk)
                
                # 开始新块
                current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk:
            chunk = AgnoDocumentChunk(
                id="",
                content=current_chunk,
                chunk_index=chunk_index,
                start_char_idx=start_idx,
                end_char_idx=start_idx + len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_semantic(self, text: str) -> List[AgnoDocumentChunk]:
        """语义切分（简化版本，可扩展）"""
        # 当前实现为句子切分的扩展版本
        # 可以集成更复杂的语义分析
        return self._chunk_by_sentence(text)
    
    def _chunk_by_fixed_size(self, text: str) -> List[AgnoDocumentChunk]:
        """固定大小切分"""
        chunks = []
        chunk_index = 0
        start_idx = 0
        
        while start_idx < len(text):
            end_idx = start_idx + self.config.chunk_size
            
            # 如果需要尊重词边界
            if self.config.respect_word_boundary and end_idx < len(text):
                # 寻找最近的空白字符
                while end_idx > start_idx and not text[end_idx].isspace():
                    end_idx -= 1
                
                # 如果没找到合适的断点，使用原始位置
                if end_idx == start_idx:
                    end_idx = start_idx + self.config.chunk_size
            
            chunk_text = text[start_idx:end_idx].strip()
            
            if chunk_text:
                chunk = AgnoDocumentChunk(
                    id="",
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_char_idx=start_idx,
                    end_char_idx=end_idx
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # 计算下一个块的起始位置（考虑重叠）
            start_idx = max(start_idx + 1, end_idx - self.config.chunk_overlap)
        
        return chunks
    
    def _chunk_recursively(self, text: str) -> List[AgnoDocumentChunk]:
        """递归切分"""
        separators = ["\n\n", "\n", "。", ".", " ", ""]
        return self._recursive_split(text, separators, 0)
    
    def _recursive_split(self, text: str, separators: List[str], sep_index: int) -> List[AgnoDocumentChunk]:
        """递归分割实现"""
        if len(text) <= self.config.chunk_size:
            return [AgnoDocumentChunk(id="", content=text, chunk_index=0)]
        
        if sep_index >= len(separators):
            # 强制切分
            return self._chunk_by_fixed_size(text)
        
        separator = separators[sep_index]
        if separator == "":
            # 字符级别切分
            return self._chunk_by_fixed_size(text)
        
        splits = text.split(separator)
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for split in splits:
            potential_chunk = current_chunk + (separator if current_chunk else "") + split
            
            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                if current_chunk:
                    # 递归处理当前块
                    sub_chunks = self._recursive_split(current_chunk, separators, sep_index + 1)
                    for sub_chunk in sub_chunks:
                        sub_chunk.chunk_index = chunk_index
                        chunks.append(sub_chunk)
                        chunk_index += 1
                
                current_chunk = split
        
        # 处理最后一个块
        if current_chunk:
            sub_chunks = self._recursive_split(current_chunk, separators, sep_index + 1)
            for sub_chunk in sub_chunks:
                sub_chunk.chunk_index = chunk_index
                chunks.append(sub_chunk)
                chunk_index += 1
        
        return chunks
    
    def _chunk_markdown(self, text: str) -> List[AgnoDocumentChunk]:
        """Markdown结构化切分"""
        # 简化的Markdown切分，按标题分割
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for line in lines:
            if line.startswith('#') and current_chunk:
                # 遇到新标题，结束当前块
                chunk = AgnoDocumentChunk(
                    id="",
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    metadata={"type": "markdown_section"}
                )
                chunks.append(chunk)
                chunk_index += 1
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
                
                # 检查大小限制
                if len(current_chunk) > self.config.chunk_size:
                    chunk = AgnoDocumentChunk(
                        id="",
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                        metadata={"type": "markdown_section"}
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk = ""
        
        # 处理最后一个块
        if current_chunk.strip():
            chunk = AgnoDocumentChunk(
                id="",
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                metadata={"type": "markdown_section"}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_code(self, text: str) -> List[AgnoDocumentChunk]:
        """代码切分"""
        # 简化的代码切分，按函数/类分割
        return self._chunk_by_paragraph(text)
    
    def _chunk_conversational(self, text: str) -> List[AgnoDocumentChunk]:
        """对话切分"""
        # 简化的对话切分，可以识别对话轮次
        return self._chunk_by_paragraph(text)
    
    def _post_process_chunks(self, chunks: List[AgnoDocumentChunk], original_text: str) -> List[AgnoDocumentChunk]:
        """后处理块"""
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            # 过滤太小的块
            if len(chunk.content) < self.config.min_chunk_size:
                if i > 0 and len(processed_chunks) > 0:
                    # 合并到前一个块
                    processed_chunks[-1].content += " " + chunk.content
                    continue
            
            # 过滤太大的块
            if len(chunk.content) > self.config.max_chunk_size:
                # 进一步切分
                sub_chunks = self._chunk_by_fixed_size(chunk.content)
                for j, sub_chunk in enumerate(sub_chunks):
                    sub_chunk.chunk_index = len(processed_chunks)
                    sub_chunk.metadata.update(chunk.metadata)
                    sub_chunk.metadata["is_sub_chunk"] = True
                    sub_chunk.metadata["parent_chunk_index"] = i
                    processed_chunks.append(sub_chunk)
            else:
                chunk.chunk_index = len(processed_chunks)
                processed_chunks.append(chunk)
        
        # 添加重叠（如果配置了）
        if self.config.chunk_overlap > 0:
            processed_chunks = self._add_overlap(processed_chunks)
        
        return processed_chunks
    
    def _add_overlap(self, chunks: List[AgnoDocumentChunk]) -> List[AgnoDocumentChunk]:
        """添加块重叠"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            current_chunk = chunks[i]
            
            # 从前一个块的末尾提取重叠内容
            overlap_start = max(0, len(prev_chunk.content) - self.config.chunk_overlap)
            overlap_content = prev_chunk.content[overlap_start:]
            
            # 创建带重叠的新块
            overlapped_content = overlap_content + " " + current_chunk.content
            
            overlapped_chunk = AgnoDocumentChunk(
                id=current_chunk.id,
                content=overlapped_content,
                chunk_index=current_chunk.chunk_index,
                start_char_idx=current_chunk.start_char_idx,
                end_char_idx=current_chunk.end_char_idx,
                metadata={
                    **current_chunk.metadata,
                    "has_overlap": True,
                    "overlap_length": len(overlap_content)
                }
            )
            
            overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks

# 便捷函数
def agno_chunk_text(text: str, 
                   strategy: AgnoChunkingStrategy = AgnoChunkingStrategy.SENTENCE,
                   chunk_size: int = 1000,
                   chunk_overlap: int = 200,
                   **kwargs) -> AgnoChunkingResult:
    """
    便捷的文本切分函数
    
    Args:
        text: 待切分文本
        strategy: 切分策略
        chunk_size: 块大小
        chunk_overlap: 重叠大小
        **kwargs: 其他配置参数
        
    Returns:
        切分结果
    """
    config = AgnoChunkingConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    
    chunker = AgnoDocumentChunker(config)
    return chunker.chunk_text(text)

def create_agno_chunker(strategy: AgnoChunkingStrategy = AgnoChunkingStrategy.SENTENCE,
                       **kwargs) -> AgnoDocumentChunker:
    """
    创建Agno文档切分器
    
    Args:
        strategy: 切分策略
        **kwargs: 配置参数
        
    Returns:
        文档切分器实例
    """
    config = AgnoChunkingConfig(strategy=strategy, **kwargs)
    return AgnoDocumentChunker(config)

# 单例获取
_agno_chunker = None

def get_agno_chunker() -> AgnoDocumentChunker:
    """获取默认Agno文档切分器单例"""
    global _agno_chunker
    if _agno_chunker is None:
        _agno_chunker = AgnoDocumentChunker()
    return _agno_chunker 