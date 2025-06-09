"""
智能检索策略选择器
统一检索策略选择逻辑，根据环境状态和配置智能选择最佳检索策略
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """搜索引擎类型"""
    ELASTICSEARCH = "elasticsearch"
    MILVUS = "milvus" 
    PGVECTOR = "pgvector"
    HYBRID = "hybrid"
    AUTO = "auto"


class EngineStatus(str, Enum):
    """引擎状态"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class EngineCapability:
    """引擎能力评估"""
    engine: SearchEngine
    status: EngineStatus
    performance_score: float  # 0-1 性能评分
    feature_support: Dict[str, bool]  # 功能支持情况
    latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    
    def is_usable(self) -> bool:
        """判断引擎是否可用"""
        return self.status in [EngineStatus.AVAILABLE, EngineStatus.DEGRADED]


@dataclass
class SearchStrategy:
    """搜索策略"""
    primary_engine: SearchEngine
    fallback_engines: List[SearchEngine]
    hybrid_config: Optional[Dict[str, Any]] = None
    estimated_performance: float = 0.0
    confidence: float = 0.0
    
    def get_description(self) -> str:
        """获取策略描述"""
        if self.primary_engine == SearchEngine.HYBRID:
            return f"混合搜索策略 (性能评分: {self.estimated_performance:.2f})"
        elif self.fallback_engines:
            fallback_str = ", ".join([e.value for e in self.fallback_engines])
            return f"{self.primary_engine.value} 主策略，备选: {fallback_str}"
        else:
            return f"{self.primary_engine.value} 单引擎策略"


class SearchStrategySelector:
    """检索策略选择器"""
    
    def __init__(self):
        """初始化策略选择器"""
        self._engine_capabilities: Dict[SearchEngine, EngineCapability] = {}
        self._last_assessment_time = 0
        self._assessment_cache_ttl = 60  # 缓存60秒
        
    async def assess_engine_capabilities(self, force_refresh: bool = False) -> Dict[SearchEngine, EngineCapability]:
        """
        评估各引擎能力
        
        Args:
            force_refresh: 是否强制刷新评估
            
        Returns:
            引擎能力评估结果
        """
        import time
        current_time = time.time()
        
        # 检查缓存
        if (not force_refresh and 
            self._engine_capabilities and 
            current_time - self._last_assessment_time < self._assessment_cache_ttl):
            return self._engine_capabilities
        
        logger.info("开始评估引擎能力")
        
        # 并发评估各引擎
        assessment_tasks = [
            self._assess_elasticsearch(),
            self._assess_milvus(), 
            self._assess_pgvector()
        ]
        
        try:
            capabilities = await asyncio.gather(*assessment_tasks, return_exceptions=True)
            
            # 处理评估结果
            self._engine_capabilities.clear()
            for capability in capabilities:
                if isinstance(capability, Exception):
                    logger.error(f"引擎评估失败: {str(capability)}")
                    continue
                
                if capability:
                    self._engine_capabilities[capability.engine] = capability
            
            self._last_assessment_time = current_time
            logger.info(f"引擎能力评估完成，发现 {len(self._engine_capabilities)} 个可用引擎")
            
        except Exception as e:
            logger.error(f"引擎能力评估异常: {str(e)}")
        
        return self._engine_capabilities
    
    async def _assess_elasticsearch(self) -> Optional[EngineCapability]:
        """评估Elasticsearch能力"""
        try:
            # 动态导入以避免循环依赖
            from app.utils.storage.detection import check_elasticsearch
            
            # 基础可用性检查
            is_available = check_elasticsearch()
            
            if not is_available:
                return EngineCapability(
                    engine=SearchEngine.ELASTICSEARCH,
                    status=EngineStatus.UNAVAILABLE,
                    performance_score=0.0,
                    feature_support={}
                )
            
            # 功能支持评估
            feature_support = {
                "full_text_search": True,
                "vector_search": True,  # ES 8.x+ 支持
                "hybrid_search": True,
                "fuzzy_search": True,
                "aggregations": True,
                "highlighting": True
            }
            
            # 性能评估（简化版，实际应该测试查询响应时间）
            performance_score = 0.8  # 假设ES有良好的性能
            
            return EngineCapability(
                engine=SearchEngine.ELASTICSEARCH,
                status=EngineStatus.AVAILABLE,
                performance_score=performance_score,
                feature_support=feature_support,
                latency_ms=50.0,  # 估算延迟
                error_rate=0.01   # 估算错误率
            )
            
        except Exception as e:
            logger.error(f"评估Elasticsearch失败: {str(e)}")
            return EngineCapability(
                engine=SearchEngine.ELASTICSEARCH,
                status=EngineStatus.UNKNOWN,
                performance_score=0.0,
                feature_support={}
            )
    
    async def _assess_milvus(self) -> Optional[EngineCapability]:
        """评估Milvus能力"""
        try:
            from app.utils.storage.detection import check_milvus
            
            is_available = check_milvus()
            
            if not is_available:
                return EngineCapability(
                    engine=SearchEngine.MILVUS,
                    status=EngineStatus.UNAVAILABLE,
                    performance_score=0.0,
                    feature_support={}
                )
            
            feature_support = {
                "vector_search": True,
                "similarity_search": True,
                "batch_search": True,
                "full_text_search": False,  # Milvus 主要用于向量搜索
                "hybrid_search": False,     # 需要与其他引擎配合
                "scalability": True
            }
            
            # Milvus 在向量搜索方面性能优异
            performance_score = 0.9
            
            return EngineCapability(
                engine=SearchEngine.MILVUS,
                status=EngineStatus.AVAILABLE,
                performance_score=performance_score,
                feature_support=feature_support,
                latency_ms=20.0,
                error_rate=0.005
            )
            
        except Exception as e:
            logger.error(f"评估Milvus失败: {str(e)}")
            return EngineCapability(
                engine=SearchEngine.MILVUS,
                status=EngineStatus.UNKNOWN,
                performance_score=0.0,
                feature_support={}
            )
    
    async def _assess_pgvector(self) -> Optional[EngineCapability]:
        """评估PGVector能力"""
        try:
            # 假设PostgreSQL总是可用（作为基础存储）
            feature_support = {
                "vector_search": True,
                "sql_integration": True,
                "transactions": True,
                "full_text_search": True,  # PostgreSQL 自带全文搜索
                "hybrid_search": True,
                "reliability": True
            }
            
            # PGVector 性能中等，但可靠性高
            performance_score = 0.6
            
            return EngineCapability(
                engine=SearchEngine.PGVECTOR,
                status=EngineStatus.AVAILABLE,
                performance_score=performance_score,
                feature_support=feature_support,
                latency_ms=100.0,
                error_rate=0.001
            )
            
        except Exception as e:
            logger.error(f"评估PGVector失败: {str(e)}")
            return EngineCapability(
                engine=SearchEngine.PGVECTOR,
                status=EngineStatus.DEGRADED,
                performance_score=0.3,
                feature_support={"basic_storage": True}
            )
    
    async def select_optimal_strategy(
        self, 
        query_requirements: Optional[Dict[str, Any]] = None
    ) -> SearchStrategy:
        """
        选择最优搜索策略
        
        Args:
            query_requirements: 查询需求，包含所需功能、性能要求等
            
        Returns:
            推荐的搜索策略
        """
        try:
            # 1. 评估引擎能力
            capabilities = await self.assess_engine_capabilities()
            
            if not capabilities:
                logger.warning("没有可用的搜索引擎，使用数据库降级策略")
                return SearchStrategy(
                    primary_engine=SearchEngine.PGVECTOR,
                    fallback_engines=[],
                    estimated_performance=0.3,
                    confidence=0.5
                )
            
            # 2. 分析查询需求
            query_requirements = query_requirements or {}
            
            # 3. 策略选择逻辑
            strategy = await self._auto_select_strategy(capabilities, query_requirements)
            
            logger.info(f"选择搜索策略: {strategy.get_description()}")
            return strategy
            
        except Exception as e:
            logger.error(f"选择搜索策略失败: {str(e)}")
            # 返回最保守的策略
            return SearchStrategy(
                primary_engine=SearchEngine.PGVECTOR,
                fallback_engines=[],
                estimated_performance=0.3,
                confidence=0.3
            )
    
    async def _auto_select_strategy(
        self, 
        capabilities: Dict[SearchEngine, EngineCapability],
        query_requirements: Dict[str, Any]
    ) -> SearchStrategy:
        """自动选择最优策略"""
        
        usable_engines = {
            engine: cap for engine, cap in capabilities.items() 
            if cap.is_usable()
        }
        
        if not usable_engines:
            return SearchStrategy(
                primary_engine=SearchEngine.PGVECTOR,
                fallback_engines=[],
                estimated_performance=0.3,
                confidence=0.5
            )
        
        # 检查是否可以使用混合策略
        has_es = SearchEngine.ELASTICSEARCH in usable_engines
        has_milvus = SearchEngine.MILVUS in usable_engines
        has_pgvector = SearchEngine.PGVECTOR in usable_engines
        
        needs_vector = query_requirements.get('vector_search', True)
        needs_full_text = query_requirements.get('full_text_search', True)
        performance_priority = query_requirements.get('performance_priority', 'balanced')
        
        # 策略优先级判断
        if has_es and has_milvus and needs_vector and needs_full_text:
            # ES + Milvus 混合策略
            return SearchStrategy(
                primary_engine=SearchEngine.HYBRID,
                fallback_engines=[SearchEngine.ELASTICSEARCH, SearchEngine.PGVECTOR],
                hybrid_config={
                    "engines": [SearchEngine.ELASTICSEARCH, SearchEngine.MILVUS],
                    "fusion_method": "rank_fusion"
                },
                estimated_performance=0.95,
                confidence=0.9
            )
        
        elif has_es and (needs_full_text or performance_priority == 'speed'):
            # ES 单引擎策略
            fallbacks = []
            if has_milvus:
                fallbacks.append(SearchEngine.MILVUS)
            if has_pgvector:
                fallbacks.append(SearchEngine.PGVECTOR)
            
            return SearchStrategy(
                primary_engine=SearchEngine.ELASTICSEARCH,
                fallback_engines=fallbacks,
                estimated_performance=0.8,
                confidence=0.8
            )
        
        elif has_milvus and needs_vector and performance_priority == 'accuracy':
            # Milvus 单引擎策略（高精度向量搜索）
            fallbacks = []
            if has_es:
                fallbacks.append(SearchEngine.ELASTICSEARCH)
            if has_pgvector:
                fallbacks.append(SearchEngine.PGVECTOR)
            
            return SearchStrategy(
                primary_engine=SearchEngine.MILVUS,
                fallback_engines=fallbacks,
                estimated_performance=0.85,
                confidence=0.75
            )
        
        elif has_pgvector:
            # PGVector 保守策略
            fallbacks = []
            if has_es:
                fallbacks.append(SearchEngine.ELASTICSEARCH)
            if has_milvus:
                fallbacks.append(SearchEngine.MILVUS)
            
            return SearchStrategy(
                primary_engine=SearchEngine.PGVECTOR,
                fallback_engines=fallbacks,
                estimated_performance=0.6,
                confidence=0.7
            )
        
        else:
            # 默认策略
            available_engines = list(usable_engines.keys())
            return SearchStrategy(
                primary_engine=available_engines[0],
                fallback_engines=available_engines[1:],
                estimated_performance=0.5,
                confidence=0.6
            )


# 全局策略选择器实例
_strategy_selector: Optional[SearchStrategySelector] = None


def get_search_strategy_selector() -> SearchStrategySelector:
    """获取检索策略选择器实例"""
    global _strategy_selector
    if _strategy_selector is None:
        _strategy_selector = SearchStrategySelector()
    return _strategy_selector


async def select_search_strategy(query_requirements: Optional[Dict[str, Any]] = None) -> SearchStrategy:
    """便捷函数：选择搜索策略"""
    selector = get_search_strategy_selector()
    return await selector.select_optimal_strategy(query_requirements) 