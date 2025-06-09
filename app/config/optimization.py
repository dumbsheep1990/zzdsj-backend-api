"""
优化配置集成模块
将优化系统配置与现有应用配置系统集成
"""

from typing import Dict, Any, Optional
import os
from pydantic import BaseSettings, Field
import yaml
import logging

# 延迟导入避免循环依赖
def get_app_settings():
    try:
        from app.config import settings
        return settings
    except ImportError:
        return None


class OptimizationSettings(BaseSettings):
    """优化系统配置"""
    
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
    
    # 数据同步配置
    DATA_SYNC_ENABLED: bool = Field(
        default=True,
        env="DATA_SYNC_ENABLED",
        description="启用数据同步"
    )
    DATA_SYNC_INTERVAL: int = Field(
        default=300,
        env="DATA_SYNC_INTERVAL",
        description="数据同步间隔（秒）"
    )
    DATA_SYNC_BATCH_SIZE: int = Field(
        default=100,
        env="DATA_SYNC_BATCH_SIZE",
        description="数据同步批次大小"
    )
    
    # 监控配置
    MONITORING_ENABLED: bool = Field(
        default=True,
        env="MONITORING_ENABLED",
        description="启用监控"
    )
    METRICS_COLLECTION_INTERVAL: int = Field(
        default=60,
        env="METRICS_COLLECTION_INTERVAL",
        description="指标收集间隔（秒）"
    )
    
    # 配置文件路径
    OPTIMIZATION_CONFIG_FILE: Optional[str] = Field(
        default=None,
        env="OPTIMIZATION_CONFIG_FILE",
        description="优化配置文件路径"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局优化配置实例
optimization_settings = OptimizationSettings()


def get_optimization_config() -> Dict[str, Any]:
    """
    获取优化配置字典
    
    Returns:
        优化配置字典，格式与retrieval_config.yaml兼容
    """
    return {
        "vector_search": {
            "top_k": optimization_settings.VECTOR_SEARCH_TOP_K,
            "similarity_threshold": optimization_settings.VECTOR_SEARCH_THRESHOLD,
            "engine": getattr(get_app_settings(), 'VECTOR_SEARCH_ENGINE', 'milvus') if get_app_settings() else 'milvus',
            "timeout": optimization_settings.REQUEST_TIMEOUT
        },
        "keyword_search": {
            "top_k": optimization_settings.KEYWORD_SEARCH_TOP_K,
            "engine": getattr(get_app_settings(), 'KEYWORD_SEARCH_ENGINE', 'elasticsearch') if get_app_settings() else 'elasticsearch',
            "fuzzy_enabled": getattr(get_app_settings(), 'KEYWORD_FUZZY_ENABLED', True) if get_app_settings() else True
        },
        "hybrid_search": {
            "vector_weight": optimization_settings.HYBRID_VECTOR_WEIGHT,
            "keyword_weight": optimization_settings.HYBRID_KEYWORD_WEIGHT,
            "top_k": max(optimization_settings.VECTOR_SEARCH_TOP_K, optimization_settings.KEYWORD_SEARCH_TOP_K),
            "rrf_k": 60
        },
        "cache": {
            "enabled": optimization_settings.CACHE_ENABLED,
            "strategy": optimization_settings.CACHE_STRATEGY,
            "max_size": optimization_settings.CACHE_MAX_SIZE,
            "ttl_seconds": optimization_settings.CACHE_TTL_SECONDS
        },
        "performance": {
            "max_concurrent_requests": optimization_settings.MAX_CONCURRENT_REQUESTS,
            "enable_query_optimization": optimization_settings.ENABLE_QUERY_OPTIMIZATION,
            "monitoring_enabled": optimization_settings.MONITORING_ENABLED
        },
        "error_handling": {
            "circuit_breaker": {
                "enabled": optimization_settings.CIRCUIT_BREAKER_ENABLED,
                "failure_threshold": optimization_settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                "recovery_timeout": optimization_settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
            }
        },
        "data_sync": {
            "enabled": optimization_settings.DATA_SYNC_ENABLED,
            "sync_interval": optimization_settings.DATA_SYNC_INTERVAL,
            "batch_size": optimization_settings.DATA_SYNC_BATCH_SIZE
        },
        "monitoring": {
            "enabled": optimization_settings.MONITORING_ENABLED,
            "metrics_collection_interval": optimization_settings.METRICS_COLLECTION_INTERVAL
        }
    }


def get_optimization_config_file_path() -> Optional[str]:
    """
    获取优化配置文件路径
    
    Returns:
        配置文件路径，优先级：环境变量 > 默认路径 > None
    """
    # 优先使用环境变量指定的路径
    if optimization_settings.OPTIMIZATION_CONFIG_FILE:
        return optimization_settings.OPTIMIZATION_CONFIG_FILE
    
    # 尝试默认路径
    default_paths = [
        "config/retrieval_config.yaml",
        "config/optimization.yaml",
        "../config/retrieval_config.yaml"
    ]
    
    for path in default_paths:
        if os.path.exists(path):
            return path
    
    return None


def is_optimization_enabled() -> bool:
    """
    检查是否启用优化功能
    
    Returns:
        是否启用优化
    """
    return optimization_settings.ENABLE_SEARCH_OPTIMIZATION


def get_cache_config() -> Dict[str, Any]:
    """
    获取缓存配置
    
    Returns:
        缓存配置字典
    """
    return {
        "enabled": optimization_settings.CACHE_ENABLED,
        "strategy": optimization_settings.CACHE_STRATEGY,
        "max_size": optimization_settings.CACHE_MAX_SIZE,
        "ttl_seconds": optimization_settings.CACHE_TTL_SECONDS
    }


def update_optimization_settings(**kwargs) -> bool:
    """
    动态更新优化设置
    
    Args:
        **kwargs: 要更新的设置项
        
    Returns:
        是否更新成功
    """
    try:
        for key, value in kwargs.items():
            if hasattr(optimization_settings, key.upper()):
                setattr(optimization_settings, key.upper(), value)
        return True
    except Exception:
        return False


def load_retrieval_config() -> Dict[str, Any]:
    """
    从retrieval_config.yaml加载配置
    
    Returns:
        配置字典
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "retrieval_config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"无法加载retrieval_config.yaml: {str(e)}")
    
    # 返回默认配置
    return {}


def merge_optimization_configs() -> Dict[str, Any]:
    """
    合并优化配置和YAML配置
    
    Returns:
        合并后的配置字典
    """
    # 获取基础优化配置
    base_config = get_optimization_config()
    
    # 加载YAML配置
    yaml_config = load_retrieval_config()
    
    # 合并配置，YAML配置优先
    merged_config = base_config.copy()
    
    if yaml_config:
        # 合并向量搜索配置
        if "vector_search" in yaml_config:
            merged_config["vector_search"].update(yaml_config["vector_search"])
        
        # 合并关键词搜索配置
        if "keyword_search" in yaml_config:
            merged_config["keyword_search"].update(yaml_config["keyword_search"])
        
        # 合并混合搜索配置
        if "hybrid_search" in yaml_config:
            merged_config["hybrid_search"].update(yaml_config["hybrid_search"])
        
        # 合并缓存配置
        if "cache" in yaml_config:
            merged_config["cache"].update(yaml_config["cache"])
        
        # 合并性能配置
        if "performance" in yaml_config:
            merged_config["performance"].update(yaml_config["performance"])
        
        # 合并错误处理配置
        if "error_handling" in yaml_config:
            merged_config["error_handling"].update(yaml_config["error_handling"])
        
        # 添加其他配置部分
        for key in ["data_sync", "monitoring", "strategy_selection", "system", "security"]:
            if key in yaml_config:
                merged_config[key] = yaml_config[key]
    
    return merged_config


def get_final_optimization_config() -> Dict[str, Any]:
    """
    获取最终的优化配置（合并所有配置源）
    
    Returns:
        最终配置字典
    """
    return merge_optimization_configs()


# 创建全局最终配置实例
final_optimization_config = None

def get_cached_optimization_config() -> Dict[str, Any]:
    """
    获取缓存的优化配置（避免重复加载）
    
    Returns:
        优化配置字典
    """
    global final_optimization_config
    if final_optimization_config is None:
        final_optimization_config = get_final_optimization_config()
    return final_optimization_config


# 导入日志模块
logger = logging.getLogger(__name__)

# 导出主要组件
__all__ = [
    'OptimizationSettings',
    'optimization_settings',
    'get_optimization_config',
    'get_optimization_config_file_path',
    'is_optimization_enabled',
    'get_cache_config',
    'update_optimization_settings',
    'get_cached_optimization_config'
] 