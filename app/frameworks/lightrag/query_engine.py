"""LightRAG查询引擎组件
提供基于知识图谱的查询功能
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import logging
from pathlib import Path
import json

try:
    import lightrag
    from lightrag import KnowledgeGraph
    from lightrag.retriever import GraphRetriever
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False

# LlamaIndex集成
from llama_index.core.schema import NodeWithScore, TextNode, Document
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.response_synthesizers import ResponseSynthesizer
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.llms import LLM
from llama_index.core.response.schema import Response
from llama_index.core import PromptTemplate

# 内部模块
from app.config import settings
from app.frameworks.lightrag.graph import get_graph_manager
from app.frameworks.llamaindex.core import get_service_context, get_llm

logger = logging.getLogger(__name__)

# RAG提示模板
RAG_PROMPT_TEMPLATE = """你是一个帮助用户回答问题的智能助手。您将收到以下信息:

1. 用户查询: {query}
2. 相关知识库片段:
{context}

使用提供的知识库片段中的信息回答用户的查询。如果知识库片段中没有足够信息来回答查询，请建议用户提供更多细节或改写其问题。如果知识库片段中包含相关信息，请连贯这些信息给出全面、准确的回答。

你的回答应包含:
1. 只使用知识库片段中的信息。
2. 清晰、简洁的结构。
3. 直接回答用户问题，不要重复问题。

你的回答:"""


class LightRAGRetriever(BaseRetriever):
    """基于LightRAG的检索器实现"""
    
    def __init__(
        self,
        graph_id: str,
        top_k: int = 5,
        use_graph_relations: bool = True,
        similarity_top_k: int = 10
    ):
        """初始化检索器
        
        参数:
            graph_id: 知识图谱ID
            top_k: 返回的最大结果数
            use_graph_relations: 是否使用图谱关系增强检索
            similarity_top_k: 相似度搜索的最大结果数
        """
        super().__init__()
        
        if not LIGHTRAG_AVAILABLE:
            raise ImportError("LightRAG依赖未安装，无法创建检索器")
        
        self.graph_id = graph_id
        self.top_k = top_k
        self.use_graph_relations = use_graph_relations
        self.similarity_top_k = similarity_top_k
        
        # 获取图谱
        self.graph_manager = get_graph_manager()
        self.graph = self.graph_manager.get_graph(graph_id)
        
        if not self.graph:
            raise ValueError(f"找不到知识图谱: {graph_id}")
        
        # 创建LightRAG检索器
        if hasattr(lightrag, 'GraphRetriever'):
            self.retriever = GraphRetriever(self.graph)
        elif hasattr(self.graph, 'retriever') and self.graph.retriever is not None:
            self.retriever = self.graph.retriever
        else:
            raise ValueError("LightRAG不支持GraphRetriever，请更新LightRAG版本")
        
        logger.info(f"LightRAG检索器初始化: 图谱={graph_id}, 使用关系={use_graph_relations}")
    
    def _node_from_chunk(self, chunk: Any, score: float) -> NodeWithScore:
        """将LightRAG的文档块转换为LlamaIndex的节点
        
        参数:
            chunk: LightRAG的文档块
            score: 相关性分数
            
        返回:
            LlamaIndex节点
        """
        # LightRAG的文档块结构可能会根据具体实现而不同
        # 这里提供一个通用的转换逻辑，可能需要根据LightRAG的API调整
        if hasattr(chunk, 'content') and hasattr(chunk, 'metadata'):
            # 标准情况，直接使用内容和元数据
            content = chunk.content
            metadata = chunk.metadata
        elif hasattr(chunk, 'text') and hasattr(chunk, 'metadata'):
            # 替代属性名称
            content = chunk.text
            metadata = chunk.metadata
        elif isinstance(chunk, dict):
            # 字典形式
            content = chunk.get('content', '') or chunk.get('text', '')
            metadata = chunk.get('metadata', {}) or {}
        else:
            # 默认使用字符串表示
            content = str(chunk)
            metadata = {}
        
        # 创建TextNode并返回
        node = TextNode(
            text=content,
            metadata=metadata,
            id_=metadata.get('id', None) or str(hash(content))
        )
        
        return NodeWithScore(node=node, score=score)
    
    async def _aretrieve(self, query: str) -> List[NodeWithScore]:
        """异步检索相关文档
        
        参数:
            query: 查询文本
            
        返回:
            相关文档节点列表
        """
        try:
            # 使用LightRAG的检索API查询
            # 具体API取决于LightRAG的实现，可能需要调整
            if hasattr(self.retriever, 'retrieve_with_graph') and self.use_graph_relations:
                # 使用图谱增强的检索
                chunks = self.retriever.retrieve_with_graph(
                    query=query,
                    top_k=self.top_k,
                    similarity_top_k=self.similarity_top_k
                )
            elif hasattr(self.retriever, 'retrieve'):
                # 标准检索
                chunks = self.retriever.retrieve(
                    query=query,
                    top_k=self.top_k
                )
            else:
                raise NotImplementedError("LightRAG检索器未实现retrieve或retrieve_with_graph方法")
            
            # 转换为LlamaIndex节点
            nodes = []
            for i, chunk in enumerate(chunks):
                # 计算分数，如果没有提供则根据位置计算
                score = getattr(chunk, 'score', 1.0 - (i / max(1, len(chunks))))
                nodes.append(self._node_from_chunk(chunk, score))
            
            return nodes
        except Exception as e:
            logger.error(f"LightRAG检索失败: {str(e)}")
            return []
    
    def retrieve(self, query: str) -> List[NodeWithScore]:
        """同步检索相关文档
        
        参数:
            query: 查询文本
            
        返回:
            相关文档节点列表
        """
        import asyncio
        return asyncio.run(self._aretrieve(query))


class LightRAGQueryEngine(BaseQueryEngine):
    """基于LightRAG的查询引擎"""
    
    def __init__(
        self,
        graph_id: str,
        llm: Optional[LLM] = None,
        top_k: int = 5,
        use_graph_relations: bool = True,
        similarity_top_k: int = 10,
        response_synthesizer: Optional[ResponseSynthesizer] = None,
        prompt_template: Optional[str] = None
    ):
        """初始化查询引擎
        
        参数:
            graph_id: 知识图谱ID
            llm: 大语言模型
            top_k: 检索结果数量
            use_graph_relations: 是否使用图谱关系
            similarity_top_k: 相似度检索结果数量
            response_synthesizer: 响应合成器
            prompt_template: 提示模板
        """
        # 初始化基类
        super().__init__()
        
        # 保存配置
        self.graph_id = graph_id
        self.top_k = top_k
        self.use_graph_relations = use_graph_relations
        
        # 获取或创建LLM
        self.llm = llm or get_llm()
        
        # 创建检索器
        self.retriever = LightRAGRetriever(
            graph_id=graph_id,
            top_k=top_k,
            use_graph_relations=use_graph_relations,
            similarity_top_k=similarity_top_k
        )
        
        # 创建响应合成器
        if response_synthesizer is None:
            from llama_index.core.response_synthesizers import get_response_synthesizer
            # 创建提示模板
            rag_prompt_template = PromptTemplate(prompt_template or RAG_PROMPT_TEMPLATE)
            self.response_synthesizer = get_response_synthesizer(
                llm=self.llm,
                text_qa_template=rag_prompt_template
            )
        else:
            self.response_synthesizer = response_synthesizer
        
        logger.info(f"LightRAG查询引擎初始化: 图谱={graph_id}, 使用关系={use_graph_relations}")
    
    async def _aquery(self, query_str: str) -> Response:
        """异步查询
        
        参数:
            query_str: 查询文本
            
        返回:
            查询响应
        """
        # 检索相关文档
        nodes = await self.retriever._aretrieve(query_str)
        
        if not nodes:
            # 如果没有找到相关文档，返回指定响应
            return Response(
                response="很抱歉，我无法在知识库中找到与您的问题相关的信息。请尝试用其他方式描述您的问题，或者提供更多细节。",
                source_nodes=nodes,
                metadata={
                    "graph_id": self.graph_id,
                    "nodes_found": 0
                }
            )
        
        # 使用响应合成器生成回答
        response = await self.response_synthesizer.asynthesize(
            query_str=query_str,
            nodes=nodes
        )
        
        # 添加元数据
        if not hasattr(response, "metadata") or response.metadata is None:
            response.metadata = {}
        
        response.metadata["graph_id"] = self.graph_id
        response.metadata["nodes_found"] = len(nodes)
        response.metadata["use_graph_relations"] = self.use_graph_relations
        
        # 添加源节点
        response.source_nodes = nodes
        
        return response
    
    def query(self, query_str: str) -> Response:
        """同步查询
        
        参数:
            query_str: 查询文本
            
        返回:
            查询响应
        """
        import asyncio
        return asyncio.run(self._aquery(query_str))


def create_lightrag_query_engine(
    graph_id: str,
    llm: Optional[LLM] = None,
    top_k: int = 5,
    use_graph_relations: bool = True,
    similarity_top_k: int = 10,
    prompt_template: Optional[str] = None
) -> LightRAGQueryEngine:
    """创建LightRAG查询引擎
    
    参数:
        graph_id: 知识图谱ID
        llm: 大语言模型
        top_k: 检索结果数量
        use_graph_relations: 是否使用图谱关系
        similarity_top_k: 相似度检索结果数量
        prompt_template: 提示模板
        
    返回:
        LightRAG查询引擎
    """
    if not LIGHTRAG_AVAILABLE:
        raise ImportError("LightRAG依赖未安装，无法创建查询引擎")
    
    if not settings.LIGHTRAG_ENABLED:
        raise ValueError("LightRAG功能未启用，请在配置中启用")
    
    # 检查图谱是否存在
    graph_manager = get_graph_manager()
    graph = graph_manager.get_graph(graph_id)
    
    if not graph:
        raise ValueError(f"找不到知识图谱: {graph_id}")
    
    # 创建查询引擎
    return LightRAGQueryEngine(
        graph_id=graph_id,
        llm=llm,
        top_k=top_k,
        use_graph_relations=use_graph_relations,
        similarity_top_k=similarity_top_k,
        prompt_template=prompt_template
    )