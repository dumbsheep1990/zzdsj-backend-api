"""
上下文压缩工具 - 支持TreeSummarize和CompactAndRefine压缩方法

该工具提供:
1. 树状总结 (TreeSummarize) - 将大型上下文递归分解为树状结构并总结
2. 紧凑精炼 (CompactAndRefine) - 先用压缩上下文生成初步回答，再用完整上下文精炼
3. 多种压缩策略可配置
4. 支持作为装饰器应用于任何Agent方法
"""

from typing import List, Dict, Any, Optional, Union, Callable, TypeVar, cast
import logging
import functools
import inspect
import time
import uuid
from pydantic import BaseModel, Field

from llama_index.core.response_synthesizers import TreeSummarize, CompactAndRefine
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import NodeWithScore, Document, QueryBundle
from llama_index.core.llms import LLM

from app.messaging.core.models import Message, MessageType, MessageRole
from app.messaging.core.formatters import convert_compressed_context_to_internal

logger = logging.getLogger(__name__)

class CompressionConfig(BaseModel):
    """上下文压缩配置"""
    enabled: bool = Field(True, description="是否启用上下文压缩")
    method: str = Field("tree_summarize", description="压缩方法: tree_summarize或compact_and_refine")
    top_n: int = Field(5, description="重排序保留的顶部结果数")
    num_children: int = Field(2, description="TreeSummarize每个节点的子节点数量")
    streaming: bool = Field(False, description="CompactAndRefine是否使用流式处理")
    rerank_model: str = Field("BAAI/bge-reranker-base", description="重排序模型名称")
    max_tokens: Optional[int] = Field(None, description="最大Token数限制")
    temperature: float = Field(0.1, description="生成温度")
    store_original: bool = Field(False, description="是否存储原始上下文（消耗内存）")
    use_message_format: bool = Field(True, description="是否使用消息格式传递压缩上下文")
    phase: str = Field("final", description="压缩阶段: retrieval或final")
    
class ContextCompressor:
    """上下文压缩工具类"""
    
    def __init__(
        self, 
        llm: Optional[LLM] = None,
        config: Optional[CompressionConfig] = None
    ):
        """
        初始化上下文压缩工具
        
        Args:
            llm: 语言模型实例，如果为None则使用全局配置的模型
            config: 压缩配置
        """
        self.llm = llm
        self.config = config or CompressionConfig()
        
    def compress_nodes(
        self, 
        nodes: List[NodeWithScore], 
        query: str,
        config: Optional[CompressionConfig] = None
    ) -> str:
        """
        压缩节点列表并返回摘要文本
        
        Args:
            nodes: 节点列表
            query: 查询字符串
            config: 压缩配置，如果为None则使用默认配置
            
        Returns:
            str: 压缩后的文本
        """
        compression_config = config or self.config
        
        if not compression_config.enabled or not nodes:
            # 压缩未启用或节点为空，返回原始内容连接
            return "\n\n".join([node.node.text for node in nodes])
        
        try:
            # 获取LLM
            from app.frameworks.llamaindex.core import get_llm
            llm = self.llm or get_llm()
            
            # 创建响应合成器
            if compression_config.method == "tree_summarize":
                # 首先应用重排序（如果启用）
                filtered_nodes = nodes
                if compression_config.top_n < len(nodes):
                    reranker = SentenceTransformerRerank(
                        top_n=compression_config.top_n,
                        model=compression_config.rerank_model
                    )
                    filtered_nodes = reranker.postprocess_nodes(
                        nodes, 
                        query_bundle=QueryBundle(query_str=query)
                    )
                
                # 应用树状总结
                synthesizer = TreeSummarize(
                    verbose=True,
                    llm=llm,
                    num_children=compression_config.num_children,
                    max_tokens=compression_config.max_tokens,
                    temperature=compression_config.temperature
                )
                
                response = synthesizer.synthesize(
                    query=query,
                    nodes=filtered_nodes
                )
                
                return response.response
                
            elif compression_config.method == "compact_and_refine":
                synthesizer = CompactAndRefine(
                    verbose=True,
                    llm=llm,
                    streaming=compression_config.streaming,
                    max_tokens=compression_config.max_tokens,
                    temperature=compression_config.temperature
                )
                
                response = synthesizer.synthesize(
                    query=query,
                    nodes=nodes
                )
                
                return response.response
            
            else:
                # 未知压缩方法，返回原始内容连接
                logger.warning(f"未知的压缩方法: {compression_config.method}")
                return "\n\n".join([node.node.text for node in nodes])
                
        except Exception as e:
            logger.error(f"压缩上下文时出错: {str(e)}")
            # 出错时返回原始内容
            return "\n\n".join([node.node.text for node in nodes])
    
    def compress_text(
        self, 
        text: str, 
        query: str,
        config: Optional[CompressionConfig] = None
    ) -> str:
        """
        压缩文本内容
        
        Args:
            text: 文本内容
            query: 查询字符串
            config: 压缩配置，如果为None则使用默认配置
            
        Returns:
            str: 压缩后的文本
        """
        # 将文本转换为节点
        doc = Document(text=text)
        node = NodeWithScore(node=doc.to_node(), score=1.0)
        
        # 调用节点压缩方法
        return self.compress_nodes([node], query, config)
    
    def compress_documents(
        self, 
        documents: List[Document], 
        query: str,
        config: Optional[CompressionConfig] = None
    ) -> str:
        """
        压缩文档列表
        
        Args:
            documents: 文档列表
            query: 查询字符串
            config: 压缩配置，如果为None则使用默认配置
            
        Returns:
            str: 压缩后的文本
        """
        # 将文档转换为节点
        nodes = [NodeWithScore(node=doc.to_node(), score=1.0) for doc in documents]
        
        # 调用节点压缩方法
        return self.compress_nodes(nodes, query, config)
    
    def compress_to_message(
        self,
        query: str,
        documents: Union[List[NodeWithScore], List[Document], str],
        config: Optional[CompressionConfig] = None
    ) -> Message:
        """
        压缩内容并返回标准消息格式
        
        Args:
            query: 查询字符串
            documents: 要压缩的文档或文本
            config: 压缩配置，如果为None则使用默认配置
            
        Returns:
            Message: 压缩上下文消息
        """
        compression_config = config or self.config
        
        # 测量开始时间
        start_time = time.time()
        
        # 存储原始内容（如果启用）
        original_text = None
        source_count = 0
        original_length = 0
        
        if isinstance(documents, str):
            original_text = documents if compression_config.store_original else None
            original_length = len(documents)
            source_count = 1
        elif isinstance(documents, list) and len(documents) > 0:
            source_count = len(documents)
            if hasattr(documents[0], "node") and hasattr(documents[0], "score"):
                # NodeWithScore列表
                if compression_config.store_original:
                    original_text = "\n\n".join([node.node.text for node in documents])
                original_length = sum(len(node.node.text) for node in documents)
            elif hasattr(documents[0], "text"):
                # Document列表
                if compression_config.store_original:
                    original_text = "\n\n".join([doc.text for doc in documents])
                original_length = sum(len(doc.text) for doc in documents)
        
        # 执行压缩
        compressed_text = ""
        try:
            if isinstance(documents, str):
                compressed_text = self.compress_text(documents, query, compression_config)
            elif isinstance(documents, list) and len(documents) > 0:
                if hasattr(documents[0], "node") and hasattr(documents[0], "score"):
                    # NodeWithScore列表
                    compressed_text = self.compress_nodes(documents, query, compression_config)
                elif hasattr(documents[0], "text"):
                    # Document列表
                    compressed_text = self.compress_documents(documents, query, compression_config)
                else:
                    raise ValueError("不支持的文档类型")
            else:
                raise ValueError("不支持的输入类型")
        except Exception as e:
            logger.error(f"压缩上下文时出错: {str(e)}")
            status = "failed"
            error_message = str(e)
            
            # 如果压缩失败，使用原始内容
            if isinstance(documents, str):
                compressed_text = documents
            elif isinstance(documents, list) and len(documents) > 0:
                if hasattr(documents[0], "node") and hasattr(documents[0], "score"):
                    compressed_text = "\n\n".join([node.node.text for node in documents])
                elif hasattr(documents[0], "text"):
                    compressed_text = "\n\n".join([doc.text for doc in documents])
        else:
            status = "success"
            error_message = None
        
        # 计算执行时间
        execution_time = int((time.time() - start_time) * 1000)  # 毫秒
        
        # 计算压缩比例
        compressed_length = len(compressed_text)
        compression_ratio = compressed_length / original_length if original_length > 0 else 1.0
        
        # 记录执行
        self._record_execution(
            query=query,
            original_length=original_length,
            compressed_length=compressed_length,
            compression_ratio=compression_ratio,
            source_count=source_count,
            execution_time=execution_time,
            status=status,
            error=error_message,
            config=compression_config
        )
        
        # 创建消息
        return convert_compressed_context_to_internal(
            compressed_text=compressed_text,
            original_text=original_text,
            method=compression_config.method,
            compression_ratio=compression_ratio,
            source_count=source_count,
            metadata={
                "query": query,
                "execution_time_ms": execution_time,
                "status": status
            }
        )
    
    def _record_execution(
        self,
        query: str,
        original_length: int,
        compressed_length: int,
        compression_ratio: float,
        source_count: int,
        execution_time: int,
        status: str,
        error: Optional[str] = None,
        config: Optional[CompressionConfig] = None
    ) -> None:
        """
        记录压缩执行记录到数据库
        
        Args:
            query: 查询字符串
            original_length: 原始内容长度
            compressed_length: 压缩内容长度
            compression_ratio: 压缩比例
            source_count: 源文档数量
            execution_time: 执行时间(毫秒)
            status: 状态
            error: 错误信息
            config: 压缩配置
        """
        try:
            from sqlalchemy.orm import Session
            from app.config import get_db
            from app.models.tool_execution import ToolExecution
            
            # 创建工具执行记录
            db = next(get_db())
            
            # 创建执行记录
            execution = ToolExecution.create(
                tool_id="context_compressor",
                input_params={
                    "query": query,
                    "method": config.method if config else "unknown",
                    "source_count": source_count
                }
            )
            
            # 设置输出结果
            execution.complete(
                output_result={
                    "original_length": original_length,
                    "compressed_length": compressed_length,
                    "compression_ratio": compression_ratio,
                    "status": status
                },
                execution_time=execution_time
            )
            
            # 如果有错误，记录错误
            if error:
                execution.error_message = error
                execution.status = "failed"
            
            # 保存到数据库
            db.add(execution)
            db.commit()
            
            # 尝试记录到专门的上下文压缩执行表
            try:
                from app.models.context_compression import ContextCompressionExecution
                
                compression_execution = ContextCompressionExecution(
                    execution_id=str(uuid.uuid4()),
                    query=query,
                    original_content_length=original_length,
                    compressed_content_length=compressed_length,
                    compression_ratio=compression_ratio,
                    source_count=source_count,
                    execution_time_ms=execution_time,
                    status=status,
                    error=error,
                    metadata={
                        "method": config.method if config else "unknown",
                        "config": config.dict() if config else {}
                    }
                )
                
                db.add(compression_execution)
                db.commit()
            except Exception as e:
                # 专门的表可能不存在，忽略错误
                logger.debug(f"记录到专门的上下文压缩执行表时出错: {str(e)}")
                pass
                
        except Exception as e:
            logger.error(f"记录压缩执行记录时出错: {str(e)}")
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        """获取工具元数据，用于工具注册"""
        return {
            "name": "context_compressor",
            "description": "上下文压缩工具，支持TreeSummarize和CompactAndRefine压缩方法",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要压缩的文本内容"
                    },
                    "query": {
                        "type": "string",
                        "description": "查询或问题，用于指导压缩过程"
                    },
                    "method": {
                        "type": "string",
                        "description": "压缩方法: tree_summarize或compact_and_refine",
                        "enum": ["tree_summarize", "compact_and_refine"]
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "重排序保留的顶部结果数"
                    },
                    "num_children": {
                        "type": "integer", 
                        "description": "TreeSummarize每个节点的子节点数量"
                    },
                    "store_original": {
                        "type": "boolean",
                        "description": "是否存储原始上下文（消耗内存）"
                    }
                },
                "required": ["text", "query"]
            }
        }

# 创建单例实例
_context_compressor = None

def get_context_compressor(llm: Optional[LLM] = None, config: Optional[CompressionConfig] = None) -> ContextCompressor:
    """获取上下文压缩工具实例"""
    global _context_compressor
    if _context_compressor is None or llm is not None or config is not None:
        _context_compressor = ContextCompressor(llm=llm, config=config)
    return _context_compressor
