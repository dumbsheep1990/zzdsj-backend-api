"""LightRAG文档处理组件
提供文档切分、加载和知识图谱构建的功能
"""

from typing import List, Dict, Any, Optional, Union, Callable, Tuple
import os
import logging
import time
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 尝试导入LightRAG依赖
try:
    import lightrag
    from lightrag import KnowledgeGraph
    from lightrag.schema import Document as LightDocument
    from lightrag.text import TextSplitter
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

# LlamaIndex文档类型
from llama_index.core import Document as LlamaDocument
from llama_index.core.schema import NodeWithScore, TextNode

# 内部模块
from app.config import settings
from app.frameworks.lightrag.graph import get_graph_manager, GraphManager

logger = logging.getLogger(__name__)

# 进度回调类型
ProgressCallback = Callable[[str, str, float, Optional[Dict[str, Any]]], None]

# 空回调函数
def null_callback(task_id: str, status: str, progress: float, info: Optional[Dict[str, Any]] = None) -> None:
    pass

class DocumentProcessor:
    """文档处理器，处理文档并构建知识图谱"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """初始化文档处理器
        
        参数:
            max_workers: 最大工作线程数，默认使用配置值
        """
        if not LIGHTRAG_AVAILABLE:
            logger.warning("LightRAG依赖未安装，文档处理功能不可用")
            self.enabled = False
            return
        
        self.enabled = settings.LIGHTRAG_ENABLED
        if not self.enabled:
            logger.info("LightRAG文档处理功能已禁用")
            return
        
        # 取配置值或默认值
        self.max_workers = max_workers or settings.LIGHTRAG_MAX_WORKERS
        self.graph_manager = get_graph_manager()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_tasks = {}
        
        logger.info(f"LightRAG文档处理器初始化: 并发数={self.max_workers}")
    
    def _convert_to_light_document(self, doc: Union[LlamaDocument, Dict[str, Any]]) -> LightDocument:
        """将LlamaIndex文档转换为LightRAG文档
        
        参数:
            doc: LlamaIndex文档或字典
            
        返回:
            LightRAG文档
        """
        # 如果是LlamaIndex文档
        if isinstance(doc, LlamaDocument):
            return LightDocument(
                id=doc.doc_id,
                content=doc.text,
                metadata=doc.metadata
            )
        # 如果是字典
        elif isinstance(doc, dict):
            doc_id = doc.get("id") or doc.get("doc_id") or str(time.time())
            content = doc.get("content") or doc.get("text") or ""
            metadata = doc.get("metadata") or {}
            
            return LightDocument(
                id=doc_id,
                content=content,
                metadata=metadata
            )
        else:
            raise ValueError(f"不支持的文档类型: {type(doc)}")
    
    def _convert_to_llama_document(self, doc: LightDocument) -> LlamaDocument:
        """将LightRAG文档转换为LlamaIndex文档
        
        参数:
            doc: LightRAG文档
            
        返回:
            LlamaIndex文档
        """
        return LlamaDocument(
            text=doc.content,
            metadata=doc.metadata,
            doc_id=doc.id
        )
    
    def process_documents(
        self,
        documents: List[Union[LlamaDocument, Dict[str, Any]]],
        graph_id: str,
        use_semantic_chunking: Optional[bool] = None,
        use_knowledge_graph: Optional[bool] = None,
        kg_relation_threshold: Optional[float] = None,
        callback: ProgressCallback = null_callback,
        task_id: Optional[str] = None
    ) -> str:
        """处理文档并构建知识图谱
        
        参数:
            documents: 要处理的文档列表
            graph_id: 知识图谱ID
            use_semantic_chunking: 是否使用语义切分
            use_knowledge_graph: 是否构建知识图谱
            kg_relation_threshold: 关系阈值
            callback: 进度回调
            task_id: 任务ID，如不提供则自动生成
            
        返回:
            任务ID
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            logger.warning("LightRAG功能未启用或依赖未安装")
            return ""
        
        # 使用默认配置或显式指定的参数
        use_semantic_chunking = use_semantic_chunking if use_semantic_chunking is not None else settings.LIGHTRAG_USE_SEMANTIC_CHUNKING
        use_knowledge_graph = use_knowledge_graph if use_knowledge_graph is not None else settings.LIGHTRAG_USE_KNOWLEDGE_GRAPH
        kg_relation_threshold = kg_relation_threshold if kg_relation_threshold is not None else settings.LIGHTRAG_KG_RELATION_THRESHOLD
        
        # 生成任务ID
        if not task_id:
            task_id = f"lightrag_process_{int(time.time())}_{len(documents)}"
        
        # 开始异步任务
        self.executor.submit(
            self._process_documents_async,
            task_id,
            documents,
            graph_id,
            use_semantic_chunking,
            use_knowledge_graph,
            kg_relation_threshold,
            callback
        )
        
        return task_id
    
    def _process_documents_async(
        self,
        task_id: str,
        documents: List[Union[LlamaDocument, Dict[str, Any]]],
        graph_id: str,
        use_semantic_chunking: bool,
        use_knowledge_graph: bool,
        kg_relation_threshold: float,
        callback: ProgressCallback
    ) -> None:
        """异步处理文档并构建知识图谱
        
        参数:
            task_id: 任务ID
            documents: 要处理的文档列表
            graph_id: 知识图谱ID
            use_semantic_chunking: 是否使用语义切分
            use_knowledge_graph: 是否构建知识图谱
            kg_relation_threshold: 关系阈值
            callback: 进度回调
        """
        try:
            # 记录活动任务
            self.active_tasks[task_id] = {
                "start_time": time.time(),
                "status": "initialized",
                "progress": 0.0
            }
            
            # 像回调函数报告开始状态
            callback(task_id, "initialized", 0.0, {
                "total_documents": len(documents),
                "use_semantic_chunking": use_semantic_chunking,
                "use_knowledge_graph": use_knowledge_graph
            })
            
            # 获取或创建图谱
            graph = self.graph_manager.get_graph(graph_id)
            if not graph:
                callback(task_id, "creating_graph", 0.1, {"graph_id": graph_id})
                graph = self.graph_manager.create_graph(graph_id)
                if not graph:
                    raise ValueError(f"无法创建图谱: {graph_id}")
            
            # 更新状态
            self.active_tasks[task_id]["status"] = "processing"
            callback(task_id, "processing", 0.2, {"graph_id": graph_id})
            
            # 转换文档
            light_documents = [self._convert_to_light_document(doc) for doc in documents]
            
            # 更新进度
            callback(task_id, "processing", 0.3, {"converted_documents": len(light_documents)})
            
            # 处理文档
            for i, doc in enumerate(light_documents):
                # 添加文档到图谱
                graph.add_document(doc)
                
                # 计算和更新进度
                progress = 0.3 + (i + 1) / len(light_documents) * 0.4
                callback(task_id, "processing", progress, {
                    "processed_documents": i + 1,
                    "total_documents": len(light_documents)
                })
            
            # 如果启用了知识图谱，则构建图谱关系
            if use_knowledge_graph:
                callback(task_id, "building_graph", 0.7, {"relation_threshold": kg_relation_threshold})
                
                # 调用LightRAG的图谱构建功能
                # 具体API取决于LightRAG的实现
                if hasattr(graph, "build_knowledge_graph"):
                    graph.build_knowledge_graph(threshold=kg_relation_threshold)
                elif hasattr(graph, "build_graph"):
                    graph.build_graph(threshold=kg_relation_threshold)
                else:
                    logger.warning("LightRAG图谱实例没有build_knowledge_graph或build_graph方法")
            
            # 完成
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["progress"] = 1.0
            self.active_tasks[task_id]["end_time"] = time.time()
            
            # 回调完成状态
            callback(task_id, "completed", 1.0, {
                "graph_id": graph_id,
                "total_documents": len(documents),
                "processed_documents": len(documents),
                "elapsed_seconds": time.time() - self.active_tasks[task_id]["start_time"]
            })
            
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            
            # 更新状态为失败
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "failed"
                self.active_tasks[task_id]["error"] = str(e)
                self.active_tasks[task_id]["end_time"] = time.time()
            
            # 回调失败状态
            callback(task_id, "failed", 0.0, {
                "error": str(e),
                "graph_id": graph_id
            })
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        参数:
            task_id: 任务ID
            
        返回:
            任务状态信息或None
        """
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id].copy()
            
            # 添加运行时间
            if "end_time" in task_info:
                task_info["elapsed_seconds"] = task_info["end_time"] - task_info["start_time"]
            else:
                task_info["elapsed_seconds"] = time.time() - task_info["start_time"]
                
            return task_info
        return None
    
    def clean_completed_tasks(self, max_age_seconds: int = 3600) -> int:
        """清理已完成的任务
        
        参数:
            max_age_seconds: 任务保留时间（秒）
            
        返回:
            清理的数量
        """
        now = time.time()
        to_remove = []
        
        for task_id, task_info in self.active_tasks.items():
            if task_info.get("status") in ["completed", "failed"]:
                if "end_time" in task_info and (now - task_info["end_time"]) > max_age_seconds:
                    to_remove.append(task_id)
                    
        for task_id in to_remove:
            del self.active_tasks[task_id]
            
        return len(to_remove)


# 全局单例
_document_processor_instance = None


def get_document_processor() -> DocumentProcessor:
    """获取文档处理器单例"""
    global _document_processor_instance
    
    if _document_processor_instance is None:
        _document_processor_instance = DocumentProcessor()
        
    return _document_processor_instance