"""
混合检索服务模块: 提供统一的ES和Milvus混合检索接口
实现高精度的向量检索和全文检索能力
支持基于知识库的分区和路由
可根据环境自动适配最佳检索策略
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import uuid
from datetime import datetime
import json
import time
from sqlalchemy.orm import Session

# 导入核心业务逻辑层
from core.knowledge import RetrievalManager, VectorManager

# 导入原有工具（保留兼容性）
from app.utils.elasticsearch_manager import get_elasticsearch_manager
from app.utils.milvus_manager import get_milvus_manager
from app.utils.storage_detector import StorageDetector
from app.utils.embedding_utils import get_embedding
from app.config import settings

logger = logging.getLogger(__name__)

class SearchConfig:
    """搜索配置类，用于统一配置搜索参数"""
    
    def __init__(
        self,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        knowledge_base_ids: Optional[List[str]] = None,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        title_weight: float = 3.0,
        content_weight: float = 2.0,
        size: int = 10,
        search_engine: str = "hybrid",  # "es", "milvus", or "hybrid"
        hybrid_method: str = "weighted_sum",  # "weighted_sum", "rank_fusion", "cascade"
        es_filter: Optional[Dict[str, Any]] = None,
        milvus_filter: Optional[str] = None,
        threshold: float = 0.7
    ):
        """
        初始化搜索配置
        
        参数:
            query_text: 查询文本
            query_vector: 查询向量
            knowledge_base_ids: 知识库ID列表
            vector_weight: 向量搜索权重（0.0-1.0）
            text_weight: 文本搜索权重（0.0-1.0）
            title_weight: 标题字段权重
            content_weight: 内容字段权重
            size: 返回结果数量
            search_engine: 搜索引擎类型
            hybrid_method: 混合搜索方法
            es_filter: ES过滤条件
            milvus_filter: Milvus过滤表达式
            threshold: 相似度阈值
        """
        self.query_text = query_text
        self.query_vector = query_vector
        self.knowledge_base_ids = knowledge_base_ids or []
        self.vector_weight = vector_weight
        self.text_weight = text_weight
        self.title_weight = title_weight
        self.content_weight = content_weight
        self.size = size
        self.search_engine = search_engine
        self.hybrid_method = hybrid_method
        self.es_filter = es_filter
        self.milvus_filter = milvus_filter
        self.threshold = threshold
        
        # 验证参数
        self._validate()
    
    def _validate(self):
        """验证参数有效性"""
        # 至少需要一种查询
        if not self.query_text and not self.query_vector:
            logger.warning("查询文本和查询向量至少需要提供一种")
        
        # 验证权重
        if self.vector_weight < 0 or self.vector_weight > 1:
            logger.warning(f"向量搜索权重超出范围: {self.vector_weight}，已调整为0.7")
            self.vector_weight = 0.7
        
        if self.text_weight < 0 or self.text_weight > 1:
            logger.warning(f"文本搜索权重超出范围: {self.text_weight}，已调整为0.3")
            self.text_weight = 0.3
        
        # 验证搜索引擎
        if self.search_engine not in ["es", "milvus", "hybrid", "semantic", "keyword"]:
            logger.warning(f"无效的搜索引擎类型: {self.search_engine}，已调整为hybrid")
            self.search_engine = "hybrid"
        
        # 验证混合方法
        if self.hybrid_method not in ["weighted_sum", "rank_fusion", "cascade"]:
            logger.warning(f"无效的混合搜索方法: {self.hybrid_method}，已调整为weighted_sum")
            self.hybrid_method = "weighted_sum"

class HybridSearchService:
    """混合搜索服务，整合ES和Milvus搜索能力"""
    
    def __init__(self, db: Session):
        """初始化混合搜索服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        
        # 核心业务逻辑层
        self.retrieval_manager = RetrievalManager(db)
        self.vector_manager = VectorManager(db)
        
        # 检测可用的存储引擎（保留兼容性）
        try:
            self.storage_info = StorageDetector.get_vector_store_info()
            self.strategy = self.storage_info['strategy']
            
            # 根据可用存储引擎初始化管理器
            self.es_manager = get_elasticsearch_manager() if self.storage_info['elasticsearch']['available'] else None
            self.milvus_manager = get_milvus_manager() if self.storage_info['milvus']['available'] else None
        except Exception as e:
            logger.warning(f"兼容性工具初始化失败: {str(e)}")
            self.storage_info = None
            self.strategy = "core"
            self.es_manager = None
            self.milvus_manager = None
        
        logger.info(f"HybridSearchService初始化完成，使用策略: {self.strategy}")
    
    async def search(self, config: SearchConfig) -> Dict[str, Any]:
        """
        执行混合搜索
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果和元数据
        """
        try:
            start_time = time.time()
            
            # 优先使用核心业务逻辑层
            if config.search_engine in ["semantic", "keyword", "hybrid"] or not self.es_manager:
                results = await self._search_with_core(config)
                engine_used = "core_layer"
            else:
                # 使用传统搜索引擎（兼容性）
                results = await self._search_legacy(config)
                engine_used = "legacy"
                
            search_time = (time.time() - start_time) * 1000  # 毫秒
            
            return {
                "results": results,
                "total": len(results),
                "query": config.query_text,
                "strategy_used": config.hybrid_method,
                "engine_used": engine_used,
                "search_time_ms": search_time,
                "knowledge_base_ids": config.knowledge_base_ids
            }
        except Exception as e:
            logger.error(f"执行搜索时出错: {str(e)}")
            return {
                "results": [],
                "total": 0,
                "query": config.query_text if hasattr(config, 'query_text') else "",
                "strategy_used": "error",
                "engine_used": "error",
                "search_time_ms": 0,
                "knowledge_base_ids": config.knowledge_base_ids if hasattr(config, 'knowledge_base_ids') else [],
                "error": str(e)
            }
    
    async def _search_with_core(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        使用核心业务逻辑层执行搜索
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            if not config.query_text:
                logger.warning("查询文本为空")
                return []
            
            # 如果指定了多个知识库，需要分别搜索并合并结果
            all_results = []
            
            if config.knowledge_base_ids:
                for kb_id in config.knowledge_base_ids:
                    kb_results = await self._search_single_kb(config, kb_id)
                    all_results.extend(kb_results)
            else:
                # 如果没有指定知识库，使用空字符串（表示全局搜索）
                all_results = await self._search_single_kb(config, "")
            
            # 按分数排序并限制结果数量
            all_results.sort(key=lambda x: x.get("final_score", x.get("similarity", x.get("score", 0))), reverse=True)
            return all_results[:config.size]
            
        except Exception as e:
            logger.error(f"核心层搜索失败: {str(e)}")
            return []
    
    async def _search_single_kb(self, config: SearchConfig, kb_id: str) -> List[Dict[str, Any]]:
        """
        在单个知识库中搜索
        
        参数:
            config: 搜索配置
            kb_id: 知识库ID
            
        返回:
            搜索结果列表
        """
        try:
            # 构建过滤条件
            filters = {}
            if config.es_filter:
                filters.update(config.es_filter)
            
            # 根据搜索引擎类型调用相应方法
            if config.search_engine == "semantic":
                result = await self.retrieval_manager.semantic_search(
                    query=config.query_text,
                    kb_id=kb_id,
                    top_k=config.size,
                    threshold=config.threshold,
                    filters=filters
                )
            elif config.search_engine == "keyword":
                result = await self.retrieval_manager.keyword_search(
                    query=config.query_text,
                    kb_id=kb_id,
                    top_k=config.size,
                    filters=filters
                )
            else:  # hybrid
                result = await self.retrieval_manager.hybrid_search(
                    query=config.query_text,
                    kb_id=kb_id,
                    top_k=config.size,
                    semantic_weight=config.vector_weight,
                    keyword_weight=config.text_weight,
                    threshold=config.threshold,
                    filters=filters
                )
            
            if not result["success"]:
                logger.error(f"搜索失败: {result['error']}")
                return []
            
            return result["data"]["results"]
            
        except Exception as e:
            logger.error(f"单知识库搜索失败: {str(e)}")
            return []
    
    async def _search_legacy(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        使用传统搜索引擎执行搜索（兼容性方法）
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            # 如果没有明确指定搜索引擎，则使用自动检测的策略
            if config.search_engine == "auto":
                config.search_engine = self.strategy
            
            # 如果需要向量搜索但没有提供查询向量，则生成向量
            if (config.search_engine in ["milvus", "hybrid"] and 
                config.query_text and not config.query_vector):
                config.query_vector = await get_embedding(config.query_text)
            
            # 根据配置的引擎执行搜索
            if config.search_engine == "es" and self.es_manager:
                results = await self._search_es(config)
            elif config.search_engine == "milvus" and self.milvus_manager:
                results = await self._search_milvus(config)
            elif config.search_engine == "hybrid" and self.es_manager and self.milvus_manager:
                results = await self._search_hybrid_legacy(config)
            elif self.es_manager:
                # 退化到ES搜索
                results = await self._search_es(config)
            elif self.milvus_manager:
                # 退化到Milvus搜索
                results = await self._search_milvus(config)
            else:
                # 无可用搜索引擎，使用核心层
                return await self._search_with_core(config)
                
            return results
            
        except Exception as e:
            logger.error(f"传统搜索失败: {str(e)}")
            # 退化到核心层搜索
            return await self._search_with_core(config)
    
    async def _search_es(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        使用ES执行搜索（兼容性方法）
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            if not self.es_manager or not config.query_text:
                return []
            
            # 构建ES查询
            query_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": config.query_text,
                                    "fields": [
                                        f"title^{config.title_weight}",
                                        f"content^{config.content_weight}"
                                    ],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "size": config.size
            }
            
            # 添加知识库过滤
            if config.knowledge_base_ids:
                query_body["query"]["bool"]["filter"] = [
                    {"terms": {"knowledge_base_id": config.knowledge_base_ids}}
                ]
            
            # 添加自定义过滤条件
            if config.es_filter:
                if "filter" not in query_body["query"]["bool"]:
                    query_body["query"]["bool"]["filter"] = []
                query_body["query"]["bool"]["filter"].append(config.es_filter)
            
            # 执行搜索
            response = await self.es_manager.search(
                index="documents",
                body=query_body
            )
            
            # 转换结果格式
            results = []
            for hit in response.get("hits", {}).get("hits", []):
                result = {
                    "id": hit["_id"],
                    "content": hit["_source"].get("content", ""),
                    "score": hit["_score"],
                    "metadata": hit["_source"],
                    "search_type": "keyword"
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"ES搜索失败: {str(e)}")
            return []
    
    async def _search_milvus(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        使用Milvus执行搜索（兼容性方法）
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            if not self.milvus_manager or not config.query_vector:
                return []
            
            # 构建Milvus搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 构建过滤表达式
            filter_expr = None
            if config.knowledge_base_ids:
                kb_filter = " or ".join([f'knowledge_base_id == "{kb_id}"' for kb_id in config.knowledge_base_ids])
                filter_expr = kb_filter
            
            if config.milvus_filter:
                if filter_expr:
                    filter_expr = f"({filter_expr}) and ({config.milvus_filter})"
                else:
                    filter_expr = config.milvus_filter
            
            # 执行搜索
            results = await self.milvus_manager.search(
                collection_name="document_chunks",
                query_vectors=[config.query_vector],
                search_params=search_params,
                limit=config.size,
                expr=filter_expr,
                output_fields=["content", "metadata", "knowledge_base_id"]
            )
            
            # 转换结果格式
            formatted_results = []
            for result in results[0]:  # Milvus返回的是嵌套列表
                formatted_result = {
                    "id": str(result.id),
                    "content": result.entity.get("content", ""),
                    "similarity": 1 - result.distance,  # 转换为相似度
                    "metadata": result.entity.get("metadata", {}),
                    "search_type": "semantic"
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Milvus搜索失败: {str(e)}")
            return []
    
    async def _search_hybrid_legacy(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        执行传统混合搜索（兼容性方法）
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            # 并行执行ES和Milvus搜索
            es_results = await self._search_es(config)
            milvus_results = await self._search_milvus(config)
            
            # 根据混合方法合并结果
            if config.hybrid_method == "weighted_sum":
                return self._merge_weighted_sum(es_results, milvus_results, config)
            elif config.hybrid_method == "rank_fusion":
                return self._merge_rank_fusion(es_results, milvus_results, config)
            elif config.hybrid_method == "cascade":
                return self._merge_cascade(es_results, milvus_results, config)
            else:
                return self._merge_weighted_sum(es_results, milvus_results, config)
                
        except Exception as e:
            logger.error(f"传统混合搜索失败: {str(e)}")
            return []
    
    def _merge_weighted_sum(
        self, 
        es_results: List[Dict[str, Any]], 
        milvus_results: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """
        使用加权求和方法合并搜索结果
        
        参数:
            es_results: ES搜索结果
            milvus_results: Milvus搜索结果
            config: 搜索配置
            
        返回:
            合并后的搜索结果
        """
        try:
            # 创建结果字典，以文档ID为键
            merged_results = {}
            
            # 处理ES结果
            for result in es_results:
                doc_id = result["id"]
                merged_results[doc_id] = {
                    **result,
                    "es_score": result.get("score", 0),
                    "milvus_score": 0,
                    "final_score": result.get("score", 0) * config.text_weight
                }
            
            # 处理Milvus结果
            for result in milvus_results:
                doc_id = result["id"]
                if doc_id in merged_results:
                    # 更新现有结果
                    merged_results[doc_id]["milvus_score"] = result.get("similarity", 0)
                    merged_results[doc_id]["final_score"] = (
                        merged_results[doc_id]["es_score"] * config.text_weight +
                        result.get("similarity", 0) * config.vector_weight
                    )
                else:
                    # 添加新结果
                    merged_results[doc_id] = {
                        **result,
                        "es_score": 0,
                        "milvus_score": result.get("similarity", 0),
                        "final_score": result.get("similarity", 0) * config.vector_weight
                    }
            
            # 按最终分数排序
            sorted_results = sorted(
                merged_results.values(),
                key=lambda x: x["final_score"],
                reverse=True
            )
            
            return sorted_results[:config.size]
            
        except Exception as e:
            logger.error(f"加权求和合并失败: {str(e)}")
            return []
    
    def _merge_rank_fusion(
        self, 
        es_results: List[Dict[str, Any]], 
        milvus_results: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """
        使用排名融合方法合并搜索结果
        
        参数:
            es_results: ES搜索结果
            milvus_results: Milvus搜索结果
            config: 搜索配置
            
        返回:
            合并后的搜索结果
        """
        try:
            # RRF (Reciprocal Rank Fusion) 算法
            k = 60  # RRF参数
            merged_scores = {}
            
            # 处理ES结果
            for rank, result in enumerate(es_results):
                doc_id = result["id"]
                rrf_score = 1 / (k + rank + 1)
                merged_scores[doc_id] = {
                    "result": result,
                    "rrf_score": rrf_score * config.text_weight
                }
            
            # 处理Milvus结果
            for rank, result in enumerate(milvus_results):
                doc_id = result["id"]
                rrf_score = 1 / (k + rank + 1)
                if doc_id in merged_scores:
                    merged_scores[doc_id]["rrf_score"] += rrf_score * config.vector_weight
                else:
                    merged_scores[doc_id] = {
                        "result": result,
                        "rrf_score": rrf_score * config.vector_weight
                    }
            
            # 按RRF分数排序
            sorted_results = sorted(
                merged_scores.items(),
                key=lambda x: x[1]["rrf_score"],
                reverse=True
            )
            
            # 转换为最终格式
            final_results = []
            for doc_id, score_info in sorted_results[:config.size]:
                result = score_info["result"]
                result["final_score"] = score_info["rrf_score"]
                final_results.append(result)
            
            return final_results
            
        except Exception as e:
            logger.error(f"排名融合合并失败: {str(e)}")
            return []
    
    def _merge_cascade(
        self, 
        es_results: List[Dict[str, Any]], 
        milvus_results: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """
        使用级联方法合并搜索结果
        
        参数:
            es_results: ES搜索结果
            milvus_results: Milvus搜索结果
            config: 搜索配置
            
        返回:
            合并后的搜索结果
        """
        try:
            # 级联策略：先用ES筛选，再用Milvus重排
            if not es_results:
                return milvus_results[:config.size]
            
            if not milvus_results:
                return es_results[:config.size]
            
            # 创建Milvus结果的映射
            milvus_map = {result["id"]: result for result in milvus_results}
            
            # 对ES结果进行重排
            reranked_results = []
            for es_result in es_results:
                doc_id = es_result["id"]
                if doc_id in milvus_map:
                    # 结合ES和Milvus分数
                    milvus_result = milvus_map[doc_id]
                    combined_result = {
                        **es_result,
                        "milvus_score": milvus_result.get("similarity", 0),
                        "final_score": (
                            es_result.get("score", 0) * config.text_weight +
                            milvus_result.get("similarity", 0) * config.vector_weight
                        )
                    }
                else:
                    # 只有ES分数
                    combined_result = {
                        **es_result,
                        "milvus_score": 0,
                        "final_score": es_result.get("score", 0) * config.text_weight
                    }
                
                reranked_results.append(combined_result)
            
            # 按最终分数排序
            reranked_results.sort(key=lambda x: x["final_score"], reverse=True)
            
            return reranked_results[:config.size]
            
        except Exception as e:
            logger.error(f"级联合并失败: {str(e)}")
            return []
    
    # ========== 便捷搜索方法 ==========
    
    async def semantic_search(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        语义搜索便捷方法
        
        参数:
            query: 查询文本
            knowledge_base_ids: 知识库ID列表
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        返回:
            搜索结果
        """
        config = SearchConfig(
            query_text=query,
            knowledge_base_ids=knowledge_base_ids,
            size=top_k,
            search_engine="semantic",
            threshold=threshold
        )
        return await self.search(config)
    
    async def keyword_search(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        关键词搜索便捷方法
        
        参数:
            query: 查询文本
            knowledge_base_ids: 知识库ID列表
            top_k: 返回结果数量
            
        返回:
            搜索结果
        """
        config = SearchConfig(
            query_text=query,
            knowledge_base_ids=knowledge_base_ids,
            size=top_k,
            search_engine="keyword"
        )
        return await self.search(config)
    
    async def hybrid_search(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        混合搜索便捷方法
        
        参数:
            query: 查询文本
            knowledge_base_ids: 知识库ID列表
            top_k: 返回结果数量
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
            threshold: 相似度阈值
            
        返回:
            搜索结果
        """
        config = SearchConfig(
            query_text=query,
            knowledge_base_ids=knowledge_base_ids,
            vector_weight=semantic_weight,
            text_weight=keyword_weight,
            size=top_k,
            search_engine="hybrid",
            threshold=threshold
        )
        return await self.search(config)

# 全局单例实例
_hybrid_search_service = None

def get_hybrid_search_service() -> HybridSearchService:
    """获取HybridSearchService的单例实例"""
    global _hybrid_search_service
    if _hybrid_search_service is None:
        _hybrid_search_service = HybridSearchService()
    return _hybrid_search_service
