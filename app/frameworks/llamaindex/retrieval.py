"""
LlamaIndex检索模块: 处理高级上下文感知文档检索
利用LlamaIndex在分层检索和查询引擎方面的优势
支持ElasticSearch混合搜索策略
与Agno框架无缝集成
"""

from typing import List, Dict, Any, Optional, Union, Tuple, Callable
import json
import logging

from llama_index.core import (
    VectorStoreIndex, 
    Response,
    QueryBundle
)
from llama_index.core.retrievers import VectorIndexRetriever, BaseRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.prompts import PromptTemplate
from llama_index.core.schema import NodeWithScore
from app.config import settings
from app.frameworks.llamaindex.elasticsearch_store import get_elasticsearch_store
from app.frameworks.agno.knowledge_base import KnowledgeBaseProcessor

logger = logging.getLogger(__name__)

# 自定义提示模板，更好地控制响应格式
DEFAULT_TEXT_QA_PROMPT_TMPL = (
    "以下是上下文信息。\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "仅根据上下文信息，不使用先验知识，"
    "回答问题: {query_str}\n"
    "如果在上下文中找不到答案，"
    "请回答'我没有足够的信息来回答这个问题。'\n"
    "以简洁有帮助的方式回答。"
)

DEFAULT_REFINE_PROMPT_TMPL = (
    "原始问题是: {query_str}\n"
    "我们已经提供了现有答案: {existing_answer}\n"
    "我们有机会使用下面的更多上下文来完善现有答案。\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "如果上下文没有用，返回现有答案。"
    "否则，使用新上下文完善现有答案。"
)

class HybridRetriever(BaseRetriever):
    """混合检索器，结合向量检索和全文检索"""
    
    def __init__(
        self,
        vector_retriever: VectorIndexRetriever,
        similarity_top_k: int = 5,
        es_index_name: Optional[str] = None,
        hybrid_weight: float = 0.5,
        use_hybrid: bool = True,
        agno_kb_id: Optional[str] = None
    ):
        """
        初始化混合检索器
        
        参数：
            vector_retriever: 向量检索器
            similarity_top_k: 检索的最大结果数
            es_index_name: ES索引名称
            hybrid_weight: 向量搜索在混合搜索中的权重 (0.0-1.0)
            use_hybrid: 是否使用混合搜索（否则仅使用向量搜索）
            agno_kb_id: 可选的Agno知识库ID，如提供则结合Agno检索
        """
        self.vector_retriever = vector_retriever
        self.similarity_top_k = similarity_top_k
        self.es_store = get_elasticsearch_store(index_name=es_index_name)
        self.hybrid_weight = hybrid_weight
        self.use_hybrid = use_hybrid
        self.agno_kb_id = agno_kb_id
        self.agno_kb = None
        
        # 如果提供了Agno知识库ID，初始化知识库处理器
        if agno_kb_id:
            try:
                self.agno_kb = KnowledgeBaseProcessor(kb_id=agno_kb_id)
            except Exception as e:
                logger.warning(f"初始化Agno知识库失败: {str(e)}")
        
        super().__init__()
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """实现检索方法"""
        query_text = query_bundle.query_str
        query_embedding = query_bundle.embedding
        
        # 尝试使用Agno检索
        agno_results = []
        if self.agno_kb:
            try:
                import asyncio
                agno_results_raw = asyncio.run(self.agno_kb.retrieve(query_text, top_k=self.similarity_top_k))
                
                # 转换成NodeWithScore格式
                for result in agno_results_raw:
                    from llama_index.core.schema import TextNode
                    node = TextNode(
                        text=result["content"],
                        metadata=result.get("metadata", {})
                    )
                    agno_results.append(NodeWithScore(
                        node=node, 
                        score=result.get("score", 1.0)
                    ))
            except Exception as e:
                logger.error(f"Agno检索失败: {str(e)}")
        
        # 如果不使用混合搜索或Agno检索成功，直接返回结果
        if not self.use_hybrid:
            if agno_results:
                return agno_results
            return self.vector_retriever.retrieve(query_bundle)
        
        # 使用混合检索
        try:
            # 执行混合搜索
            es_results = self.es_store.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                top_k=self.similarity_top_k,
                vector_weight=self.hybrid_weight
            )
            
            # 如果有Agno结果，合并并排序
            if agno_results:
                combined_results = es_results + agno_results
                # 按分数排序
                combined_results.sort(key=lambda x: x.score, reverse=True)
                # 截取前K个
                return combined_results[:self.similarity_top_k]
            
            return es_results
        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}，回退到向量检索")
            # 如果有Agno结果，返回Agno结果
            if agno_results:
                return agno_results
            # 否则回退到向量检索
            return self.vector_retriever.retrieve(query_bundle)

def get_retriever(
    index: Optional[VectorStoreIndex] = None,
    similarity_top_k: int = 5,
    use_hybrid: bool = True,
    hybrid_weight: float = 0.5,
    es_index_name: Optional[str] = None,
    agno_kb_id: Optional[str] = None
) -> BaseRetriever:
    """
    获取检索器，支持向量检索和混合检索
    
    参数：
        index: 可选的向量存储索引
        similarity_top_k: 检索的最大结果数
        use_hybrid: 是否使用混合检索
        hybrid_weight: 向量搜索在混合搜索中的权重 (0.0-1.0)
        es_index_name: ES索引名称
        agno_kb_id: 可选的Agno知识库ID
        
    返回：
        检索器实例
    """
    # 如果提供了索引，则使用其向量检索器
    if index:
        vector_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=similarity_top_k
        )
    else:
        # 否则创建ES存储，并使用向量检索
        es_store = get_elasticsearch_store(index_name=es_index_name)
        vector_retriever = None  # 需要在HybridRetriever内部处理
    
    # 确定是否使用混合检索
    if use_hybrid and (vector_retriever or es_store):
        # 只有当vector_retriever存在时才使用HybridRetriever
        if vector_retriever:
            return HybridRetriever(
                vector_retriever=vector_retriever,
                similarity_top_k=similarity_top_k,
                es_index_name=es_index_name,
                hybrid_weight=hybrid_weight,
                use_hybrid=use_hybrid,
                agno_kb_id=agno_kb_id
            )
        else:
            # 如果没有向量检索器，但有ES，使用ES的混合搜索
            class ESHybridRetriever(BaseRetriever):
                def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
                    results = es_store.hybrid_search(
                        query_text=query_bundle.query_str,
                        query_embedding=query_bundle.embedding,
                        top_k=similarity_top_k,
                        vector_weight=hybrid_weight
                    )
                    
                    # 如果提供了Agno知识库ID，尝试获取Agno结果
                    if agno_kb_id:
                        try:
                            import asyncio
                            agno_kb = KnowledgeBaseProcessor(kb_id=agno_kb_id)
                            agno_results_raw = asyncio.run(agno_kb.retrieve(
                                query_bundle.query_str, 
                                top_k=similarity_top_k
                            ))
                            
                            # 转换成NodeWithScore格式
                            agno_results = []
                            for result in agno_results_raw:
                                from llama_index.core.schema import TextNode
                                node = TextNode(
                                    text=result["content"],
                                    metadata=result.get("metadata", {})
                                )
                                agno_results.append(NodeWithScore(
                                    node=node, 
                                    score=result.get("score", 1.0)
                                ))
                            
                            # 合并结果
                            combined_results = results + agno_results
                            # 按分数排序
                            combined_results.sort(key=lambda x: x.score, reverse=True)
                            # 截取前K个
                            return combined_results[:similarity_top_k]
                        except Exception as e:
                            logger.error(f"Agno检索失败: {str(e)}")
                    
                    return results
            
            return ESHybridRetriever()
    
    # 如果不使用混合检索，返回向量检索器或基于ES的检索器
    if vector_retriever:
        if agno_kb_id:  # 如果提供了Agno知识库ID，使用包装器结合Agno结果
            class AgnoVectorRetriever(BaseRetriever):
                def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
                    # 先获取向量检索结果
                    vector_results = vector_retriever.retrieve(query_bundle)
                    
                    # 尝试获取Agno结果
                    try:
                        import asyncio
                        agno_kb = KnowledgeBaseProcessor(kb_id=agno_kb_id)
                        agno_results_raw = asyncio.run(agno_kb.retrieve(
                            query_bundle.query_str, 
                            top_k=similarity_top_k
                        ))
                        
                        # 转换成NodeWithScore格式
                        agno_results = []
                        for result in agno_results_raw:
                            from llama_index.core.schema import TextNode
                            node = TextNode(
                                text=result["content"],
                                metadata=result.get("metadata", {})
                            )
                            agno_results.append(NodeWithScore(
                                node=node, 
                                score=result.get("score", 1.0)
                            ))
                        
                        # 合并结果
                        combined_results = vector_results + agno_results
                        # 按分数排序
                        combined_results.sort(key=lambda x: x.score, reverse=True)
                        # 截取前K个
                        return combined_results[:similarity_top_k]
                    except Exception as e:
                        logger.error(f"Agno检索失败: {str(e)}")
                        return vector_results
            
            return AgnoVectorRetriever()
        return vector_retriever
    else:
        class ESVectorRetriever(BaseRetriever):
            def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
                if query_bundle.embedding:
                    results = es_store._vector_search(
                        query_embedding=query_bundle.embedding,
                        top_k=similarity_top_k
                    )
                else:
                    results = es_store._text_search(
                        query_text=query_bundle.query_str,
                        top_k=similarity_top_k
                    )
                
                # 如果提供了Agno知识库ID，尝试获取Agno结果
                if agno_kb_id:
                    try:
                        import asyncio
                        agno_kb = KnowledgeBaseProcessor(kb_id=agno_kb_id)
                        agno_results_raw = asyncio.run(agno_kb.retrieve(
                            query_bundle.query_str, 
                            top_k=similarity_top_k
                        ))
                        
                        # 转换成NodeWithScore格式
                        agno_results = []
                        for result in agno_results_raw:
                            from llama_index.core.schema import TextNode
                            node = TextNode(
                                text=result["content"],
                                metadata=result.get("metadata", {})
                            )
                            agno_results.append(NodeWithScore(
                                node=node, 
                                score=result.get("score", 1.0)
                            ))
                        
                        # 合并结果
                        combined_results = results + agno_results
                        # 按分数排序
                        combined_results.sort(key=lambda x: x.score, reverse=True)
                        # 截取前K个
                        return combined_results[:similarity_top_k]
                    except Exception as e:
                        logger.error(f"Agno检索失败: {str(e)}")
                
                return results
        
        return ESVectorRetriever()

def get_query_engine(
    index: Optional[VectorStoreIndex] = None,
    similarity_top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7,
    use_hybrid: Optional[bool] = None,
    hybrid_weight: Optional[float] = None,
    es_index_name: Optional[str] = None,
    agno_kb_id: Optional[str] = None
):
    """
    获取具有自定义设置的查询引擎
    
    参数：
        index: 要使用的向量索引，可选
        similarity_top_k: 检索的最大结果数
        similarity_cutoff: 最小相似度阈值
        use_hybrid: 是否使用混合检索，默认使用配置值
        hybrid_weight: 向量搜索权重，默认使用配置值
        es_index_name: ES索引名称
        agno_kb_id: 可选的Agno知识库ID
        
    返回：
        配置好的查询引擎
    """
    # 使用配置值或默认值
    _use_hybrid = use_hybrid if use_hybrid is not None else settings.ELASTICSEARCH_HYBRID_SEARCH
    _hybrid_weight = hybrid_weight if hybrid_weight is not None else settings.ELASTICSEARCH_HYBRID_WEIGHT
    
    # 创建检索器
    retriever = get_retriever(
        index=index, 
        similarity_top_k=similarity_top_k,
        use_hybrid=_use_hybrid,
        hybrid_weight=_hybrid_weight,
        es_index_name=es_index_name,
        agno_kb_id=agno_kb_id
    )
    
    # 创建提示模板
    text_qa_template = PromptTemplate(DEFAULT_TEXT_QA_PROMPT_TMPL)
    refine_template = PromptTemplate(DEFAULT_REFINE_PROMPT_TMPL)
    
    # 定义后处理器
    postprocessors = []
    if similarity_cutoff is not None:
        postprocessors.append(SimilarityPostprocessor(similarity_cutoff=similarity_cutoff))
    
    # 创建查询引擎
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        node_postprocessors=postprocessors
    )
    
    return query_engine

async def retrieve_documents(
    query: str,
    index: Optional[VectorStoreIndex] = None,
    top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7,
    use_hybrid: Optional[bool] = None,
    hybrid_weight: Optional[float] = None,
    es_index_name: Optional[str] = None,
    agno_kb_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    使用LlamaIndex检索相关文档
    
    参数：
        query: 要搜索的查询字符串
        index: 要搜索的LlamaIndex
        top_k: 要检索的文档数量
        similarity_cutoff: 可选的最小相似度分数
        use_hybrid: 是否使用混合检索
        hybrid_weight: 向量搜索权重
        es_index_name: ES索引名称
        agno_kb_id: 可选的Agno知识库ID
        
    返回：
        文档字典列表，包含内容和元数据
    """
    # 使用配置值或默认值
    _use_hybrid = use_hybrid if use_hybrid is not None else settings.ELASTICSEARCH_HYBRID_SEARCH
    _hybrid_weight = hybrid_weight if hybrid_weight is not None else settings.ELASTICSEARCH_HYBRID_WEIGHT
    
    # 创建检索器
    retriever = get_retriever(
        index=index, 
        similarity_top_k=top_k,
        use_hybrid=_use_hybrid,
        hybrid_weight=_hybrid_weight,
        es_index_name=es_index_name,
        agno_kb_id=agno_kb_id
    )
    
    # 创建查询包
    query_bundle = QueryBundle(query)
    
    # 执行检索
    nodes = retriever.retrieve(query_bundle)
    
    # 应用后处理
    if similarity_cutoff is not None:
        nodes = [node for node in nodes if node.score >= similarity_cutoff]
    
    # 将结果转换为字典列表
    results = []
    for node in nodes:
        doc = {
            "text": node.node.get_content(),
            "metadata": node.node.metadata,
            "score": node.score
        }
        results.append(doc)
    
    return results

async def query_documents(
    query: str,
    index: Optional[VectorStoreIndex] = None,
    top_k: int = 5,
    similarity_cutoff: Optional[float] = 0.7,
    return_sources: bool = True,
    use_hybrid: Optional[bool] = None,
    hybrid_weight: Optional[float] = None,
    es_index_name: Optional[str] = None,
    agno_kb_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询文档并获取综合答案
    
    参数：
        query: 要搜索的查询字符串
        index: 要搜索的LlamaIndex
        top_k: 要检索的文档数量
        similarity_cutoff: 可选的最小相似度分数
        return_sources: 是否在响应中包含源文档
        use_hybrid: 是否使用混合检索
        hybrid_weight: 向量搜索权重
        es_index_name: ES索引名称
        agno_kb_id: 可选的Agno知识库ID
        
    返回：
        包含答案和可选源文档的字典
    """
    # 获取查询引擎
    query_engine = get_query_engine(
        index=index, 
        similarity_top_k=top_k,
        similarity_cutoff=similarity_cutoff,
        use_hybrid=use_hybrid,
        hybrid_weight=hybrid_weight,
        es_index_name=es_index_name,
        agno_kb_id=agno_kb_id
    )
    
    # 执行查询
    response = query_engine.query(query)
    
    # 提取结果
    result = {
        "answer": response.response,
    }
    
    # 如果请求源文档，并且可用
    if return_sources and hasattr(response, "source_nodes") and response.source_nodes:
        sources = []
        for source_node in response.source_nodes:
            source = {
                "text": source_node.node.get_content(),
                "metadata": source_node.node.metadata,
                "score": source_node.score
            }
            sources.append(source)
        result["sources"] = sources
    
    return result

def create_custom_query_engine(
    index: Optional[VectorStoreIndex] = None,
    query_template: str = DEFAULT_TEXT_QA_PROMPT_TMPL,
    stream: bool = False,
    use_hybrid: Optional[bool] = None,
    hybrid_weight: Optional[float] = None,
    es_index_name: Optional[str] = None,
    agno_kb_id: Optional[str] = None
) -> RetrieverQueryEngine:
    """
    创建具有特定模板的自定义查询引擎
    
    参数：
        index: 要使用的LlamaIndex
        query_template: 自定义查询提示模板
        stream: 是否启用流式响应
        use_hybrid: 是否使用混合检索
        hybrid_weight: 向量搜索权重
        es_index_name: ES索引名称
        agno_kb_id: 可选的Agno知识库ID
        
    返回：
        自定义查询引擎
    """
    # 使用配置值或默认值
    _use_hybrid = use_hybrid if use_hybrid is not None else settings.ELASTICSEARCH_HYBRID_SEARCH
    _hybrid_weight = hybrid_weight if hybrid_weight is not None else settings.ELASTICSEARCH_HYBRID_WEIGHT
    
    # 创建检索器
    retriever = get_retriever(
        index=index, 
        similarity_top_k=5,
        use_hybrid=_use_hybrid,
        hybrid_weight=_hybrid_weight,
        es_index_name=es_index_name,
        agno_kb_id=agno_kb_id
    )
    
    # 创建自定义提示模板
    custom_template = PromptTemplate(query_template)
    
    # 创建查询引擎
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=custom_template,
        streaming=stream
    )
    
    return query_engine
