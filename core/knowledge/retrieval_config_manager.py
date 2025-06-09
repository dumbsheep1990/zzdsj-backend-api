"""
统一检索配置管理器
集中管理所有检索相关的配置，提供配置验证、默认值处理和动态更新功能
"""

import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import os
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """搜索引擎类型"""
    ELASTICSEARCH = "elasticsearch"
    MILVUS = "milvus" 
    PGVECTOR = "pgvector"
    HYBRID = "hybrid"
    AUTO = "auto"


class FusionMethod(str, Enum):
    """结果融合方法"""
    WEIGHTED_SUM = "weighted_sum"
    RANK_FUSION = "rank_fusion"
    CASCADE = "cascade"
    MAX_SCORE = "max_score"


@dataclass
class VectorSearchConfig:
    """向量搜索配置"""
    similarity_threshold: float = 0.7
    top_k: int = 10
    metric_type: str = "COSINE"
    index_type: str = "HNSW"
    search_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.similarity_threshold < 0.0 or self.similarity_threshold > 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        if self.top_k < 1 or self.top_k > 1000:
            raise ValueError("top_k must be between 1 and 1000")


@dataclass  
class KeywordSearchConfig:
    """关键词搜索配置"""
    top_k: int = 10
    analyzer: str = "ik_max_word"
    boost_title: float = 3.0
    boost_content: float = 2.0
    boost_keywords: float = 1.5
    min_score: Optional[float] = None
    
    def __post_init__(self):
        if self.top_k < 1 or self.top_k > 1000:
            raise ValueError("top_k must be between 1 and 1000")


@dataclass
class HybridSearchConfig:
    """混合搜索配置"""
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    fusion_method: FusionMethod = FusionMethod.WEIGHTED_SUM
    rrf_k: float = 60.0
    normalize_scores: bool = True
    min_final_score: float = 0.0
    
    def __post_init__(self):
        # 验证权重和
        total_weight = self.vector_weight + self.keyword_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Vector and keyword weights must sum to 1.0, got {total_weight}")
        
        if self.rrf_k <= 0:
            raise ValueError("rrf_k must be positive")


@dataclass
class StorageEngineConfig:
    """存储引擎配置"""
    elasticsearch: Dict[str, Any] = field(default_factory=dict)
    milvus: Dict[str, Any] = field(default_factory=dict) 
    pgvector: Dict[str, Any] = field(default_factory=dict)
    
    def get_engine_config(self, engine: SearchEngine) -> Dict[str, Any]:
        """获取指定引擎的配置"""
        config_map = {
            SearchEngine.ELASTICSEARCH: self.elasticsearch,
            SearchEngine.MILVUS: self.milvus,
            SearchEngine.PGVECTOR: self.pgvector
        }
        return config_map.get(engine, {})


@dataclass
class PerformanceConfig:
    """性能配置"""
    enable_cache: bool = True
    cache_ttl: int = 3600  # 秒
    cache_size: int = 1000
    enable_parallel_search: bool = True
    max_concurrent_searches: int = 5
    request_timeout: int = 30
    
    def __post_init__(self):
        if self.cache_ttl < 0:
            self.cache_ttl = 0
        if self.cache_size < 0:
            self.cache_size = 0
        if self.max_concurrent_searches < 1:
            self.max_concurrent_searches = 1


class RetrievalConfigManager:
    """检索配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果不提供则使用默认配置
        """
        self.config_file = config_file
        self._vector_config = VectorSearchConfig()
        self._keyword_config = KeywordSearchConfig()
        self._hybrid_config = HybridSearchConfig()
        self._storage_config = StorageEngineConfig()
        self._performance_config = PerformanceConfig()
        self._preferred_engine = SearchEngine.AUTO
        
        # 加载配置
        self._load_config()
        
    def _load_config(self):
        """从配置文件和环境变量加载配置"""
        try:
            # 1. 加载文件配置
            if self.config_file and Path(self.config_file).exists():
                self._load_from_file()
            
            # 2. 加载环境变量配置
            self._load_from_env()
            
            logger.info("检索配置加载完成")
            
        except Exception as e:
            logger.error(f"加载检索配置失败: {str(e)}")
            logger.info("使用默认配置")
    
    def _load_from_file(self):
        """从YAML文件加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            retrieval_config = config_data.get('retrieval', {})
            
            # 更新向量搜索配置
            vector_config = retrieval_config.get('vector_search', {})
            if vector_config:
                self._vector_config = VectorSearchConfig(**vector_config)
            
            # 更新关键词搜索配置
            keyword_config = retrieval_config.get('keyword_search', {})
            if keyword_config:
                self._keyword_config = KeywordSearchConfig(**keyword_config)
            
            # 更新混合搜索配置
            hybrid_config = retrieval_config.get('hybrid_search', {})
            if hybrid_config:
                self._hybrid_config = HybridSearchConfig(**hybrid_config)
            
            # 更新存储引擎配置
            storage_config = retrieval_config.get('storage_engines', {})
            if storage_config:
                self._storage_config = StorageEngineConfig(**storage_config)
            
            # 更新性能配置
            performance_config = retrieval_config.get('performance', {})
            if performance_config:
                self._performance_config = PerformanceConfig(**performance_config)
            
            # 首选引擎
            preferred_engine = retrieval_config.get('preferred_engine', 'auto')
            self._preferred_engine = SearchEngine(preferred_engine)
            
        except Exception as e:
            logger.error(f"从文件加载配置失败: {str(e)}")
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        try:
            # 向量搜索配置
            if os.getenv('VECTOR_SIMILARITY_THRESHOLD'):
                self._vector_config.similarity_threshold = float(os.getenv('VECTOR_SIMILARITY_THRESHOLD'))
            if os.getenv('VECTOR_TOP_K'):
                self._vector_config.top_k = int(os.getenv('VECTOR_TOP_K'))
            
            # 混合搜索配置
            if os.getenv('HYBRID_VECTOR_WEIGHT'):
                self._hybrid_config.vector_weight = float(os.getenv('HYBRID_VECTOR_WEIGHT'))
            if os.getenv('HYBRID_KEYWORD_WEIGHT'):
                self._hybrid_config.keyword_weight = float(os.getenv('HYBRID_KEYWORD_WEIGHT'))
            
            # 重新验证权重
            total_weight = self._hybrid_config.vector_weight + self._hybrid_config.keyword_weight
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"权重和不等于1.0: {total_weight}，自动调整")
                self._hybrid_config.vector_weight = 0.7
                self._hybrid_config.keyword_weight = 0.3
            
            # 首选引擎
            if os.getenv('PREFERRED_SEARCH_ENGINE'):
                try:
                    self._preferred_engine = SearchEngine(os.getenv('PREFERRED_SEARCH_ENGINE'))
                except ValueError:
                    logger.warning(f"无效的搜索引擎: {os.getenv('PREFERRED_SEARCH_ENGINE')}")
            
        except Exception as e:
            logger.error(f"从环境变量加载配置失败: {str(e)}")
    
    def get_vector_config(self) -> VectorSearchConfig:
        """获取向量搜索配置"""
        return self._vector_config
    
    def get_keyword_config(self) -> KeywordSearchConfig:
        """获取关键词搜索配置"""
        return self._keyword_config
    
    def get_hybrid_config(self) -> HybridSearchConfig:
        """获取混合搜索配置"""
        return self._hybrid_config
    
    def get_storage_config(self) -> StorageEngineConfig:
        """获取存储引擎配置"""
        return self._storage_config
    
    def get_performance_config(self) -> PerformanceConfig:
        """获取性能配置"""
        return self._performance_config
    
    def get_preferred_engine(self) -> SearchEngine:
        """获取首选搜索引擎"""
        return self._preferred_engine
    
    def update_config(self, config_updates: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            config_updates: 配置更新数据
            
        Returns:
            是否更新成功
        """
        try:
            # 更新向量搜索配置
            if 'vector_search' in config_updates:
                vector_updates = config_updates['vector_search']
                for key, value in vector_updates.items():
                    if hasattr(self._vector_config, key):
                        setattr(self._vector_config, key, value)
            
            # 更新混合搜索配置
            if 'hybrid_search' in config_updates:
                hybrid_updates = config_updates['hybrid_search']
                for key, value in hybrid_updates.items():
                    if hasattr(self._hybrid_config, key):
                        setattr(self._hybrid_config, key, value)
                
                # 重新验证权重
                total_weight = self._hybrid_config.vector_weight + self._hybrid_config.keyword_weight
                if abs(total_weight - 1.0) > 0.01:
                    raise ValueError(f"权重和必须等于1.0，当前为: {total_weight}")
            
            # 更新首选引擎
            if 'preferred_engine' in config_updates:
                self._preferred_engine = SearchEngine(config_updates['preferred_engine'])
            
            logger.info("配置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")
            return False
    
    def validate_config(self) -> List[str]:
        """
        验证配置的有效性
        
        Returns:
            错误信息列表，如果为空则配置有效
        """
        errors = []
        
        try:
            # 验证向量搜索配置
            if self._vector_config.similarity_threshold < 0 or self._vector_config.similarity_threshold > 1:
                errors.append("向量搜索相似度阈值必须在0-1之间")
            
            # 验证混合搜索权重
            total_weight = self._hybrid_config.vector_weight + self._hybrid_config.keyword_weight
            if abs(total_weight - 1.0) > 0.01:
                errors.append(f"混合搜索权重和必须等于1.0，当前为: {total_weight}")
            
            # 验证性能配置
            if self._performance_config.max_concurrent_searches < 1:
                errors.append("最大并发搜索数必须大于0")
            
        except Exception as e:
            errors.append(f"配置验证异常: {str(e)}")
        
        return errors
    
    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return {
            "vector_search": {
                "similarity_threshold": self._vector_config.similarity_threshold,
                "top_k": self._vector_config.top_k,
                "metric_type": self._vector_config.metric_type,
                "index_type": self._vector_config.index_type,
                "search_params": self._vector_config.search_params
            },
            "keyword_search": {
                "top_k": self._keyword_config.top_k,
                "analyzer": self._keyword_config.analyzer,
                "boost_title": self._keyword_config.boost_title,
                "boost_content": self._keyword_config.boost_content,
                "boost_keywords": self._keyword_config.boost_keywords,
                "min_score": self._keyword_config.min_score
            },
            "hybrid_search": {
                "vector_weight": self._hybrid_config.vector_weight,
                "keyword_weight": self._hybrid_config.keyword_weight,
                "fusion_method": self._hybrid_config.fusion_method.value,
                "rrf_k": self._hybrid_config.rrf_k,
                "normalize_scores": self._hybrid_config.normalize_scores,
                "min_final_score": self._hybrid_config.min_final_score
            },
            "storage_engines": {
                "elasticsearch": self._storage_config.elasticsearch,
                "milvus": self._storage_config.milvus,
                "pgvector": self._storage_config.pgvector
            },
            "performance": {
                "enable_cache": self._performance_config.enable_cache,
                "cache_ttl": self._performance_config.cache_ttl,
                "cache_size": self._performance_config.cache_size,
                "enable_parallel_search": self._performance_config.enable_parallel_search,
                "max_concurrent_searches": self._performance_config.max_concurrent_searches,
                "request_timeout": self._performance_config.request_timeout
            },
            "preferred_engine": self._preferred_engine.value
        }


# 全局配置管理器实例
_config_manager: Optional[RetrievalConfigManager] = None


def get_retrieval_config_manager(config_file: Optional[str] = None) -> RetrievalConfigManager:
    """获取检索配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = RetrievalConfigManager(config_file)
    return _config_manager


def reload_config(config_file: Optional[str] = None) -> RetrievalConfigManager:
    """重新加载配置"""
    global _config_manager
    _config_manager = RetrievalConfigManager(config_file)
    return _config_manager 