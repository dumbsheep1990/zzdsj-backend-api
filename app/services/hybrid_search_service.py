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
        milvus_filter: Optional[str] = None
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
        if self.search_engine not in ["es", "milvus", "hybrid"]:
            logger.warning(f"无效的搜索引擎类型: {self.search_engine}，已调整为hybrid")
            self.search_engine = "hybrid"
        
        # 验证混合方法
        if self.hybrid_method not in ["weighted_sum", "rank_fusion", "cascade"]:
            logger.warning(f"无效的混合搜索方法: {self.hybrid_method}，已调整为weighted_sum")
            self.hybrid_method = "weighted_sum"

class HybridSearchService:
    """混合搜索服务，整合ES和Milvus搜索能力"""
    
    def __init__(self):
        """初始化混合搜索服务"""
        # 检测可用的存储引擎
        self.storage_info = StorageDetector.get_vector_store_info()
        self.strategy = self.storage_info['strategy']
        
        # 根据可用存储引擎初始化管理器
        self.es_manager = get_elasticsearch_manager() if self.storage_info['elasticsearch']['available'] else None
        self.milvus_manager = get_milvus_manager() if self.storage_info['milvus']['available'] else None
        
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
                engine_used = "elasticsearch"
            elif config.search_engine == "milvus" and self.milvus_manager:
                results = await self._search_milvus(config)
                engine_used = "milvus"
            elif config.search_engine == "hybrid" and self.es_manager and self.milvus_manager:
                results = await self._search_hybrid(config)
                engine_used = "hybrid"
            elif self.es_manager:
                # 退化到ES搜索
                results = await self._search_es(config)
                engine_used = "elasticsearch (fallback)"
            elif self.milvus_manager:
                # 退化到Milvus搜索
                results = await self._search_milvus(config)
                engine_used = "milvus (fallback)"
            else:
                # 无可用搜索引擎
                logger.error("无可用的搜索引擎")
                return {
                    "results": [],
                    "total": 0,
                    "query": config.query_text,
                    "strategy_used": "none",
                    "engine_used": "none",
                    "search_time_ms": 0,
                    "knowledge_base_ids": config.knowledge_base_ids
                }
                
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
    
    async def _search_es(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        使用ES执行搜索
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            if not self.es_manager:
                logger.warning("Elasticsearch管理器未初始化")
                return []
                
            if len(config.knowledge_base_ids) == 1:
                # 单一知识库搜索
                kb_id = config.knowledge_base_ids[0]
                return self.es_manager.search_kb(
                    kb_id=kb_id,
                    query_text=config.query_text,
                    query_vector=config.query_vector,
                    vector_weight=config.vector_weight,
                    text_weight=config.text_weight,
                    top_k=config.size
                )
            elif config.knowledge_base_ids:
                # 多知识库搜索
                return self.es_manager.search_multiple_kb(
                    kb_ids=config.knowledge_base_ids,
                    query_text=config.query_text,
                    query_vector=config.query_vector,
                    vector_weight=config.vector_weight,
                    text_weight=config.text_weight,
                    top_k=config.size
                )
            else:
                # 搜索所有可用知识库
                # 获取所有的知识库别名
                kb_aliases = self.es_manager.get_all_kb_aliases()
                kb_ids = [alias['kb_id'] for alias in kb_aliases]
                
                if not kb_ids:
                    logger.warning("没有可搜索的知识库")
                    return []
                    
                return self.es_manager.search_multiple_kb(
                    kb_ids=kb_ids,
                    query_text=config.query_text,
                    query_vector=config.query_vector,
                    vector_weight=config.vector_weight,
                    text_weight=config.text_weight,
                    top_k=config.size
                )
        except Exception as e:
            logger.error(f"ES搜索时出错: {str(e)}")
            return []
    
    async def _search_milvus(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        使用Milvus执行搜索
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            if not self.milvus_manager:
                logger.warning("Milvus管理器未初始化")
                return []
                
            if not config.query_vector:
                # 如果有文本但没有向量，则生成向量
                if config.query_text:
                    config.query_vector = await get_embedding(config.query_text)
                else:
                    logger.warning("Milvus搜索需要查询向量或查询文本")
                    return []
                
            if len(config.knowledge_base_ids) == 1:
                # 单一知识库搜索
                kb_id = config.knowledge_base_ids[0]
                return self.milvus_manager.search_vectors(
                    kb_id=kb_id,
                    query_vector=config.query_vector,
                    top_k=config.size,
                    expr=config.milvus_filter
                )
            elif config.knowledge_base_ids:
                # 多知识库搜索
                return self.milvus_manager.search_multiple_kb(
                    kb_ids=config.knowledge_base_ids,
                    query_vector=config.query_vector,
                    top_k=config.size,
                    expr=config.milvus_filter
                )
            else:
                # 搜索所有可用知识库
                # 获取所有知识库分区
                kb_partitions = self.milvus_manager.get_kb_partitions()
                kb_ids = [p.replace('kb_', '') for p in kb_partitions]
                
                if not kb_ids:
                    logger.warning("没有可搜索的知识库分区")
                    return []
                    
                return self.milvus_manager.search_multiple_kb(
                    kb_ids=kb_ids,
                    query_vector=config.query_vector,
                    top_k=config.size,
                    expr=config.milvus_filter
                )
        except Exception as e:
            logger.error(f"Milvus搜索时出错: {str(e)}")
            return []
    
    async def _search_hybrid(self, config: SearchConfig) -> List[Dict[str, Any]]:
        """
        执行ES与Milvus的混合搜索
        
        参数:
            config: 搜索配置
            
        返回:
            搜索结果列表
        """
        try:
            # 执行ES搜索
            es_results = await self._search_es(config)
            
            # 执行Milvus搜索（如果有向量）
            milvus_results = []
            if config.query_vector:
                milvus_results = await self._search_milvus(config)
            
            # 根据混合方法合并结果
            if config.hybrid_method == "weighted_sum":
                return self._merge_weighted_sum(es_results, milvus_results, config)
            elif config.hybrid_method == "rank_fusion":
                return self._merge_rank_fusion(es_results, milvus_results, config)
            elif config.hybrid_method == "cascade":
                return self._merge_cascade(es_results, milvus_results, config)
            else:
                # 默认使用加权和
                return self._merge_weighted_sum(es_results, milvus_results, config)
        except Exception as e:
            logger.error(f"混合搜索时出错: {str(e)}")
            return []
    
    def _merge_weighted_sum(
        self, 
        es_results: List[Dict[str, Any]], 
        milvus_results: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """
        使用加权和方法合并ES和Milvus结果
        
        参数:
            es_results: ES搜索结果
            milvus_results: Milvus搜索结果
            config: 搜索配置
            
        返回:
            合并后的结果列表
        """
        # 如果一种结果为空，直接返回另一种
        if not es_results:
            return milvus_results
        if not milvus_results:
            return es_results
        
        # 合并结果
        merged = {}
        
        # 处理ES结果
        for item in es_results:
            doc_id = item.get("document_id", "") or item.get("id", "")
            if not doc_id:
                continue
                
            if doc_id not in merged:
                merged[doc_id] = item.copy()
                # 使用文本权重
                merged[doc_id]["score"] = item.get("score", 0) * config.text_weight
            else:
                # 增加分数
                merged[doc_id]["score"] += item.get("score", 0) * config.text_weight
                # 保留高亮信息
                if "highlight" in item:
                    merged[doc_id]["highlight"] = item["highlight"]
        
        # 处理Milvus结果
        for item in milvus_results:
            doc_id = item.get("document_id", "") or item.get("id", "")
            if not doc_id:
                continue
                
            if doc_id not in merged:
                merged[doc_id] = item.copy()
                # 使用向量权重
                merged[doc_id]["score"] = item.get("score", 0) * config.vector_weight
                merged[doc_id]["vector_score"] = item.get("score", 0)
            else:
                # 增加分数
                merged[doc_id]["score"] += item.get("score", 0) * config.vector_weight
                merged[doc_id]["vector_score"] = item.get("score", 0)
                # 如果不存在内容字段，从Milvus结果获取
                if not merged[doc_id].get("content") and item.get("text"):
                    merged[doc_id]["content"] = item["text"]
        
        # 转换为列表并排序
        results = list(merged.values())
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 截取指定数量的结果
        return results[:config.size]
    
    def _merge_rank_fusion(
        self, 
        es_results: List[Dict[str, Any]], 
        milvus_results: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """
        使用排序融合方法合并ES和Milvus结果
        
        参数:
            es_results: ES搜索结果
            milvus_results: Milvus搜索结果
            config: 搜索配置
            
        返回:
            合并后的结果列表
        """
        # 如果一种结果为空，直接返回另一种
        if not es_results:
            return milvus_results
        if not milvus_results:
            return es_results
        
        # 合并结果
        merged = {}
        
        # 为ES结果分配排名
        for i, item in enumerate(es_results):
            doc_id = item.get("document_id", "") or item.get("id", "")
            if not doc_id:
                continue
                
            rank = i + 1  # 排名从1开始
            
            if doc_id not in merged:
                merged[doc_id] = item.copy()
                merged[doc_id]["es_rank"] = rank
                merged[doc_id]["fusion_score"] = 1.0 / rank
            else:
                merged[doc_id]["es_rank"] = rank
                merged[doc_id]["fusion_score"] = 1.0 / rank
        
        # 为Milvus结果分配排名
        for i, item in enumerate(milvus_results):
            doc_id = item.get("document_id", "") or item.get("id", "")
            if not doc_id:
                continue
                
            rank = i + 1  # 排名从1开始
            
            if doc_id not in merged:
                merged[doc_id] = item.copy()
                merged[doc_id]["milvus_rank"] = rank
                merged[doc_id]["fusion_score"] = 1.0 / rank
            else:
                merged[doc_id]["milvus_rank"] = rank
                # 如果同时存在ES和Milvus排名，取加权和
                if "es_rank" in merged[doc_id]:
                    es_score = 1.0 / merged[doc_id]["es_rank"]
                    milvus_score = 1.0 / rank
                    merged[doc_id]["fusion_score"] = (
                        es_score * config.text_weight +
                        milvus_score * config.vector_weight
                    )
                else:
                    merged[doc_id]["fusion_score"] = 1.0 / rank
                
                # 如果不存在内容字段，从Milvus结果获取
                if not merged[doc_id].get("content") and item.get("text"):
                    merged[doc_id]["content"] = item["text"]
        
        # 转换为列表并按融合分数排序
        results = list(merged.values())
        results.sort(key=lambda x: x.get("fusion_score", 0), reverse=True)
        
        # 更新最终分数
        for item in results:
            item["score"] = item.get("fusion_score", 0)
        
        # 截取指定数量的结果
        return results[:config.size]
    
    def _merge_cascade(
        self, 
        es_results: List[Dict[str, Any]], 
        milvus_results: List[Dict[str, Any]], 
        config: SearchConfig
    ) -> List[Dict[str, Any]]:
        """
        使用级联方法合并ES和Milvus结果
        先使用Milvus检索，然后使用ES重新排序
        
        参数:
            es_results: ES搜索结果
            milvus_results: Milvus搜索结果
            config: 搜索配置
            
        返回:
            合并后的结果列表
        """
        # 如果一种结果为空，直接返回另一种
        if not es_results:
            return milvus_results
        if not milvus_results:
            return es_results
        
        # 建立Milvus结果映射
        milvus_dict = {}
        for item in milvus_results:
            doc_id = item.get("document_id", "") or item.get("id", "")
            if not doc_id:
                continue
            milvus_dict[doc_id] = item
        
        # 建立ES结果映射
        es_dict = {}
        for item in es_results:
            doc_id = item.get("document_id", "") or item.get("id", "")
            if not doc_id:
                continue
            es_dict[doc_id] = item
        
        # 先获取Milvus和ES的交集结果
        common_results = []
        for doc_id in set(milvus_dict.keys()) & set(es_dict.keys()):
            # 从ES结果中获取基本信息
            result = es_dict[doc_id].copy()
            
            # 加入Milvus分数
            result["vector_score"] = milvus_dict[doc_id].get("score", 0)
            
            # 组合分数: ES分数占比text_weight，Milvus分数占比vector_weight
            result["score"] = (
                es_dict[doc_id].get("score", 0) * config.text_weight +
                milvus_dict[doc_id].get("score", 0) * config.vector_weight
            )
            
            common_results.append(result)
        
        # 排序交集结果
        common_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 如果交集结果足够，直接返回
        if len(common_results) >= config.size:
            return common_results[:config.size]
        
        # 否则，添加仅在一个结果集中出现的文档
        remaining_slots = config.size - len(common_results)
        
        # 优先添加Milvus单独结果
        milvus_only = []
        for doc_id in set(milvus_dict.keys()) - set(es_dict.keys()):
            milvus_only.append(milvus_dict[doc_id])
        
        # 按分数排序
        milvus_only.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 添加足够数量的Milvus结果
        milvus_count = min(len(milvus_only), remaining_slots // 2)
        common_results.extend(milvus_only[:milvus_count])
        
        # 更新剩余槽位
        remaining_slots -= milvus_count
        
        # 添加ES单独结果
        if remaining_slots > 0:
            es_only = []
            for doc_id in set(es_dict.keys()) - set(milvus_dict.keys()):
                es_only.append(es_dict[doc_id])
            
            # 按分数排序
            es_only.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # 添加足够数量的ES结果
            common_results.extend(es_only[:remaining_slots])
        
        # 最后再次按分数排序
        common_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return common_results

    async def create_knowledge_base_index(self, kb_id: str, kb_name: str, description: Optional[str] = None) -> bool:
        """
        为知识库创建索引和分区
        
        参数:
            kb_id: 知识库ID
            kb_name: 知识库名称
            description: 知识库描述
            
        返回:
            操作是否成功
        """
        try:
            # 创建ES别名和路由
            es_success = self.es_manager.create_knowledge_base_alias(kb_id)
            
            # 创建Milvus分区
            milvus_success = self.milvus_manager.create_kb_partition(kb_id)
            
            return es_success and milvus_success
            
        except Exception as e:
            logger.error(f"创建知识库索引时出错: {str(e)}")
            return False
    
    async def delete_knowledge_base_index(self, kb_id: str) -> bool:
        """
        删除知识库索引和分区
        
        参数:
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            # 删除ES别名和文档
            es_success = self.es_manager.delete_knowledge_base_alias(kb_id) and \
                        self.es_manager.delete_kb_documents(kb_id)
            
            # 删除Milvus分区
            milvus_success = self.milvus_manager.delete_kb_partition(kb_id)
            
            return es_success and milvus_success
            
        except Exception as e:
            logger.error(f"删除知识库索引时出错: {str(e)}")
            return False
    
    async def index_document(
        self,
        kb_id: str,
        doc_id: str,
        chunk_id: str,
        title: str,
        content: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        索引文档到ES和Milvus
        
        参数:
            kb_id: 知识库ID
            doc_id: 文档ID
            chunk_id: 分块ID
            title: 标题
            content: 内容
            vector: 向量
            metadata: 元数据
            
        返回:
            操作是否成功
        """
        try:
            # 生成唯一ID
            unique_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # 构建ES文档
            es_doc = {
                "id": unique_id,
                "document_id": doc_id,
                "knowledge_base_id": kb_id,
                "chunk_id": chunk_id,
                "title": title,
                "content": content,
                "vector": vector,
                "metadata": metadata,
                "created_at": now,
                "updated_at": now
            }
            
            # 索引到ES
            es_success = self.es_manager.index_document(es_doc, kb_id)
            
            # 索引到Milvus
            milvus_success = self.milvus_manager.insert_vector(
                id=unique_id,
                document_id=doc_id,
                knowledge_base_id=kb_id,
                chunk_id=chunk_id,
                vector=vector,
                text=content,
                metadata={
                    "title": title,
                    **metadata
                }
            )
            
            return es_success and milvus_success
            
        except Exception as e:
            logger.error(f"索引文档时出错: {str(e)}")
            return False
    
    async def batch_index_documents(
        self,
        kb_id: str,
        documents: List[Dict[str, Any]]
    ) -> bool:
        """
        批量索引文档到ES和Milvus
        
        参数:
            kb_id: 知识库ID
            documents: 文档列表
            
        返回:
            操作是否成功
        """
        try:
            if not documents:
                return True
                
            # 准备Milvus批量数据
            milvus_data = []
            
            # 索引到ES
            for doc in documents:
                # 生成唯一ID
                unique_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                
                # 确保必要字段存在
                if "vector" not in doc or "content" not in doc:
                    logger.warning(f"文档缺少向量或内容字段: {doc.get('id', 'unknown')}")
                    continue
                
                # 构建ES文档
                es_doc = {
                    "id": unique_id,
                    "document_id": doc.get("document_id", ""),
                    "knowledge_base_id": kb_id,
                    "chunk_id": doc.get("chunk_id", ""),
                    "title": doc.get("title", ""),
                    "content": doc["content"],
                    "vector": doc["vector"],
                    "metadata": doc.get("metadata", {}),
                    "created_at": now,
                    "updated_at": now
                }
                
                # 索引到ES
                self.es_manager.index_document(es_doc, kb_id)
                
                # 添加到Milvus批量数据
                milvus_data.append({
                    "id": unique_id,
                    "document_id": doc.get("document_id", ""),
                    "chunk_id": doc.get("chunk_id", ""),
                    "vector": doc["vector"],
                    "text": doc["content"],
                    "metadata": {
                        "title": doc.get("title", ""),
                        **(doc.get("metadata", {}))
                    }
                })
            
            # 批量索引到Milvus
            milvus_success = self.milvus_manager.batch_insert_vectors(milvus_data, kb_id)
            
            return milvus_success
            
        except Exception as e:
            logger.error(f"批量索引文档时出错: {str(e)}")
            return False

# 全局单例实例
_hybrid_search_service = None

def get_hybrid_search_service() -> HybridSearchService:
    """获取HybridSearchService的单例实例"""
    global _hybrid_search_service
    if _hybrid_search_service is None:
        _hybrid_search_service = HybridSearchService()
    return _hybrid_search_service
