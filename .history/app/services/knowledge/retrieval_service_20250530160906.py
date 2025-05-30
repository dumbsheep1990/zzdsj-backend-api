from typing import List, Dict, Any, Optional, Union
import logging
import time
import asyncio
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# 使用核心层而不是直接访问服务层
from app.core.knowledge.retrieval_manager import RetrievalManager
from app.core.knowledge.vector_manager import VectorManager
from app.utils.storage_detector import StorageDetector

logger = logging.getLogger(__name__)

class SourceWeight(BaseModel):
    """数据源权重配置"""
    source_id: str
    weight: float = 1.0
    max_results: int = 10

class RerankConfig(BaseModel):
    """重排序配置"""
    enabled: bool = False
    model_name: Optional[str] = None
    model_type: str = "cross_encoder"
    top_n: int = 50
    params: Dict[str, Any] = Field(default_factory=dict)

class FusionConfig(BaseModel):
    """融合配置"""
    strategy: str = "reciprocal_rank_fusion"
    rrf_k: float = 60.0
    normalize: bool = True

class AdvancedRetrievalConfig(BaseModel):
    """高级检索配置"""
    sources: List[SourceWeight] = Field(default_factory=list)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    rerank: RerankConfig = Field(default_factory=RerankConfig)
    max_results: int = 10
    query_preprocessing: bool = True

class AdvancedRetrievalService:
    """高级检索服务，在混合检索基础上添加多源融合和重排序功能"""
    
    def __init__(self, retrieval_manager: Optional[RetrievalManager] = None, 
                 vector_manager: Optional[VectorManager] = None,
                 db: Optional[Session] = None):
        """初始化高级检索服务
        
        Args:
            retrieval_manager: 检索管理器，如果为None则创建新实例
            vector_manager: 向量管理器，如果为None则创建新实例
            db: 数据库会话，用于创建管理器实例
        """
        # 使用核心层管理器
        if retrieval_manager is not None:
            self.retrieval_manager = retrieval_manager
        elif db is not None:
            self.retrieval_manager = RetrievalManager(db)
        else:
            raise ValueError("必须提供 retrieval_manager 或 db 参数")
            
        if vector_manager is not None:
            self.vector_manager = vector_manager
        elif db is not None:
            self.vector_manager = VectorManager(db)
        else:
            raise ValueError("必须提供 vector_manager 或 db 参数")
        
        # 存储检测（保持兼容性）
        try:
            self.storage_info = StorageDetector.get_vector_store_info()
        except Exception as e:
            logger.warning(f"存储检测失败: {str(e)}")
            self.storage_info = None
        
        logger.info("AdvancedRetrievalService initialized with core layer managers")
        
    async def retrieve(self, query: str, config: Optional[AdvancedRetrievalConfig] = None) -> Dict[str, Any]:
        """执行高级检索"""
        start_time = time.time()
        
        try:
            # 使用默认配置（如果未提供）
            if config is None:
                config = self._get_default_config()
            
            # 查询预处理
            processed_query, query_vector = await self._preprocess_query(query, config.query_preprocessing)
            
            # 1. 从多个数据源检索结果
            source_results = await self._retrieve_from_sources(processed_query, query_vector, config.sources)
            
            # 2. 融合结果
            fused_results = self._fuse_results(source_results, config.fusion)
            
            # 3. 可选的重排序
            if config.rerank.enabled and fused_results:
                reranked_results = await self._rerank_results(processed_query, fused_results, config.rerank)
                final_results = reranked_results[:config.max_results]
            else:
                final_results = fused_results[:config.max_results]
            
            # 4. 构建响应
            elapsed_time = (time.time() - start_time) * 1000  # 毫秒
            
            return {
                "query": query,
                "results": final_results,
                "total": len(final_results),
                "source_distribution": {
                    source_id: len(results) for source_id, results in source_results.items()
                },
                "fusion_strategy": config.fusion.strategy,
                "reranking_applied": config.rerank.enabled,
                "search_time_ms": elapsed_time
            }
            
        except Exception as e:
            logger.error(f"高级检索失败: {str(e)}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "total": 0,
                "search_time_ms": (time.time() - start_time) * 1000
            }
    
    async def _preprocess_query(self, query: str, enable_preprocessing: bool) -> tuple:
        """查询预处理"""
        if not enable_preprocessing:
            return query, None
        
        try:
            # 使用核心层的向量管理器生成查询向量
            query_vector = await self.vector_manager.generate_embedding(query)
            
            # 这里可以添加更多预处理逻辑，如查询扩展、同义词替换等
            
            return query, query_vector
        except Exception as e:
            logger.warning(f"查询预处理失败: {str(e)}, 继续使用原始查询")
            return query, None
    
    async def _retrieve_from_sources(
        self, query: str, query_vector: Optional[List[float]], sources: List[SourceWeight]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """从多个数据源检索结果"""
        # 如果没有指定数据源，使用默认的知识库
        if not sources:
            sources = [SourceWeight(source_id="default", weight=1.0, max_results=20)]
        
        # 并行从所有数据源检索
        tasks = []
        for source in sources:
            task = self._retrieve_from_source(query, query_vector, source)
            tasks.append(task)
        
        # 等待所有检索任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        source_results = {}
        for i, result in enumerate(results):
            source_id = sources[i].source_id
            
            if isinstance(result, Exception):
                logger.error(f"从数据源 {source_id} 检索时出错: {str(result)}")
                source_results[source_id] = []
            else:
                # 添加数据源权重信息
                for item in result:
                    item["source_id"] = source_id
                    item["source_weight"] = sources[i].weight
                
                source_results[source_id] = result
        
        return source_results
    
    async def _retrieve_from_source(
        self, query: str, query_vector: Optional[List[float]], source: SourceWeight
    ) -> List[Dict[str, Any]]:
        """从单个数据源检索"""
        try:
            # 使用核心层的检索管理器
            knowledge_base_ids = [source.source_id] if source.source_id != "default" else []
            
            # 执行混合检索
            response = await self.retrieval_manager.hybrid_search(
                query=query,
                query_vector=query_vector,
                knowledge_base_ids=knowledge_base_ids,
                limit=source.max_results,
                semantic_weight=0.7,  # 默认语义权重
                keyword_weight=0.3,   # 默认关键词权重
                min_score=0.0
            )
            
            # 提取结果
            return response.get("results", [])
            
        except Exception as e:
            logger.error(f"从数据源 {source.source_id} 检索失败: {str(e)}")
            return []
    
    def _fuse_results(
        self, source_results: Dict[str, List[Dict[str, Any]]], fusion_config: FusionConfig
    ) -> List[Dict[str, Any]]:
        """融合多个数据源的结果"""
        # 简单实现，稍后我们会添加更复杂的融合策略
        if fusion_config.strategy == "reciprocal_rank_fusion":
            return self._reciprocal_rank_fusion(source_results, fusion_config.rrf_k, fusion_config.normalize)
        else:
            # 默认使用简单合并
            return self._simple_append_fusion(source_results)
    
    def _reciprocal_rank_fusion(
        self, source_results: Dict[str, List[Dict[str, Any]]], k: float = 60.0, normalize: bool = True
    ) -> List[Dict[str, Any]]:
        """使用倒数排名融合（RRF）算法融合结果"""
        # 这是RRF的简单实现，后续会扩展
        from collections import defaultdict
        
        # 初始化
        doc_scores = defaultdict(float)
        doc_data = {}
        
        # 计算RRF分数
        for source_id, results in source_results.items():
            # 应用源权重
            source_weight = 1.0
            if results and len(results) > 0:
                source_weight = results[0].get("source_weight", 1.0)
            
            for rank, doc in enumerate(results):
                doc_id = self._get_doc_id(doc)
                
                # RRF公式: 1 / (k + rank)
                rrf_score = 1.0 / (k + rank)
                doc_scores[doc_id] += rrf_score * source_weight
                
                # 保存文档数据
                if doc_id not in doc_data:
                    doc_data[doc_id] = doc
        
        # 标准化分数
        if normalize and doc_scores:
            max_score = max(doc_scores.values())
            min_score = min(doc_scores.values())
            score_range = max_score - min_score
            
            if score_range > 0:
                for doc_id in doc_scores:
                    doc_scores[doc_id] = (doc_scores[doc_id] - min_score) / score_range
        
        # 排序并返回结果
        sorted_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
        
        fused_results = []
        for doc_id in sorted_ids:
            doc = doc_data[doc_id].copy()
            doc["score"] = doc_scores[doc_id]
            doc["fusion_method"] = "rrf"
            fused_results.append(doc)
        
        return fused_results
    
    def _simple_append_fusion(self, source_results: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """简单合并多个数据源的结果（避免重复）"""
        seen_ids = set()
        fused_results = []
        
        for source_id, results in source_results.items():
            for doc in results:
                doc_id = self._get_doc_id(doc)
                
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    fused_results.append(doc)
        
        # 按分数排序
        fused_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return fused_results
    
    def _get_doc_id(self, doc: Dict[str, Any]) -> str:
        """获取文档的唯一标识符"""
        # 首选内部ID
        if "id" in doc and doc["id"]:
            return doc["id"]
        
        # 尝试组合ID
        id_parts = []
        if "document_id" in doc:
            id_parts.append(str(doc["document_id"]))
        
        if "source_id" in doc:
            id_parts.append(str(doc["source_id"]))
        
        if id_parts:
            return ":".join(id_parts)
        
        # 最后使用内容的哈希
        import hashlib
        content = doc.get("content", "") or doc.get("title", "")
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _rerank_results(
        self, query: str, results: List[Dict[str, Any]], rerank_config: RerankConfig
    ) -> List[Dict[str, Any]]:
        """使用重排序模型重排结果"""
        if not results or len(results) <= 1:
            return results
        
        try:
            from app.services.rerank.rerank_adapter import UniversalRerankAdapter
            
            # 限制重排序的文档数量
            top_n = min(rerank_config.top_n, len(results))
            
            # 提取文档内容
            documents = []
            for result in results[:top_n]:
                documents.append(result.get("content", ""))
            
            # 创建重排序适配器
            adapter = UniversalRerankAdapter(model_name=rerank_config.model_name)
            
            # 执行重排序
            scores = await adapter.rerank(query, documents)
            
            # 更新前N个结果的分数
            for i in range(top_n):
                results[i]["original_score"] = results[i].get("score", 0.0)
                results[i]["score"] = scores[i]
                results[i]["reranked"] = True
            
            # 重新排序所有结果
            reranked_results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return results  # 如果失败，返回原始结果
    
    def _get_default_config(self) -> AdvancedRetrievalConfig:
        """获取默认配置"""
        return AdvancedRetrievalConfig(
            sources=[SourceWeight(source_id="default", weight=1.0, max_results=20)],
            fusion=FusionConfig(strategy="reciprocal_rank_fusion", rrf_k=60.0, normalize=True),
            rerank=RerankConfig(enabled=False),
            max_results=10,
            query_preprocessing=True
        )

# 全局单例
_advanced_retrieval_service = None

def get_advanced_retrieval_service() -> AdvancedRetrievalService:
    """获取高级检索服务实例"""
    global _advanced_retrieval_service
    if _advanced_retrieval_service is None:
        _advanced_retrieval_service = AdvancedRetrievalService()
    return _advanced_retrieval_service
