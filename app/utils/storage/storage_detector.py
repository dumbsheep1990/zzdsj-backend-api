"""
存储引擎检测模块
自动检测并适应不同环境中可用的存储引擎，支持灵活的混合检索系统
注意：MinIO和Elasticsearch是系统的基础必需组件，在任何部署模式下都必须启用
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
        """检查Elasticsearch是否可用 (基础必需组件)"""
        try:
            # Elasticsearch是基础必需组件，不允许通过环境变量禁用
            logger.info("检测Elasticsearch连接状态 (基础必需组件)")
            
            # 检查必要的配置信息是否存在
            if not settings.ELASTICSEARCH_URL:
                logger.error("Elasticsearch URL未配置 - 这是基础必需组件")
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
            
            cluster_status = health.get('status', 'unknown')
            is_available = cluster_status in ['green', 'yellow']
            
            logger.info(f"Elasticsearch状态: 集群状态={cluster_status}, 索引存在={index_exists}, 可用={is_available}")
            
            if not is_available:
                logger.error("Elasticsearch集群不健康 - 这会影响系统核心功能")
            
            return is_available
            
        except Exception as e:
            logger.error(f"Elasticsearch连接检测失败 (基础必需组件): {str(e)}")
            return False
    
    @staticmethod
    def check_milvus():
        """检查Milvus是否可用 (可选增强组件)"""
        try:
            # 检查部署模式，在最小化模式下自动跳过
            if settings.DEPLOYMENT_MODE == 'minimal':
                logger.info("最小化部署模式，跳过Milvus检测")
                return False
                
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
            logger.warning(f"Milvus连接检测失败 (可选增强组件): {str(e)}")
            return False
    
    @staticmethod
    def check_minio():
        """检查MinIO是否可用 (基础必需组件)"""
        try:
            # MinIO是基础必需组件，不允许通过环境变量禁用
            logger.info("检测MinIO连接状态 (基础必需组件)")
            
            # 检查必要的配置信息是否存在
            if not settings.MINIO_ENDPOINT:
                logger.error("MinIO端点未配置 - 这是基础必需组件")
                return False
                
            # 尝试导入和连接MinIO
            try:
                from minio import Minio
                from minio.error import S3Error
                
                client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                
                # 测试连接 - 列出存储桶
                buckets = list(client.list_buckets())
                
                # 检查默认存储桶是否存在
                bucket_exists = client.bucket_exists(settings.MINIO_BUCKET)
                
                logger.info(f"MinIO状态: 存储桶数量={len(buckets)}, 默认存储桶存在={bucket_exists}")
                
                if not bucket_exists:
                    logger.warning(f"默认存储桶 '{settings.MINIO_BUCKET}' 不存在，需要初始化")
                
                return True
                
            except ImportError:
                logger.error("MinIO依赖库未安装 - 这是基础必需组件")
                return False
            except Exception as e:
                logger.error(f"MinIO连接失败 (基础必需组件): {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"MinIO检测异常 (基础必需组件): {str(e)}")
            return False
    
    @staticmethod
    def determine_storage_strategy():
        """基于可用存储引擎确定最佳存储策略"""
        # 检测基础必需存储组件
        es_available = StorageDetector.check_elasticsearch()
        minio_available = StorageDetector.check_minio()
        
        # 检测可选增强组件
        milvus_available = StorageDetector.check_milvus()
        
        logger.info(f"存储组件可用性: Elasticsearch={es_available}(必需), MinIO={minio_available}(必需), Milvus={milvus_available}(可选)")
        
        # 检查基础必需组件是否可用
        if not es_available or not minio_available:
            missing_components = []
            if not es_available:
                missing_components.append("Elasticsearch")
            if not minio_available:
                missing_components.append("MinIO")
            
            logger.error(f"基础必需存储组件不可用: {', '.join(missing_components)}")
            strategy = "insufficient_storage"
        else:
            # 基础组件可用，根据可选组件确定策略
            if milvus_available:
                # 完整架构：ES + MinIO + Milvus
                strategy = "full_dual_storage_enhanced"
                logger.info("使用完整双存储引擎架构 (ES + MinIO + Milvus增强)")
            else:
                # 标准架构：ES + MinIO
                strategy = "standard_dual_storage"
                logger.info("使用标准双存储引擎架构 (ES + MinIO)")
        
        return strategy
    
    @staticmethod
    def get_vector_store_info():
        """获取向量存储详细信息"""
        
        # 检查各存储引擎的可用性
        es_available = StorageDetector.check_elasticsearch()
        milvus_available = StorageDetector.check_milvus()
        
        # 检查文件存储
        file_storage_available = True  # 本地文件存储总是可用
        minio_available = StorageDetector.check_minio() if settings.MINIO_ENABLED else False
        
        # 确定存储策略
        if milvus_available:
            strategy = "milvus_primary"
        elif es_available:
            strategy = "elasticsearch_only"
        else:
            strategy = "no_vector_store"
        
        return {
            # Elasticsearch - 基础必需组件
            "elasticsearch": {
                "available": es_available,
                "url": settings.ELASTICSEARCH_URL,
                "index": settings.ELASTICSEARCH_INDEX,
                "enabled": True,  # 始终启用
                "is_required": True,  # 标记为基础必需组件
                "component_type": "core",
                "description": "文档分片存储和混合检索引擎 (基础必需)",
                "role": "提供文档索引、全文搜索和混合检索功能",
                "features": ["文档分片存储", "全文索引", "向量搜索", "混合检索"]
            },
            
            # 用户文件存储 - 基础必需功能
            "file_storage": {
                "available": file_storage_available,
                "type": settings.FILE_STORAGE_TYPE,
                "path": settings.FILE_STORAGE_PATH,
                "base_url": settings.FILE_STORAGE_BASE_URL,
                "enabled": True,  # 始终启用
                "is_required": True,  # 标记为基础必需功能
                "component_type": "core",
                "description": "用户文件上传和存储 (基础必需)",
                "role": "提供用户文件上传、存储和访问功能"
            },
            
            # MinIO - 可选增强组件（主要作为Milvus依赖）
            "minio": {
                "available": minio_available,
                "endpoint": settings.MINIO_ENDPOINT,
                "bucket": settings.MINIO_BUCKET,
                "enabled": settings.MINIO_ENABLED,
                "is_required": False,  # 标记为可选组件
                "component_type": "enhancement",
                "description": "Milvus存储后端或高级文件存储 (可选增强)",
                "role": "作为Milvus的存储依赖或提供高级文件存储功能"
            },
            
            # Milvus - 可选增强组件
            "milvus": {
                "available": milvus_available,
                "host": settings.MILVUS_HOST,
                "port": settings.MILVUS_PORT,
                "collection": settings.MILVUS_COLLECTION,
                "enabled": settings.MILVUS_ENABLED,
                "is_required": False,  # 标记为可选组件
                "component_type": "enhancement",
                "description": "高性能向量搜索引擎 (可选增强)",
                "role": "提供比Elasticsearch更高性能的向量搜索能力"
            },
            
            # 系统架构总结
            "storage_architecture": {
                "type": "elasticsearch_based" if es_available else "insufficient",
                "core_components": ["elasticsearch", "file_storage"],
                "enhancement_components": [comp for comp in ["minio", "milvus"] if locals().get(f"{comp}_available", False)],
                "file_storage_engine": settings.FILE_STORAGE_TYPE.upper(),
                "search_engine": "Elasticsearch" if es_available else "MISSING",
                "vector_search_engine": "Milvus" if milvus_available else "Elasticsearch (fallback)",
                "hybrid_search_enabled": settings.ELASTICSEARCH_HYBRID_SEARCH,
                "architecture_description": StorageDetector._get_architecture_description(strategy)
            },
            
            # 混合检索状态
            "hybrid_search_status": {
                "enabled": settings.ELASTICSEARCH_HYBRID_SEARCH,
                "forced_enabled": True,  # 混合检索是系统核心功能，强制启用
                "weight_config": {
                    "semantic_weight": settings.ELASTICSEARCH_HYBRID_WEIGHT,
                    "keyword_weight": 1.0 - settings.ELASTICSEARCH_HYBRID_WEIGHT
                },
                "optimization": "语义搜索优先，关键词搜索辅助",
                "recommendation": "混合检索是系统核心功能，建议保持启用状态"
            }
        }
    
    @staticmethod
    def _get_architecture_description(strategy: str) -> str:
        """获取架构描述"""
        descriptions = {
            "full_dual_storage_enhanced": "完整双存储引擎架构 - MinIO负责文件存储，Elasticsearch负责文档检索，Milvus提供增强向量搜索",
            "standard_dual_storage": "标准双存储引擎架构 - MinIO负责文件存储，Elasticsearch负责文档检索和向量搜索",
            "insufficient_storage": "存储架构不完整 - 缺少基础必需组件",
        }
        return descriptions.get(strategy, "未知架构配置")
    
    @staticmethod
    def get_system_requirements():
        """获取系统要求信息"""
        return {
            "core_requirements": [
                {
                    "name": "Elasticsearch", 
                    "critical": True,
                    "status": "required",
                    "description": "文档分片存储和混合检索引擎"
                },
                {
                    "name": "PostgreSQL", 
                    "critical": True,
                    "status": "required",
                    "description": "关系数据库"
                },
                {
                    "name": "Redis", 
                    "critical": True,
                    "status": "required",
                    "description": "缓存和会话存储"
                },
                {
                    "name": "RabbitMQ", 
                    "critical": True,
                    "status": "required",
                    "description": "消息队列"
                },
                {
                    "name": "File Storage", 
                    "critical": True,
                    "status": "required",
                    "description": "用户文件存储（本地或远程）"
                }
            ],
            "enhancement_requirements": [
                {
                    "name": "Milvus", 
                    "critical": False,
                    "status": "optional",
                    "description": "高性能向量搜索引擎"
                },
                {
                    "name": "MinIO", 
                    "critical": False,
                    "status": "optional",
                    "description": "Milvus存储后端或高级文件存储"
                },
                {
                    "name": "Nacos", 
                    "critical": False,
                    "status": "optional",
                    "description": "服务发现和配置中心"
                }
            ],
            "deployment_requirements": {
                "minimal": {
                    "core_services": ["PostgreSQL", "Elasticsearch", "Redis", "RabbitMQ"],
                    "file_storage": "local",
                    "vector_search": "elasticsearch_only",
                    "resource_requirements": {
                        "memory": "4GB",
                        "cpu": "2 cores",
                        "disk": "20GB"
                    }
                },
                "standard": {
                    "core_services": ["PostgreSQL", "Elasticsearch", "Redis", "RabbitMQ"],
                    "enhancement_services": ["Milvus", "MinIO", "etcd"],
                    "file_storage": "local_or_minio",
                    "vector_search": "milvus_primary",
                    "resource_requirements": {
                        "memory": "8GB",
                        "cpu": "4 cores", 
                        "disk": "50GB"
                    }
                },
                "production": {
                    "core_services": ["PostgreSQL", "Elasticsearch", "Redis", "RabbitMQ"],
                    "enhancement_services": ["Milvus", "MinIO", "etcd", "Nacos", "InfluxDB"],
                    "file_storage": "minio_recommended",
                    "vector_search": "milvus_primary",
                    "resource_requirements": {
                        "memory": "16GB+",
                        "cpu": "8+ cores",
                        "disk": "100GB+"
                    }
                }
            },
            "critical_warning": "Elasticsearch是系统核心组件，必须正常运行才能提供基本功能"
        }
    
    @staticmethod
    def validate_core_storage():
        """验证核心存储组件是否可用"""
        es_available = StorageDetector.check_elasticsearch()
        minio_available = StorageDetector.check_minio()
        
        validation_result = {
            "overall_status": "healthy" if (es_available and minio_available) else "critical",
            "core_components": {
                "elasticsearch": {
                    "status": "healthy" if es_available else "critical",
                    "message": "Elasticsearch可用" if es_available else "Elasticsearch不可用"
                },
                "minio": {
                    "status": "healthy" if minio_available else "critical", 
                    "message": "MinIO可用" if minio_available else "MinIO不可用"
                }
            },
            "recommendations": []
        }
        
        # 生成建议
        if not es_available:
            validation_result["recommendations"].append("请检查Elasticsearch服务状态并确保配置正确")
        if not minio_available:
            validation_result["recommendations"].append("请检查MinIO服务状态并确保配置正确")
        
        if es_available and minio_available:
            validation_result["recommendations"].append("核心存储组件状态良好，系统可以正常运行")
        
        return validation_result


# 用于向后兼容的别名
def get_storage_detector():
    """获取存储检测器实例"""
    return StorageDetector()

# 导出常用函数
__all__ = ["StorageDetector", "get_storage_detector"]
