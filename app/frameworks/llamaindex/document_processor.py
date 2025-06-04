"""
文档处理模块，提供高级文档切分、元数据提取和索引功能
支持动态配置、并发处理和进度回调
"""

from typing import List, Dict, Any, Optional, Union, Callable, Tuple, Type
from enum import Enum
import os
import asyncio
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

from llama_index.core import Document
from llama_index.core.schema import NodeWithScore, TextNode, MetadataMode
from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
    SentenceWindowNodeParser,
    SemanticSplitterNodeParser,
)
from llama_index.core.node_parser.interface import NodeParser
from llama_index.readers.file import PDFReader, DocxReader, UnstructuredReader
from llama_index.readers.markdown import MarkdownReader
from llama_index.readers.json import JSONReader
from llama_index.readers.web import SimpleWebPageReader

from app.config import settings
from app.frameworks.llamaindex.elasticsearch_store import get_elasticsearch_store
from app.frameworks.llamaindex.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

# 切分器类型枚举
class SplitterType(str, Enum):
    SENTENCE = "sentence"
    TOKEN = "token"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    RECURSIVE = "recursive"
    MARKDOWN = "markdown"
    JSON = "json"
    WINDOW = "window"

# 进度回调状态枚举
class ProcessingStatus(str, Enum):
    INITIALIZED = "initialized"
    LOADING = "loading"
    SPLITTING = "splitting"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 进度回调类型
ProgressCallback = Callable[[str, ProcessingStatus, float, Optional[Dict[str, Any]]], None]

# 空回调函数
def null_callback(task_id: str, status: ProcessingStatus, progress: float, info: Optional[Dict[str, Any]] = None) -> None:
    """
    默认的空回调函数，不执行任何操作
    
    参数:
        task_id: 任务ID
        status: 处理状态
        progress: 进度百分比 (0.0-1.0)
        info: 附加信息
    """
    # 可以在这里添加默认的日志记录
    logger.debug(f"Task {task_id}: {status.value} - {progress:.1%} {info or ''}")

class ProcessingTask:
    """处理任务对象，用于跟踪任务状态和进度"""
    
    def __init__(self, task_id: str, callback: ProgressCallback = null_callback):
        self.task_id = task_id
        self.callback = callback
        self.status = ProcessingStatus.INITIALIZED
        self.progress = 0.0
        self.start_time = datetime.now()
        self.end_time = None
        self.result = None
        self.error = None
        self.cancelled = False
        self.extra_info = {}
    
    def update_progress(self, status: ProcessingStatus, progress: float, info: Optional[Dict[str, Any]] = None) -> None:
        """更新任务进度并触发回调"""
        self.status = status
        self.progress = progress
        
        if info:
            self.extra_info.update(info)
        
        if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
            self.end_time = datetime.now()
        
        # 触发回调
        self.callback(self.task_id, status, progress, self.extra_info)
    
    def cancel(self) -> None:
        """取消任务"""
        self.cancelled = True
        self.update_progress(ProcessingStatus.CANCELLED, self.progress)
    
    def is_cancelled(self) -> bool:
        """检查任务是否已取消"""
        return self.cancelled
    
    def get_elapsed_time(self) -> float:
        """获取任务已运行时间（秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取任务摘要信息"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_seconds": self.get_elapsed_time(),
            "cancelled": self.cancelled,
            "extra_info": self.extra_info
        }

class DocumentSplitterFactory:
    """文档切分器工厂，根据配置创建各种切分器"""
    
    @staticmethod
    def create_splitter(
        splitter_type: SplitterType,
        chunk_size: int = None,
        chunk_overlap: int = None,
        **kwargs
    ) -> NodeParser:
        """
        创建切分器
        
        参数:
            splitter_type: 切分器类型
            chunk_size: 块大小
            chunk_overlap: 块重叠
            **kwargs: 附加参数
            
        返回:
            配置好的NodeParser
        """
        # 使用默认值或配置中的值
        chunk_size = chunk_size or settings.DOCUMENT_CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.DOCUMENT_CHUNK_OVERLAP
        
        if splitter_type == SplitterType.SENTENCE:
            return SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                paragraph_separator=kwargs.get("paragraph_separator", "\n\n"),
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.TOKEN:
            return TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.SEMANTIC:
            buffer_size = kwargs.get("buffer_size", 1)
            embed_model = get_embedding_model()
            
            return SemanticSplitterNodeParser(
                buffer_size=buffer_size,
                embed_model=embed_model,
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.WINDOW:
            window_size = kwargs.get("window_size", 3)
            
            return SentenceWindowNodeParser(
                window_size=window_size, 
                sentence_splitter=SentenceSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                ),
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.RECURSIVE:
            # 递归切分器实现，根据嵌套结构分层切分
            from llama_index.core.node_parser import HierarchicalNodeParser
            
            return HierarchicalNodeParser.from_defaults(
                chunk_sizes=kwargs.get("chunk_sizes", [2048, 1024, 512]),
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.MARKDOWN:
            # Markdown特定切分器
            from llama_index.core.node_parser import MarkdownNodeParser
            
            return MarkdownNodeParser(
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.JSON:
            # JSON特定切分器
            from llama_index.core.node_parser import JSONNodeParser
            
            return JSONNodeParser(
                include_metadata=kwargs.get("include_metadata", True),
                include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
            )
        
        elif splitter_type == SplitterType.HYBRID:
            # 混合切分器 - 结合语义和句子切分
            semantic_splitter = SemanticSplitterNodeParser(
                buffer_size=kwargs.get("buffer_size", 1),
                embed_model=get_embedding_model(),
                include_metadata=kwargs.get("include_metadata", True)
            )
            
            sentence_splitter = SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                include_metadata=kwargs.get("include_metadata", True)
            )
            
            # 返回主切分器，这里使用语义切分
            # 在实际应用中可以增加更复杂的混合逻辑
            return semantic_splitter
        
        # 默认使用句子切分器
        return SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            include_metadata=kwargs.get("include_metadata", True),
            include_prev_next_rel=kwargs.get("include_prev_next_rel", True)
        )

class DocumentProcessor:
    """文档处理器，负责文档加载、切分、向量化和索引"""
    
    def __init__(
        self, 
        concurrency: int = None, 
        default_splitter_type: SplitterType = None,
        default_chunk_size: int = None,
        default_chunk_overlap: int = None,
        es_index_name: str = None
    ):
        """
        初始化文档处理器
        
        参数:
            concurrency: 并发处理线程数
            default_splitter_type: 默认切分器类型
            default_chunk_size: 默认块大小
            default_chunk_overlap: 默认块重叠
            es_index_name: ES索引名称
        """
        # 使用配置值或默认值
        self.concurrency = concurrency or settings.DOCUMENT_PROCESSING_CONCURRENCY
        self.default_splitter_type = default_splitter_type or SplitterType(settings.DOCUMENT_SPLITTER_TYPE)
        self.default_chunk_size = default_chunk_size or settings.DOCUMENT_CHUNK_SIZE
        self.default_chunk_overlap = default_chunk_overlap or settings.DOCUMENT_CHUNK_OVERLAP
        
        # 获取或创建ES存储
        self.es_store = get_elasticsearch_store(index_name=es_index_name)
        
        # 获取嵌入模型
        self.embedding_model = get_embedding_model()
        
        # 任务管理
        self.tasks = {}
        self.executor = ThreadPoolExecutor(max_workers=self.concurrency)
        
        logger.info(f"初始化文档处理器: 并发={self.concurrency}, 切分器={self.default_splitter_type.value}")
    
    def process_document(
        self,
        source_path: str,
        task_id: str = None,
        callback: ProgressCallback = null_callback,
        splitter_type: SplitterType = None,
        chunk_size: int = None,
        chunk_overlap: int = None,
        metadata_extractor_configs: List[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_prev_next_rel: bool = True,
        **kwargs
    ) -> str:
        """
        处理文档 - 同步方法，启动异步任务
        
        参数:
            source_path: 文档路径或URL
            task_id: 可选任务ID，如不提供则自动生成
            callback: 进度回调函数
            splitter_type: 切分器类型
            chunk_size: 块大小
            chunk_overlap: 块重叠
            metadata_extractor_configs: 元数据提取器配置列表
            include_metadata: 是否包含元数据
            include_prev_next_rel: 是否包含前后文关系
            **kwargs: 附加参数
            
        返回:
            任务ID
        """
        # 创建任务ID（如果未提供）
        task_id = task_id or str(uuid.uuid4())
        
        # 创建任务对象
        task = ProcessingTask(task_id, callback)
        self.tasks[task_id] = task
        
        # 更新初始进度
        task.update_progress(
            ProcessingStatus.INITIALIZED, 
            0.0, 
            {
                "source_path": source_path,
                "splitter_type": splitter_type.value if splitter_type else self.default_splitter_type.value,
                "chunk_size": chunk_size or self.default_chunk_size,
                "chunk_overlap": chunk_overlap or self.default_chunk_overlap,
            }
        )
        
        # 启动异步处理
        self.executor.submit(
            self._process_document_async,
            task,
            source_path,
            splitter_type or self.default_splitter_type,
            chunk_size or self.default_chunk_size,
            chunk_overlap or self.default_chunk_overlap,
            metadata_extractor_configs,
            include_metadata,
            include_prev_next_rel,
            **kwargs
        )
        
        return task_id
    
    def _process_document_async(
        self,
        task: ProcessingTask,
        source_path: str,
        splitter_type: SplitterType,
        chunk_size: int,
        chunk_overlap: int,
        metadata_extractor_configs: List[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_prev_next_rel: bool = True,
        **kwargs
    ) -> None:
        """
        异步处理文档
        
        参数:
            task: 处理任务对象
            source_path: 文档路径或URL
            splitter_type: 切分器类型
            chunk_size: 块大小
            chunk_overlap: 块重叠
            metadata_extractor_configs: 元数据提取器配置列表
            include_metadata: 是否包含元数据
            include_prev_next_rel: 是否包含前后文关系
            **kwargs: 附加参数
        """
        try:
            # 1. 加载文档
            task.update_progress(ProcessingStatus.LOADING, 0.1, {"message": "正在加载文档..."})
            
            documents = self._load_document(source_path, **kwargs)
            if not documents:
                task.update_progress(
                    ProcessingStatus.FAILED, 
                    0.0, 
                    {"error": f"无法加载文档: {source_path}"}
                )
                return
            
            # 更新加载进度
            doc_count = len(documents)
            task.update_progress(
                ProcessingStatus.LOADING, 
                0.2, 
                {
                    "message": f"已加载{doc_count}个文档",
                    "document_count": doc_count
                }
            )
            
            # 2. 配置切分器
            splitter = DocumentSplitterFactory.create_splitter(
                splitter_type,
                chunk_size,
                chunk_overlap,
                include_metadata=include_metadata,
                include_prev_next_rel=include_prev_next_rel,
                **kwargs
            )
            
            # 3. 进行文档切分
            task.update_progress(
                ProcessingStatus.SPLITTING, 
                0.3, 
                {"message": "正在切分文档..."}
            )
            
            nodes = splitter.get_nodes_from_documents(documents)
            node_count = len(nodes)
            
            task.update_progress(
                ProcessingStatus.SPLITTING, 
                0.4, 
                {
                    "message": f"已切分为{node_count}个节点",
                    "node_count": node_count
                }
            )
            
            # 4. 元数据提取和增强
            if metadata_extractor_configs:
                task.update_progress(
                    ProcessingStatus.EMBEDDING, 
                    0.4, 
                    {"message": "正在提取文档元数据..."}
                )
                
                # 实现多种元数据提取策略
                for config in metadata_extractor_configs:
                    extractor_type = config.get("type", "")
                    
                    try:
                        if extractor_type == "summary":
                            # 自动摘要提取
                            await self._extract_summaries(nodes, config)
                        elif extractor_type == "keywords":
                            # 关键词提取
                            await self._extract_keywords(nodes, config)
                        elif extractor_type == "topics":
                            # 主题标签提取
                            await self._extract_topics(nodes, config)
                        elif extractor_type == "entities":
                            # 实体识别提取
                            await self._extract_entities(nodes, config)
                        elif extractor_type == "questions":
                            # 问题生成
                            await self._generate_questions(nodes, config)
                        else:
                            logger.warning(f"未知的元数据提取器类型: {extractor_type}")
                            
                    except Exception as e:
                        logger.error(f"元数据提取失败 ({extractor_type}): {str(e)}")
                        # 继续处理其他提取器
            
            # 5. 向量化
            task.update_progress(
                ProcessingStatus.EMBEDDING, 
                0.5, 
                {"message": "正在生成文本向量..."}
            )
            
            # 批量处理向量化，提高效率
            batch_size = settings.EMBEDDING_BATCH_SIZE
            for i in range(0, len(nodes), batch_size):
                # 检查任务是否被取消
                if task.is_cancelled():
                    task.update_progress(
                        ProcessingStatus.CANCELLED, 
                        i / len(nodes), 
                        {"message": "任务已取消"}
                    )
                    return
                
                batch = nodes[i:i+batch_size]
                progress = 0.5 + (0.3 * (i / len(nodes)))
                
                # 更新向量化进度
                task.update_progress(
                    ProcessingStatus.EMBEDDING, 
                    progress, 
                    {
                        "message": f"正在生成向量批次 {i//batch_size + 1}/{(len(nodes)-1)//batch_size + 1}",
                        "current_batch": i//batch_size + 1,
                        "total_batches": (len(nodes)-1)//batch_size + 1
                    }
                )
                
                # 为每个节点生成嵌入向量
                for node in batch:
                    if not node.embedding:
                        text = node.get_content(metadata_mode=MetadataMode.NONE)
                        try:
                            node.embedding = self.embedding_model.get_text_embedding(text)
                        except Exception as e:
                            logger.error(f"生成嵌入向量时出错: {str(e)}")
                            # 继续处理其他节点
            
            # 6. 保存到ES
            task.update_progress(
                ProcessingStatus.INDEXING, 
                0.8, 
                {"message": "正在索引到Elasticsearch..."}
            )
            
            # 添加到ES存储
            try:
                self.es_store.add(nodes)
                
                # 索引完成
                task.update_progress(
                    ProcessingStatus.COMPLETED, 
                    1.0, 
                    {
                        "message": "文档处理完成",
                        "document_count": doc_count,
                        "node_count": node_count,
                        "index_name": self.es_store._index_name
                    }
                )
                
            except Exception as e:
                logger.error(f"保存到Elasticsearch时出错: {str(e)}")
                task.update_progress(
                    ProcessingStatus.FAILED, 
                    0.8, 
                    {"error": f"索引文档时出错: {str(e)}"}
                )
        
        except Exception as e:
            logger.error(f"处理文档时出错: {str(e)}")
            task.update_progress(
                ProcessingStatus.FAILED, 
                0.0, 
                {"error": str(e)}
            )
    
    def _load_document(self, source_path: str, **kwargs) -> List[Document]:
        """
        加载文档
        
        参数:
            source_path: 文档路径或URL
            **kwargs: 附加参数
            
        返回:
            Document对象列表
        """
        try:
            # 检查是否为URL
            if source_path.startswith(("http://", "https://")):
                return SimpleWebPageReader().load_data([source_path])
            
            # 检查路径是否存在
            if not os.path.exists(source_path):
                logger.error(f"文件或目录不存在: {source_path}")
                return []
            
            # 如果是目录，使用目录加载器
            if os.path.isdir(source_path):
                from llama_index.core import SimpleDirectoryReader
                
                # 获取文件扩展名过滤器
                file_extns = kwargs.get("file_extns", None)
                exclude_hidden = kwargs.get("exclude_hidden", True)
                
                return SimpleDirectoryReader(
                    source_path, 
                    file_extns=file_extns,
                    exclude_hidden=exclude_hidden
                ).load_data()
            
            # 如果是文件，根据扩展名选择加载器
            file_ext = os.path.splitext(source_path)[-1].lower()
            
            if file_ext == ".pdf":
                return PDFReader().load_data(source_path)
                
            elif file_ext in [".docx", ".doc"]:
                return DocxReader().load_data(source_path)
                
            elif file_ext in [".md", ".markdown"]:
                return MarkdownReader().load_data(source_path)
                
            elif file_ext in [".json"]:
                return JSONReader().load_data(source_path)
                
            # 其他文件类型使用通用加载器
            return UnstructuredReader().load_data(source_path)
                
        except Exception as e:
            logger.error(f"加载文档 {source_path} 时出错: {str(e)}")
            return []
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        参数:
            task_id: 任务ID
            
        返回:
            任务状态摘要，如果任务不存在则返回None
        """
        task = self.tasks.get(task_id)
        if task:
            return task.get_summary()
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        参数:
            task_id: 任务ID
            
        返回:
            取消是否成功
        """
        task = self.tasks.get(task_id)
        if task:
            task.cancel()
            return True
        return False
    
    def clear_completed_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        清理已完成的旧任务
        
        参数:
            max_age_seconds: 最大保留时间（秒）
            
        返回:
            清理的任务数量
        """
        now = datetime.now()
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                if task.end_time and (now - task.end_time).total_seconds() > max_age_seconds:
                    tasks_to_remove.append(task_id)
        
        # 删除旧任务
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        return len(tasks_to_remove)
    
    def close(self):
        """关闭处理器并释放资源"""
        # 取消所有正在运行的任务
        for task_id, task in self.tasks.items():
            if task.status not in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                task.cancel()
        
        # 关闭线程池
        self.executor.shutdown(wait=False)
    
    # 元数据提取方法
    async def _extract_summaries(self, nodes: List[BaseNode], config: Dict[str, Any]) -> None:
        """提取文档摘要"""
        try:
            from llama_index.core.llms import LLM
            from llama_index.core import Settings
            
            llm = Settings.llm
            max_length = config.get("max_length", 150)
            
            for node in nodes:
                if len(node.text) > 200:  # 只为较长的文本生成摘要
                    prompt = f"请为以下文本生成{max_length}字以内的摘要:\n\n{node.text[:2000]}"
                    try:
                        response = await llm.acomplete(prompt)
                        node.metadata["summary"] = response.text.strip()
                    except:
                        # 简化摘要逻辑
                        node.metadata["summary"] = node.text[:max_length] + "..."
                        
        except Exception as e:
            logger.error(f"摘要提取失败: {str(e)}")
    
    async def _extract_keywords(self, nodes: List[BaseNode], config: Dict[str, Any]) -> None:
        """提取关键词"""
        try:
            import re
            from collections import Counter
            
            max_keywords = config.get("max_keywords", 10)
            
            for node in nodes:
                # 简单的关键词提取（基于词频）
                text = re.sub(r'[^\w\s]', '', node.text.lower())
                words = [word for word in text.split() if len(word) > 3]
                
                # 过滤常见停用词
                stop_words = {'这个', '那个', '可以', '需要', '进行', '使用', '具有', '包括', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                words = [word for word in words if word not in stop_words]
                
                # 提取高频词作为关键词
                keyword_counts = Counter(words)
                keywords = [word for word, _ in keyword_counts.most_common(max_keywords)]
                node.metadata["keywords"] = keywords
                
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
    
    async def _extract_topics(self, nodes: List[BaseNode], config: Dict[str, Any]) -> None:
        """提取主题标签"""
        try:
            # 基于关键词的简单主题分类
            topic_keywords = {
                "技术": ["技术", "开发", "编程", "代码", "algorithm", "programming", "development"],
                "商业": ["商业", "市场", "销售", "客户", "business", "market", "sales"],
                "教育": ["教育", "学习", "培训", "知识", "education", "learning", "training"],
                "健康": ["健康", "医疗", "治疗", "健身", "health", "medical", "fitness"],
                "科学": ["科学", "研究", "实验", "理论", "science", "research", "theory"]
            }
            
            for node in nodes:
                text_lower = node.text.lower()
                detected_topics = []
                
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if keyword in text_lower:
                            detected_topics.append(topic)
                            break
                
                node.metadata["topics"] = list(set(detected_topics))
                
        except Exception as e:
            logger.error(f"主题提取失败: {str(e)}")
    
    async def _extract_entities(self, nodes: List[BaseNode], config: Dict[str, Any]) -> None:
        """提取实体信息"""
        try:
            import re
            
            for node in nodes:
                entities = {
                    "dates": [],
                    "emails": [],
                    "urls": [],
                    "phone_numbers": []
                }
                
                # 提取日期
                date_pattern = r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4}年\d{1,2}月\d{1,2}日'
                entities["dates"] = re.findall(date_pattern, node.text)
                
                # 提取邮箱
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                entities["emails"] = re.findall(email_pattern, node.text)
                
                # 提取URL
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                entities["urls"] = re.findall(url_pattern, node.text)
                
                # 提取电话号码
                phone_pattern = r'\d{3}-\d{3}-\d{4}|\d{11}|1[3-9]\d{9}'
                entities["phone_numbers"] = re.findall(phone_pattern, node.text)
                
                node.metadata["entities"] = entities
                
        except Exception as e:
            logger.error(f"实体提取失败: {str(e)}")
    
    async def _generate_questions(self, nodes: List[BaseNode], config: Dict[str, Any]) -> None:
        """生成问题"""
        try:
            max_questions = config.get("max_questions", 3)
            
            for node in nodes:
                if len(node.text) > 100:
                    # 基于文本内容生成简单问题
                    questions = []
                    
                    # 基于关键词生成问题
                    if "什么" not in node.text.lower():
                        questions.append(f"什么是{node.text.split('。')[0][:20]}？")
                    
                    if "如何" not in node.text.lower():
                        questions.append(f"如何{node.text.split('。')[0][:20]}？")
                    
                    if "为什么" not in node.text.lower():
                        questions.append(f"为什么{node.text.split('。')[0][:20]}？")
                    
                    node.metadata["questions"] = questions[:max_questions]
                    
        except Exception as e:
            logger.error(f"问题生成失败: {str(e)}")

# 全局单例
_processor_instance = None

def get_document_processor() -> DocumentProcessor:
    """
    获取全局文档处理器实例
    
    返回:
        DocumentProcessor实例
    """
    global _processor_instance
    
    if _processor_instance is None:
        _processor_instance = DocumentProcessor()
    
    return _processor_instance
