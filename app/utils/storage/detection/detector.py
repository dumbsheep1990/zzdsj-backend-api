"""
存储检测器实现
基于新架构的存储引擎检测
"""

from typing import Dict, List, Any, Optional
import logging
import os
from ..core.base import StorageComponent
from ..core.exceptions import StorageError, ConnectionError

logger = logging.getLogger(__name__)


class StorageDetector(StorageComponent):
    """
    存储引擎检测器
    自动识别和管理不同存储引擎的可用性
    """
    
    def __init__(self, name: str = "detector", config: Optional[Dict[str, Any]] = None):
        """
        初始化存储检测器
        
        参数:
            name: 检测器名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._detection_results = {}
        self._supported_engines = ["milvus", "elasticsearch", "minio", "database"]
    
    async def initialize(self) -> None:
        """初始化检测器"""
        if self._initialized:
            return
        
        self._initialized = True
        self.logger.info("存储检测器初始化完成")
    
    async def connect(self) -> bool:
        """建立连接（检测器不需要连接）"""
        return True
    
    async def disconnect(self) -> None:
        """断开连接（检测器不需要断开）"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 重新检测所有存储引擎
            await self.detect_all_storage_engines()
            return True
        except Exception as e:
            self.logger.error(f"存储检测器健康检查失败: {str(e)}")
            return False
    
    async def detect_all_storage_engines(self) -> Dict[str, Dict[str, Any]]:
        """检测所有支持的存储引擎"""
        results = {}
        
        for engine in self._supported_engines:
            try:
                detection_result = await self._detect_engine(engine)
                results[engine] = detection_result
                self._detection_results[engine] = detection_result
            except Exception as e:
                self.logger.warning(f"检测存储引擎 {engine} 失败: {str(e)}")
                results[engine] = {
                    "available": False,
                    "error": str(e),
                    "config": {}
                }
        
        self.logger.info(f"存储引擎检测完成: {results}")
        return results
    
    async def _detect_engine(self, engine: str) -> Dict[str, Any]:
        """检测单个存储引擎"""
        if engine == "milvus":
            return await self._detect_milvus()
        elif engine == "elasticsearch":
            return await self._detect_elasticsearch()
        elif engine == "minio":
            return await self._detect_minio()
        elif engine == "database":
            return await self._detect_database()
        else:
            raise StorageError(f"不支持的存储引擎: {engine}")
    
    async def _detect_milvus(self) -> Dict[str, Any]:
        """检测Milvus可用性"""
        try:
            # 检查环境变量禁用
            if os.getenv("MILVUS_ENABLED", "").lower() == "false":
                return {"available": False, "reason": "环境变量禁用", "config": {}}
            
            # 检查配置
            host = self.get_config("vector_store_host", "localhost")
            port = self.get_config("vector_store_port", 19530)
            
            if not host or not port:
                return {"available": False, "reason": "配置缺失", "config": {}}
            
            # 尝试导入和连接
            try:
                from pymilvus import connections, utility
                
                alias = f"detect_{self.name}"
                connections.connect(alias=alias, host=host, port=port)
                
                # 测试连接
                utility.list_collections(using=alias)
                
                # 清理连接
                connections.disconnect(alias)
                
                return {
                    "available": True,
                    "config": {
                        "host": host,
                        "port": port,
                        "collection": self.get_config("vector_store_collection", "default_collection")
                    }
                }
                
            except ImportError:
                return {"available": False, "reason": "依赖库未安装", "config": {}}
            except Exception as e:
                return {"available": False, "reason": f"连接失败: {str(e)}", "config": {}}
            
        except Exception as e:
            return {"available": False, "reason": f"检测异常: {str(e)}", "config": {}}
    
    async def _detect_elasticsearch(self) -> Dict[str, Any]:
        """检测Elasticsearch可用性"""
        try:
            # 检查环境变量禁用
            if os.getenv("ELASTICSEARCH_ENABLED", "").lower() == "false":
                return {"available": False, "reason": "环境变量禁用", "config": {}}
            
            # 检查配置
            url = self.get_config("elasticsearch_url", "")
            if not url:
                return {"available": False, "reason": "URL未配置", "config": {}}
            
            # 尝试导入和连接
            try:
                from elasticsearch import Elasticsearch
                
                # 构建连接参数
                es_kwargs = {}
                username = self.get_config("elasticsearch_username")
                password = self.get_config("elasticsearch_password")
                api_key = self.get_config("elasticsearch_api_key")
                
                if username and password:
                    es_kwargs["basic_auth"] = (username, password)
                if api_key:
                    es_kwargs["api_key"] = api_key
                
                # 创建客户端并测试
                es = Elasticsearch(url, **es_kwargs)
                health = es.cluster.health()
                
                return {
                    "available": True,
                    "config": {
                        "url": url,
                        "status": health.get("status"),
                        "index": self.get_config("elasticsearch_index", "default_index")
                    }
                }
                
            except ImportError:
                return {"available": False, "reason": "依赖库未安装", "config": {}}
            except Exception as e:
                return {"available": False, "reason": f"连接失败: {str(e)}", "config": {}}
            
        except Exception as e:
            return {"available": False, "reason": f"检测异常: {str(e)}", "config": {}}
    
    async def _detect_minio(self) -> Dict[str, Any]:
        """检测MinIO可用性"""
        try:
            # 检查配置
            endpoint = self.get_config("object_store_endpoint", "localhost:9000")
            access_key = self.get_config("object_store_access_key", "")
            secret_key = self.get_config("object_store_secret_key", "")
            
            if not endpoint:
                return {"available": False, "reason": "端点未配置", "config": {}}
            
            # 尝试导入和连接
            try:
                from minio import Minio
                
                client = Minio(
                    endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=self.get_config("object_store_secure", False)
                )
                
                # 测试连接
                list(client.list_buckets())
                
                return {
                    "available": True,
                    "config": {
                        "endpoint": endpoint,
                        "bucket": self.get_config("object_store_bucket", "default-bucket"),
                        "secure": self.get_config("object_store_secure", False)
                    }
                }
                
            except ImportError:
                return {"available": False, "reason": "依赖库未安装", "config": {}}
            except Exception as e:
                return {"available": False, "reason": f"连接失败: {str(e)}", "config": {}}
            
        except Exception as e:
            return {"available": False, "reason": f"检测异常: {str(e)}", "config": {}}
    
    async def _detect_database(self) -> Dict[str, Any]:
        """检测数据库可用性"""
        # 数据库总是可用的，作为fallback
        return {
            "available": True,
            "config": {
                "type": "database",
                "note": "fallback storage option"
            }
        }
    
    async def determine_best_storage_strategy(self) -> Dict[str, Any]:
        """确定最佳存储策略"""
        if not self._detection_results:
            await self.detect_all_storage_engines()
        
        # 检查环境变量或配置中的强制策略
        forced_strategy = os.getenv("SEARCH_STORAGE_STRATEGY", "").lower()
        if forced_strategy and forced_strategy != "auto":
            return {
                "strategy": forced_strategy,
                "reason": "环境变量强制指定",
                "available_engines": self._detection_results
            }
        
        config_strategy = self.get_config("search_storage_strategy", "auto").lower()
        if config_strategy and config_strategy != "auto":
            return {
                "strategy": config_strategy,
                "reason": "配置文件指定",
                "available_engines": self._detection_results
            }
        
        # 自动确定策略
        milvus_available = self._detection_results.get("milvus", {}).get("available", False)
        es_available = self._detection_results.get("elasticsearch", {}).get("available", False)
        
        if milvus_available and es_available:
            strategy = "hybrid"
            reason = "Milvus和Elasticsearch都可用，使用混合策略"
        elif milvus_available:
            strategy = "milvus"
            reason = "仅Milvus可用"
        elif es_available:
            strategy = "elasticsearch"
            reason = "仅Elasticsearch可用"
        else:
            strategy = "database"
            reason = "向量存储不可用，降级到数据库"
        
        return {
            "strategy": strategy,
            "reason": reason,
            "available_engines": self._detection_results
        }
    
    def get_engine_status(self, engine: str) -> Optional[Dict[str, Any]]:
        """获取特定引擎的状态"""
        return self._detection_results.get(engine)
    
    def is_engine_available(self, engine: str) -> bool:
        """检查特定引擎是否可用"""
        status = self.get_engine_status(engine)
        return status.get("available", False) if status else False


# 全局检测器实例
_global_detector: Optional[StorageDetector] = None


async def detect_storage_type(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    检测存储类型的便捷函数
    
    参数:
        config: 配置参数
        
    返回:
        检测结果
    """
    global _global_detector
    
    if _global_detector is None or config is not None:
        _global_detector = StorageDetector("global", config)
        await _global_detector.initialize()
    
    return await _global_detector.determine_best_storage_strategy()


async def get_storage_config() -> Dict[str, Any]:
    """
    获取存储配置的便捷函数
    
    返回:
        存储配置信息
    """
    global _global_detector
    
    if _global_detector is None:
        _global_detector = StorageDetector("global")
        await _global_detector.initialize()
    
    return await _global_detector.detect_all_storage_engines() 