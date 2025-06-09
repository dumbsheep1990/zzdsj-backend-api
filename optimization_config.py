"""简单的优化配置模块"""

from typing import Dict, Any

def get_optimization_config() -> Dict[str, Any]:
    """获取优化配置"""
    return {
        "vector_search": {
            "top_k": 20,
            "similarity_threshold": 0.75,
            "engine": "milvus",
            "timeout": 120
        },
        "keyword_search": {
            "top_k": 15,
            "engine": "elasticsearch",
            "fuzzy_enabled": True
        },
        "hybrid_search": {
            "vector_weight": 0.6,
            "keyword_weight": 0.4,
            "top_k": 20,
            "rrf_k": 60
        },
        "cache": {
            "enabled": True,
            "strategy": "hybrid",
            "max_size": 5000,
            "ttl_seconds": 1800
        },
        "performance": {
            "max_concurrent_requests": 100,
            "enable_query_optimization": True,
            "monitoring_enabled": True
        }
    }

def is_optimization_enabled() -> bool:
    """检查是否启用优化功能"""
    import os
    return os.getenv('ENABLE_SEARCH_OPTIMIZATION', 'true').lower() == 'true'

# 配置组件状态
OPTIMIZATION_AVAILABLE = False
CONFIG_MANAGER_AVAILABLE = False

print("✅ 优化配置模块加载成功") 