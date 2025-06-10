"""
Agno检索模块: 提供强大的向量检索和语义搜索功能
基于Agno框架的内置检索能力，支持多种检索策略和20+向量数据库
实现高性能的异步检索和智能重排序
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import logging
import asyncio
from dataclasses import dataclass

from app.config import settings
from app.frameworks.agno.config import get_agno_config
from app.frameworks.agno.knowledge_base import AgnoKnowledgeBase
from app.frameworks.agno.vector_store import get_vector_store, AgnoVectorStore

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """检索结果数据类"""
    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str
    source_id: Optional[str] = None

class AgnoRetriever:
    """Agno检索器基类"""
    
    def __init__(
        self,
        knowledge_base: AgnoKnowledgeBase,
        similarity_top_k: int = 5,
        similarity_cutoff: float = 0.7,
        retrieval_strategy: str = "vector",
        **kwargs
    ):
        """
        初始化Agno检索器
        
        参数:
            knowledge_base: Agno知识库实例
            similarity_top_k: 返回的相似结果数量
            similarity_cutoff: 相似度阈值
            retrieval_strategy: 检索策略 ('vector', 'hybrid', 'semantic')
            **kwargs: 其他配置参数
        """
        self.knowledge_base = knowledge_base
        self.similarity_top_k = similarity_top_k
        self.similarity_cutoff = similarity_cutoff
        self.retrieval_strategy = retrieval_strategy
        self.config = kwargs
        
        # 初始化向量存储
        self.vector_store = get_vector_store(
            collection_name=f"kb_{knowledge_base.kb_id}",
            store_type="milvus"
        )
        
        # 初始化嵌入模型
        self.embedding_model = self._init_embedding_model()
    
    def _init_embedding_model(self):
        """初始化嵌入模型"""
        try:
            from agno.embeddings import OpenAIEmbeddings
            
            config = get_agno_config()
            return OpenAIEmbeddings(
                model=config.default_embedding_model,
                api_key=settings.OPENAI_API_KEY
            )
        except Exception as e:
            logger.error(f"初始化嵌入模型失败: {str(e)}")
            raise
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """
        执行检索查询
        
        参数:
            query: 查询字符串
            **kwargs: 检索参数覆盖
            
        返回:
            检索结果列表
        """
        try:
            # 合并检索参数
            retrieval_params = {
                "top_k": kwargs.get("top_k", self.similarity_top_k),
                "cutoff": kwargs.get("cutoff", self.similarity_cutoff),
                "strategy": kwargs.get("strategy", self.retrieval_strategy)
            }
            
            # 根据策略执行检索
            if retrieval_params["strategy"] == "vector":
                return await self._vector_retrieve(query, retrieval_params)
            elif retrieval_params["strategy"] == "hybrid":
                return await self._hybrid_retrieve(query, retrieval_params)
            elif retrieval_params["strategy"] == "semantic":
                return await self._semantic_retrieve(query, retrieval_params)
            else:
                raise ValueError(f"不支持的检索策略: {retrieval_params['strategy']}")
                
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []
    
    async def _vector_retrieve(self, query: str, params: Dict[str, Any]) -> List[RetrievalResult]:
        """向量检索"""
        try:
            # 生成查询向量
            query_embedding = await self.embedding_model.aembed_query(query)
            
            # 向量搜索
            search_results = await self.vector_store.search_vectors(
                query_vector=query_embedding,
                top_k=params["top_k"],
                filter_criteria=params.get("filter")
            )
            
            # 格式化结果
            results = []
            for chunk_id, score, metadata in search_results:
                if score >= params["cutoff"]:
                    results.append(RetrievalResult(
                        content=metadata.get("content", ""),
                        metadata=metadata,
                        score=score,
                        chunk_id=chunk_id,
                        source_id=metadata.get("source_id")
                    ))
            
            logger.info(f"向量检索完成，找到 {len(results)} 个相关结果")
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []
    
    async def _hybrid_retrieve(self, query: str, params: Dict[str, Any]) -> List[RetrievalResult]:
        """混合检索：结合向量检索和关键词检索"""
        try:
            # 并行执行向量检索和关键词检索
            vector_task = self._vector_retrieve(query, params)
            keyword_task = self._keyword_retrieve(query, params)
            
            vector_results, keyword_results = await asyncio.gather(
                vector_task, keyword_task, return_exceptions=True
            )
            
            # 处理异常
            if isinstance(vector_results, Exception):
                logger.warning(f"向量检索失败: {vector_results}")
                vector_results = []
            
            if isinstance(keyword_results, Exception):
                logger.warning(f"关键词检索失败: {keyword_results}")
                keyword_results = []
            
            # 合并和重排序结果
            combined_results = self._merge_and_rerank(
                vector_results, keyword_results, query, params
            )
            
            logger.info(f"混合检索完成，合并后找到 {len(combined_results)} 个结果")
            return combined_results
            
        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            return []
    
    async def _semantic_retrieve(self, query: str, params: Dict[str, Any]) -> List[RetrievalResult]:
        """语义检索：使用Agno的高级语义理解"""
        try:
            # 使用Agno的知识库检索能力
            search_results = await self.knowledge_base.search(
                query=query,
                top_k=params["top_k"],
                similarity_threshold=params["cutoff"],
                search_type="semantic"
            )
            
            # 格式化结果
            results = []
            for result in search_results:
                results.append(RetrievalResult(
                    content=result.get("content", ""),
                    metadata=result.get("metadata", {}),
                    score=result.get("score", 0.0),
                    chunk_id=result.get("chunk_id", ""),
                    source_id=result.get("source_id")
                ))
            
            logger.info(f"语义检索完成，找到 {len(results)} 个相关结果")
            return results
            
        except Exception as e:
            logger.error(f"语义检索失败: {str(e)}")
            return []
    
    async def _keyword_retrieve(self, query: str, params: Dict[str, Any]) -> List[RetrievalResult]:
        """关键词检索"""
        try:
            # 简化的关键词检索实现
            # 在实际应用中，可以使用Elasticsearch或其他全文搜索引擎
            search_results = await self.knowledge_base.search(
                query=query,
                top_k=params["top_k"],
                search_type="keyword"
            )
            
            # 格式化结果
            results = []
            for result in search_results:
                results.append(RetrievalResult(
                    content=result.get("content", ""),
                    metadata=result.get("metadata", {}),
                    score=result.get("score", 0.0),
                    chunk_id=result.get("chunk_id", ""),
                    source_id=result.get("source_id")
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"关键词检索失败: {str(e)}")
            return []
    
    def _merge_and_rerank(
        self, 
        vector_results: List[RetrievalResult], 
        keyword_results: List[RetrievalResult], 
        query: str, 
        params: Dict[str, Any]
    ) -> List[RetrievalResult]:
        """合并并重排序检索结果"""
        try:
            # 使用字典去重，保留最高分数
            merged_results = {}
            
            # 添加向量检索结果（权重0.7）
            for result in vector_results:
                key = result.chunk_id
                weighted_score = result.score * 0.7
                
                if key not in merged_results or weighted_score > merged_results[key].score:
                    merged_results[key] = RetrievalResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=weighted_score,
                        chunk_id=result.chunk_id,
                        source_id=result.source_id
                    )
            
            # 添加关键词检索结果（权重0.3）
            for result in keyword_results:
                key = result.chunk_id
                weighted_score = result.score * 0.3
                
                if key in merged_results:
                    # 合并分数
                    merged_results[key].score += weighted_score
                else:
                    merged_results[key] = RetrievalResult(
                        content=result.content,
                        metadata=result.metadata,
                        score=weighted_score,
                        chunk_id=result.chunk_id,
                        source_id=result.source_id
                    )
            
            # 按分数排序
            sorted_results = sorted(
                merged_results.values(),
                key=lambda x: x.score,
                reverse=True
            )
            
            # 应用cutoff和top_k限制
            filtered_results = [
                result for result in sorted_results
                if result.score >= params["cutoff"]
            ]
            
            return filtered_results[:params["top_k"]]
            
        except Exception as e:
            logger.error(f"合并重排序失败: {str(e)}")
            return vector_results[:params["top_k"]]

class MultiModalRetriever(AgnoRetriever):
    """多模态检索器，支持文本、图像等多种模态的检索"""
    
    def __init__(self, knowledge_base: AgnoKnowledgeBase, **kwargs):
        super().__init__(knowledge_base, **kwargs)
        self.multimodal_enabled = True
    
    async def retrieve_multimodal(
        self, 
        query: Union[str, Dict[str, Any]], 
        modality: str = "text",
        **kwargs
    ) -> List[RetrievalResult]:
        """
        多模态检索
        
        参数:
            query: 查询内容（文本、图像路径等）
            modality: 模态类型 ('text', 'image', 'audio')
            **kwargs: 其他参数
            
        返回:
            检索结果列表
        """
        try:
            if modality == "text":
                return await self.retrieve(query, **kwargs)
            elif modality == "image":
                return await self._retrieve_by_image(query, **kwargs)
            elif modality == "audio":
                return await self._retrieve_by_audio(query, **kwargs)
            else:
                raise ValueError(f"不支持的模态类型: {modality}")
                
        except Exception as e:
            logger.error(f"多模态检索失败: {str(e)}")
            return []
    
    async def _retrieve_by_image(self, image_query: Dict[str, Any], **kwargs) -> List[RetrievalResult]:
        """基于图像的检索"""
        # 占位符实现，实际需要图像编码器
        logger.warning("图像检索功能待实现")
        return []
    
    async def _retrieve_by_audio(self, audio_query: Dict[str, Any], **kwargs) -> List[RetrievalResult]:
        """基于音频的检索"""
        # 占位符实现，实际需要音频编码器
        logger.warning("音频检索功能待实现")
        return []

def get_query_engine(
    index: AgnoKnowledgeBase,
    similarity_top_k: int = 5,
    similarity_cutoff: float = 0.7,
    retrieval_strategy: str = "vector",
    response_mode: str = "compact",
    **kwargs
) -> "AgnoQueryEngine":
    """
    创建Agno查询引擎，对应LlamaIndex的get_query_engine
    
    参数:
        index: Agno知识库实例
        similarity_top_k: 检索数量
        similarity_cutoff: 相似度阈值
        retrieval_strategy: 检索策略
        response_mode: 响应模式
        **kwargs: 其他参数
        
    返回:
        Agno查询引擎实例
    """
    from app.frameworks.agno.query_engine import AgnoQueryEngine
    
    # 创建检索器
    retriever = AgnoRetriever(
        knowledge_base=index,
        similarity_top_k=similarity_top_k,
        similarity_cutoff=similarity_cutoff,
        retrieval_strategy=retrieval_strategy,
        **kwargs
    )
    
    # 创建查询引擎
    query_engine = AgnoQueryEngine(
        retriever=retriever,
        response_mode=response_mode,
        **kwargs
    )
    
    return query_engine

def create_retriever(
    knowledge_base: AgnoKnowledgeBase,
    retriever_type: str = "vector",
    **kwargs
) -> AgnoRetriever:
    """
    创建检索器的工厂函数
    
    参数:
        knowledge_base: 知识库实例
        retriever_type: 检索器类型 ('vector', 'multimodal')
        **kwargs: 其他参数
        
    返回:
        检索器实例
    """
    if retriever_type == "multimodal":
        return MultiModalRetriever(knowledge_base, **kwargs)
    else:
        return AgnoRetriever(knowledge_base, **kwargs)

# 保持与LlamaIndex接口兼容的别名
get_llamaindex_retriever = create_retriever
create_llamaindex_query_engine = get_query_engine 