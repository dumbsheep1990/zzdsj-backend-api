"""
存储引擎检测模块
自动检测并适应不同环境中可用的存储引擎，支持灵活的混合检索系统
"""

import logging
from typing import Dict, List, Any, Optional
from elasticsearch import Elasticsearch
from pymilvus import connections, utility
import os

from app.config import settings

logger = logging.getLogger(__name__)

class StorageDetector:
    """存储引擎检测器，自动识别当前环境中可用的存储引擎"""
    
    @staticmethod
    def check_elasticsearch():
        """检查Elasticsearch是否可用"""
        try:
            # 检查是否有环境变量禁用ES
            if os.getenv("ELASTICSEARCH_ENABLED", "").lower() == "false":
                logger.info("Elasticsearch已通过环境变量禁用")
                return False
                
            # 检查必要的配置信息是否存在
            if not settings.ELASTICSEARCH_URL:
                logger.warning("Elasticsearch URL未配置")
                return False
                
            # 尝试连接Elasticsearch
            es_client_kwargs = {}
            
            # 身份验证配置
            if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
                es_client_kwargs["basic_auth"] = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
            
            if settings.ELASTICSEARCH_API_KEY:
                es_client_kwargs["api_key"] = settings.ELASTICSEARCH_API_KEY
                
            if settings.ELASTICSEARCH_CLOUD_ID:
                es_client_kwargs["cloud_id"] = settings.ELASTICSEARCH_CLOUD_ID
            
            # 创建Elasticsearch客户端
            es = Elasticsearch(
                settings.ELASTICSEARCH_URL,
                **es_client_kwargs
            )
            
            # 检查集群健康状态
            health = es.cluster.health()
            
            # 检查所需索引是否存在
            index_exists = es.indices.exists(index=settings.ELASTICSEARCH_INDEX)
            
            logger.info(f"Elasticsearch连接检测: 集群状态={health.get('status')}, 索引存在={index_exists}")
            
            return health.get('status') in ['green', 'yellow']
            
        except Exception as e:
            logger.warning(f"Elasticsearch连接检测失败: {str(e)}")
            return False
    
    @staticmethod
    def check_milvus():
        """检查Milvus是否可用"""
        try:
            # 检查是否有环境变量禁用Milvus
            if os.getenv("MILVUS_ENABLED", "").lower() == "false":
                logger.info("Milvus已通过环境变量禁用")
                return False
                
            # 检查必要的配置信息是否存在
            if not settings.MILVUS_HOST or not settings.MILVUS_PORT:
                logger.warning("Milvus主机或端口未配置")
                return False
                
            # 尝试连接Milvus
            connections.connect(
                alias="default_check", 
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            
            # 检查集合是否存在
            collection_exists = utility.has_collection(settings.MILVUS_COLLECTION)
            
            logger.info(f"Milvus连接检测: 集合存在={collection_exists}")
            
            # 关闭连接
            connections.disconnect("default_check")
            
            return True
            
        except Exception as e:
            logger.warning(f"Milvus连接检测失败: {str(e)}")
            return False
    
    @staticmethod
    def determine_storage_strategy():
        """基于可用存储引擎确定最佳存储策略"""
        # 首先检查是否通过环境变量明确设置了策略
        strategy_from_env = os.getenv("SEARCH_STORAGE_STRATEGY", "").lower()
        if strategy_from_env and strategy_from_env != "auto":
            logger.info(f"使用环境变量指定的存储策略: {strategy_from_env}")
            return strategy_from_env
        
        # 检查配置文件中是否明确设置了策略
        configured_strategy = getattr(settings, "SEARCH_STORAGE_STRATEGY", "auto").lower()
        if configured_strategy and configured_strategy != "auto":
            logger.info(f"使用配置文件指定的存储策略: {configured_strategy}")
            return configured_strategy
        
        # 检测可用存储
        es_available = StorageDetector.check_elasticsearch()
        milvus_available = StorageDetector.check_milvus()
        
        logger.info(f"存储可用性检测: Elasticsearch={es_available}, Milvus={milvus_available}")
        
        # 基于可用性决定策略
        if es_available and milvus_available:
            strategy = "hybrid"
        elif es_available:
            strategy = "elasticsearch"
        elif milvus_available:
            strategy = "milvus"
        else:
            # 无可用向量存储，降级到数据库
            strategy = "database"
        
        logger.info(f"自动确定的存储策略: {strategy}")
        return strategy
    
    @staticmethod
    def get_vector_store_info():
        """获取向量存储详细信息"""
        info = {
            "strategy": StorageDetector.determine_storage_strategy(),
            "elasticsearch": {
                "available": StorageDetector.check_elasticsearch(),
                "url": settings.ELASTICSEARCH_URL,
                "index": settings.ELASTICSEARCH_INDEX,
                "hybrid_search": getattr(settings, "ELASTICSEARCH_HYBRID_SEARCH", True),
                "hybrid_weight": getattr(settings, "ELASTICSEARCH_HYBRID_WEIGHT", 0.5)
            },
            "milvus": {
                "available": StorageDetector.check_milvus(),
                "host": settings.MILVUS_HOST,
                "port": settings.MILVUS_PORT,
                "collection": settings.MILVUS_COLLECTION
            }
        }
        return info
