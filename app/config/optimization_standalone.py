"""
独立的优化配置模块
避免循环导入问题，提供基本的优化配置功能
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field


class StandaloneOptimizationSettings(BaseSettings):
    """独立的优化系统配置"""
    
    # 优化开关
    ENABLE_SEARCH_OPTIMIZATION: bool = Field(
        default=True, 
        env="ENABLE_SEARCH_OPTIMIZATION",
        description="启用搜索优化功能"
    )
    
    # 缓存配置
    CACHE_ENABLED: bool = Field(
        default=True,
        env="CACHE_ENABLED", 
        description="启用缓存"
    )
    CACHE_STRATEGY: str = Field(
        default="hybrid",
        env="CACHE_STRATEGY",
        description="缓存策略：lru/lfu/ttl/hybrid"
    )
    CACHE_MAX_SIZE: int = Field(
        default=5000,
        env="CACHE_MAX_SIZE",
        description="缓存最大条目数"
    )
    CACHE_TTL_SECONDS: int = Field(
        default=1800,
        env="CACHE_TTL_SECONDS", 
        description="缓存TTL时间（秒）"
    )
    
    # 性能配置
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=100,
        env="MAX_CONCURRENT_REQUESTS",
        description="最大并发请求数"
    )
    REQUEST_TIMEOUT: int = Field(
        default=120,
        env="REQUEST_TIMEOUT",
        description="请求超时时间（秒）"
    )
    ENABLE_QUERY_OPTIMIZATION: bool = Field(
        default=True,
        env="ENABLE_QUERY_OPTIMIZATION",
        description="启用查询优化"
    )
    
    # 搜索配置
    VECTOR_SEARCH_TOP_K: int = Field(
        default=20,
        env="VECTOR_SEARCH_TOP_K",
        description="向量搜索默认返回数量"
    )
    VECTOR_SEARCH_THRESHOLD: float = Field(
        default=0.75,
        env="VECTOR_SEARCH_THRESHOLD",
        description="向量搜索相似度阈值"
    )
    KEYWORD_SEARCH_TOP_K: int = Field(
        default=15,
        env="KEYWORD_SEARCH_TOP_K",
        description="关键词搜索默认返回数量"
    )
    HYBRID_VECTOR_WEIGHT: float = Field(
        default=0.6,
        env="HYBRID_VECTOR_WEIGHT",
        description="混合搜索向量权重"
    )
    HYBRID_KEYWORD_WEIGHT: float = Field(
        default=0.4,
        env="HYBRID_KEYWORD_WEIGHT",
        description="混合搜索关键词权重"
    )
    
    # 错误处理配置
    CIRCUIT_BREAKER_ENABLED: bool = Field(
        default=True,
        env="CIRCUIT_BREAKER_ENABLED",
        description="启用熔断器"
    )
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5,
        env="CIRCUIT_BREAKER_FAILURE_THRESHOLD",
        description="熔断器失败阈值"
    )
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(
        default=60,
        env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
        description="熔断器恢复超时（秒）"
    )
    
    # 监控配置
    MONITORING_ENABLED: bool = Field(
        default=True,
        env="MONITORING_ENABLED",
        description="启用监控"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
standalone_settings = StandaloneOptimizationSettings()


def get_standalone_optimization_config() -> Dict[str, Any]:
    """
    获取独立的优化配置字典
    
    Returns:
        优化配置字典
    """
    return {
        "vector_search": {
            "top_k": standalone_settings.VECTOR_SEARCH_TOP_K,
            "similarity_threshold": standalone_settings.VECTOR_SEARCH_THRESHOLD,
            "engine": "milvus",
            "timeout": standalone_settings.REQUEST_TIMEOUT
        },
        "keyword_search": {
            "top_k": standalone_settings.KEYWORD_SEARCH_TOP_K,
            "engine": "elasticsearch",
            "fuzzy_enabled": True
        },
        "hybrid_search": {
            "vector_weight": standalone_settings.HYBRID_VECTOR_WEIGHT,
            "keyword_weight": standalone_settings.HYBRID_KEYWORD_WEIGHT,
            "top_k": max(standalone_settings.VECTOR_SEARCH_TOP_K, standalone_settings.KEYWORD_SEARCH_TOP_K),
            "rrf_k": 60
        },
        "cache": {
            "enabled": standalone_settings.CACHE_ENABLED,
            "strategy": standalone_settings.CACHE_STRATEGY,
            "max_size": standalone_settings.CACHE_MAX_SIZE,
            "ttl_seconds": standalone_settings.CACHE_TTL_SECONDS
        },
        "performance": {
            "max_concurrent_requests": standalone_settings.MAX_CONCURRENT_REQUESTS,
            "enable_query_optimization": standalone_settings.ENABLE_QUERY_OPTIMIZATION,
            "monitoring_enabled": standalone_settings.MONITORING_ENABLED
        },
        "error_handling": {
            "circuit_breaker": {
                "enabled": standalone_settings.CIRCUIT_BREAKER_ENABLED,
                "failure_threshold": standalone_settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                "recovery_timeout": standalone_settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
            }
        },
        "monitoring": {
            "enabled": standalone_settings.MONITORING_ENABLED
        }
    }


def is_standalone_optimization_enabled() -> bool:
    """
    检查是否启用优化功能
    
    Returns:
        是否启用优化
    """
    return standalone_settings.ENABLE_SEARCH_OPTIMIZATION


def get_standalone_cache_config() -> Dict[str, Any]:
    """
    获取缓存配置
    
    Returns:
        缓存配置字典
    """
    return {
        "enabled": standalone_settings.CACHE_ENABLED,
        "strategy": standalone_settings.CACHE_STRATEGY,
        "max_size": standalone_settings.CACHE_MAX_SIZE,
        "ttl_seconds": standalone_settings.CACHE_TTL_SECONDS
    }


def update_standalone_settings(**kwargs) -> bool:
    """
    动态更新优化设置
    
    Args:
        **kwargs: 要更新的设置项
        
    Returns:
        是否更新成功
    """
    try:
        for key, value in kwargs.items():
            if hasattr(standalone_settings, key.upper()):
                setattr(standalone_settings, key.upper(), value)
        return True
    except Exception:
        return False


# 导出主要组件
__all__ = [
    'StandaloneOptimizationSettings',
    'standalone_settings',
    'get_standalone_optimization_config',
    'is_standalone_optimization_enabled',
    'get_standalone_cache_config',
    'update_standalone_settings'
] 