"""
统一文档切分工具 - 基于LlamaIndex实现
封装LlamaIndex的DocumentProcessor和DocumentSplitterFactory，提供统一的切分接口
"""

from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
import logging
from datetime import datetime

# 导入LlamaIndex组件
from app.frameworks.llamaindex.document_processor import (
    DocumentSplitterFactory,
    SplitterType,
    DocumentProcessor as LlamaIndexDocumentProcessor,
    ProcessingTask,
    ProcessingStatus
)
from llama_index.core import Document
from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)

@dataclass
class ChunkingConfig:
    """统一的切分配置类"""
    strategy: str = "sentence"  # 对应SplitterType
    chunk_size: int = 1000
    chunk_overlap: int = 200
    language: str = "zh"
    preserve_structure: bool = True
    min_chunk_size: int = 100
    max_chunk_size: int = 5000
    
    # LlamaIndex特定参数
    include_metadata: bool = True
    include_prev_next_rel: bool = True
    
    # 语义切分参数
    semantic_threshold: float = 0.7
    buffer_size: int = 1
    
    # 窗口切分参数
    window_size: int = 3
    
    # 递归切分参数
    chunk_sizes: List[int] = field(default_factory=lambda: [2048, 1024, 512])
    
    # 自定义参数
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_llamaindex_params(self) -> Dict[str, Any]:
        """转换为LlamaIndex参数"""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "include_metadata": self.include_metadata,
            "include_prev_next_rel": self.include_prev_next_rel,
            "buffer_size": self.buffer_size,
            "window_size": self.window_size,
            "chunk_sizes": self.chunk_sizes,
            **self.custom_params
        }

@dataclass
class DocumentChunk:
    """统一的文档切片类"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: Optional[str] = None
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    embedding: Optional[List[float]] = None
    
    @classmethod
    def from_llamaindex_node(cls, node: TextNode) -> "DocumentChunk":
        """从LlamaIndex节点创建切片"""
        return cls(
            content=node.text,
            metadata=node.metadata,
            chunk_id=node.node_id,
            start_pos=node.start_char_idx,
            end_pos=node.end_char_idx,
            embedding=node.embedding
        )
    
    def to_llamaindex_node(self) -> TextNode:
        """转换为LlamaIndex节点"""
        return TextNode(
            text=self.content,
            metadata=self.metadata,
            id_=self.chunk_id,
            start_char_idx=self.start_pos,
            end_char_idx=self.end_pos,
            embedding=self.embedding
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "char_count": len(self.content),
            "token_count": self._estimate_token_count(),
            "has_embedding": self.embedding is not None
        }
    
    def _estimate_token_count(self) -> int:
        """估算token数量"""
        if any(ord(char) > 127 for char in self.content):
            return len(self.content)
        else:
            return int(len(self.content.split()) * 1.3)

@dataclass
class ChunkingResult:
    """切分结果类"""
    chunks: List[DocumentChunk]
    total_chunks: int = 0
    total_chars: int = 0
    strategy_used: str = ""
    config_used: Optional[ChunkingConfig] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        self.total_chunks = len(self.chunks)
        self.total_chars = sum(len(chunk.content) for chunk in self.chunks)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "total_chunks": self.total_chunks,
            "total_chars": self.total_chars,
            "strategy_used": self.strategy_used,
            "avg_chunk_size": self.total_chars / self.total_chunks if self.total_chunks > 0 else 0,
            "processing_time": self.processing_time,
            "created_at": datetime.now().isoformat()
        }

class DocumentChunkingTool:
    """统一文档切分工具 - 基于LlamaIndex实现"""
    
    def __init__(self):
        self.progress_callback: Optional[Callable[[str, float], None]] = None
    
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def chunk_document(self, content: str, config: Optional[ChunkingConfig] = None) -> ChunkingResult:
        """
        切分文档 - 使用LlamaIndex实现
        
        Args:
            content: 文档内容
            config: 切分配置
            
        Returns:
            切分结果
        """
        import time
        start_time = time.time()
        
        if not content or not content.strip():
            return ChunkingResult(chunks=[], strategy_used="none")
        
        config = config or ChunkingConfig()
        
        try:
            if self.progress_callback:
                self.progress_callback("开始文档切分", 0.1)
            
            # 创建LlamaIndex文档对象
            document = Document(text=content)
            
            if self.progress_callback:
                self.progress_callback("创建切分器", 0.2)
            
            # 获取切分器类型
            try:
                splitter_type = SplitterType(config.strategy)
            except ValueError:
                logger.warning(f"不支持的切分策略: {config.strategy}, 使用sentence策略")
                splitter_type = SplitterType.SENTENCE
            
            # 创建切分器
            splitter = DocumentSplitterFactory.create_splitter(
                splitter_type=splitter_type,
                **config.to_llamaindex_params()
            )
            
            if self.progress_callback:
                self.progress_callback("执行文档切分", 0.5)
            
            # 执行切分
            nodes = splitter.get_nodes_from_documents([document])
            
            if self.progress_callback:
                self.progress_callback("转换切分结果", 0.8)
            
            # 转换为统一格式
            chunks = []
            for node in nodes:
                chunk = DocumentChunk.from_llamaindex_node(node)
                # 添加额外的元数据
                chunk.metadata.update({
                    "strategy": config.strategy,
                    "language": config.language,
                    "created_at": datetime.now().isoformat()
                })
                chunks.append(chunk)
            
            # 过滤太小的切片
            chunks = [chunk for chunk in chunks if len(chunk.content.strip()) >= config.min_chunk_size]
            
            if self.progress_callback:
                self.progress_callback("切分完成", 1.0)
            
            processing_time = time.time() - start_time
            
            result = ChunkingResult(
                chunks=chunks,
                strategy_used=config.strategy,
                config_used=config,
                processing_time=processing_time
            )
            
            logger.info(f"文档切分完成: {result.total_chunks}个切片, 策略: {config.strategy}, 耗时: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"文档切分失败: {str(e)}")
            raise
    
    async def chunk_document_async(self, content: str, config: Optional[ChunkingConfig] = None, 
                                 task_id: Optional[str] = None) -> str:
        """
        异步切分文档 - 使用LlamaIndex的异步处理器
        
        Args:
            content: 文档内容
            config: 切分配置
            task_id: 任务ID
            
        Returns:
            任务ID
        """
        config = config or ChunkingConfig()
        
        # 创建临时文件用于异步处理
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_file = f.name
        
        try:
            # 获取LlamaIndex处理器
            processor = LlamaIndexDocumentProcessor()
            
            # 设置进度回调
            if self.progress_callback:
                def progress_wrapper(task_obj: ProcessingTask):
                    if self.progress_callback:
                        status_map = {
                            ProcessingStatus.INITIALIZED: "初始化",
                            ProcessingStatus.LOADING: "加载文档",
                            ProcessingStatus.SPLITTING: "切分文档",
                            ProcessingStatus.EMBEDDING: "生成向量",
                            ProcessingStatus.INDEXING: "建立索引",
                            ProcessingStatus.COMPLETED: "完成",
                            ProcessingStatus.FAILED: "失败",
                            ProcessingStatus.CANCELLED: "取消"
                        }
                        message = status_map.get(task_obj.status, str(task_obj.status))
                        self.progress_callback(message, task_obj.progress)
                
                # 注意：这里的回调设置需要根据实际的LlamaIndex实现调整
                processor.set_progress_callback(progress_wrapper)
            
            # 转换切分策略
            try:
                splitter_type = SplitterType(config.strategy)
            except ValueError:
                splitter_type = SplitterType.SENTENCE
            
            # 启动异步处理
            task_id = processor.process_document(
                source_path=temp_file,
                task_id=task_id,
                splitter_type=splitter_type,
                **config.to_llamaindex_params()
            )
            
            return task_id
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def get_available_strategies(self) -> List[Dict[str, str]]:
        """获取可用的切分策略"""
        strategies = []
        for strategy in SplitterType:
            strategies.append({
                "value": strategy.value,
                "label": self._get_strategy_label(strategy.value),
                "description": self._get_strategy_description(strategy.value)
            })
        return strategies
    
    def _get_strategy_label(self, strategy: str) -> str:
        """获取策略标签"""
        labels = {
            "sentence": "句子切分",
            "token": "Token切分",
            "semantic": "语义切分",
            "hybrid": "混合切分",
            "recursive": "递归切分",
            "markdown": "Markdown切分",
            "json": "JSON切分",
            "window": "窗口切分"
        }
        return labels.get(strategy, strategy)
    
    def _get_strategy_description(self, strategy: str) -> str:
        """获取策略描述"""
        descriptions = {
            "sentence": "按句子边界进行切分，保持语义完整",
            "token": "按Token数量精确切分，适合模型输入",
            "semantic": "基于语义相似度切分，保持语义连贯",
            "hybrid": "结合多种策略的混合切分",
            "recursive": "递归多层次切分，保持层次结构",
            "markdown": "按Markdown结构切分，保持文档结构",
            "json": "按JSON字段切分，处理结构化数据",
            "window": "句子窗口切分，包含前后文上下文"
        }
        return descriptions.get(strategy, "")
    
    def estimate_chunks(self, content: str, config: Optional[ChunkingConfig] = None) -> Dict[str, Any]:
        """估算切分结果"""
        config = config or ChunkingConfig()
        content_length = len(content)
        
        # 根据策略估算
        if config.strategy == "token":
            # Token切分比较精确
            estimated_chunks = max(1, content_length // (config.chunk_size - config.chunk_overlap))
        elif config.strategy == "sentence":
            # 句子切分估算
            sentence_count = content.count('。') + content.count('.') + content.count('!') + content.count('?')
            estimated_chunks = max(1, sentence_count // 3)  # 假设每个chunk包含3个句子
        elif config.strategy == "semantic":
            # 语义切分难以精确估算
            estimated_chunks = max(1, content_length // (config.chunk_size * 0.8))  # 考虑语义边界调整
        else:
            estimated_chunks = max(1, content_length // config.chunk_size)
        
        return {
            "estimated_chunks": estimated_chunks,
            "content_length": content_length,
            "avg_chunk_size": content_length // estimated_chunks if estimated_chunks > 0 else 0,
            "strategy": config.strategy
        }
    
    def validate_config(self, config: ChunkingConfig) -> ChunkingConfig:
        """验证和修正配置"""
        # 确保chunk_size在合理范围内
        if config.chunk_size < config.min_chunk_size:
            config.chunk_size = config.min_chunk_size
            logger.warning(f"chunk_size过小，已调整为{config.min_chunk_size}")
        elif config.chunk_size > config.max_chunk_size:
            config.chunk_size = config.max_chunk_size
            logger.warning(f"chunk_size过大，已调整为{config.max_chunk_size}")
        
        # 确保overlap不会超过chunk_size
        if config.chunk_overlap >= config.chunk_size:
            config.chunk_overlap = config.chunk_size // 2
            logger.warning(f"chunk_overlap过大，已调整为{config.chunk_overlap}")
        
        # 验证策略是否支持
        try:
            SplitterType(config.strategy)
        except ValueError:
            logger.warning(f"不支持的策略{config.strategy}，已调整为sentence")
            config.strategy = "sentence"
        
        return config

# 全局工具实例
_chunking_tool = None

def get_chunking_tool() -> DocumentChunkingTool:
    """获取全局切分工具实例"""
    global _chunking_tool
    if _chunking_tool is None:
        _chunking_tool = DocumentChunkingTool()
    return _chunking_tool 