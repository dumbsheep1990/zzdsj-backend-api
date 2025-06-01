"""
存储系统模块
提供向量存储、对象存储、搜索引擎等存储系统的统一接口

重构后的模块结构:
- core: 核心组件和基础架构
- vector_storage: 向量存储功能
- object_storage: 对象存储功能  
- detection: 存储检测功能
"""

# 导入新的重构后的组件
from .core import (
    StorageComponent, VectorStorage, ObjectStorage,
    StorageError, ConnectionError, ConfigurationError, 
    VectorStoreError, ObjectStoreError,
    StorageConfig, create_config_from_settings
)

from .vector_storage import (
    VectorStore, get_vector_store, create_vector_store, MilvusVectorStore
)

from .object_storage import (
    ObjectStore, get_object_store, create_object_store, MinioObjectStore
)

from .detection import (
    StorageDetector, detect_storage_type, get_storage_config
)

# 为了保持向后兼容，导入原有接口
try:
    # 向量存储向后兼容
    from .vector_storage.legacy_support import (
        init_milvus, get_collection, add_vectors, search_similar_vectors
    )
    
    # 对象存储向后兼容
    from .object_storage.legacy_support import (
        get_minio_client, upload_file, download_file, delete_file, get_file_url
    )
    
    # 存储检测向后兼容
    from .detection.legacy_support import (
        check_elasticsearch, check_milvus, determine_storage_strategy, 
        get_vector_store_info
    )
    
    # 保持旧的管理器接口（如果存在）
    try:
        from .milvus_manager import MilvusManager, get_milvus_manager, create_milvus_collection
        from .elasticsearch_manager import ElasticsearchManager, get_elasticsearch_manager, create_elasticsearch_index
        legacy_managers_available = True
    except ImportError:
        legacy_managers_available = False
    
    # 构建完整的__all__列表
    __all__ = [
        # 新的重构后接口
        "StorageComponent", "VectorStorage", "ObjectStorage",
        "StorageError", "ConnectionError", "ConfigurationError", 
        "VectorStoreError", "ObjectStoreError",
        "StorageConfig", "create_config_from_settings",
        
        # 向量存储
        "VectorStore", "get_vector_store", "create_vector_store", "MilvusVectorStore",
        
        # 对象存储  
        "ObjectStore", "get_object_store", "create_object_store", "MinioObjectStore",
        
        # 存储检测
        "StorageDetector", "detect_storage_type", "get_storage_config",
        
        # 向后兼容的向量存储接口
        "init_milvus", "get_collection", "add_vectors", "search_similar_vectors",
        
        # 向后兼容的对象存储接口
        "get_minio_client", "upload_file", "download_file", "delete_file", "get_file_url",
        
        # 向后兼容的存储检测接口
        "check_elasticsearch", "check_milvus", "determine_storage_strategy", "get_vector_store_info"
    ]
    
    # 如果legacy managers可用，添加到导出列表
    if legacy_managers_available:
        __all__.extend([
            "MilvusManager", "get_milvus_manager", "create_milvus_collection",
            "ElasticsearchManager", "get_elasticsearch_manager", "create_elasticsearch_index"
        ])
    
except ImportError as e:
    # 如果向后兼容模块导入失败，只导出新接口
    import logging
    logging.warning(f"Storage模块向后兼容导入失败: {e}")
    
    __all__ = [
        # 新的重构后接口
        "StorageComponent", "VectorStorage", "ObjectStorage",
        "StorageError", "ConnectionError", "ConfigurationError", 
        "VectorStoreError", "ObjectStoreError", 
        "StorageConfig", "create_config_from_settings",
        
        # 向量存储
        "VectorStore", "get_vector_store", "create_vector_store", "MilvusVectorStore",
        
        # 对象存储
        "ObjectStore", "get_object_store", "create_object_store", "MinioObjectStore",
        
        # 存储检测
        "StorageDetector", "detect_storage_type", "get_storage_config"
    ]
