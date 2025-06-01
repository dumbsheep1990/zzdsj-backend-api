"""
存储检测模块
提供存储引擎检测和配置功能
"""

from .detector import StorageDetector, detect_storage_type, get_storage_config
from .legacy_support import (
    check_elasticsearch, check_milvus, determine_storage_strategy, 
    get_vector_store_info
)

__all__ = [
    # 新接口
    "StorageDetector",
    "detect_storage_type",
    "get_storage_config",
    
    # 向后兼容接口
    "check_elasticsearch",
    "check_milvus", 
    "determine_storage_strategy",
    "get_vector_store_info"
] 