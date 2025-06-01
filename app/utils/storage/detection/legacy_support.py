"""
存储检测向后兼容支持
保持原有接口不变，内部使用新架构实现
"""

import logging
from .detector import StorageDetector, detect_storage_type, get_storage_config
from ..core.config import create_config_from_settings

logger = logging.getLogger(__name__)

# 全局检测器实例，保持与原接口兼容
_global_detector = None


def _get_detector():
    """获取全局检测器实例"""
    global _global_detector
    
    if _global_detector is None:
        try:
            # 尝试导入settings
            from app.config import settings
            
            # 创建配置
            config = create_config_from_settings(settings).to_dict()
            
            # 创建检测器
            _global_detector = StorageDetector("global", config)
            
            # 异步初始化
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_global_detector.initialize())
                else:
                    loop.run_until_complete(_global_detector.initialize())
            except RuntimeError:
                asyncio.run(_global_detector.initialize())
            
        except Exception as e:
            logger.error(f"存储检测器创建失败: {str(e)}")
            # 创建默认检测器
            _global_detector = StorageDetector("global")
    
    return _global_detector


def check_elasticsearch():
    """
    检查Elasticsearch是否可用
    保持与原接口兼容
    """
    try:
        detector = _get_detector()
        
        # 异步检测
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，返回缓存结果或默认值
                status = detector.get_engine_status("elasticsearch")
                return status.get("available", False) if status else False
            else:
                loop.run_until_complete(detector.detect_all_storage_engines())
                return detector.is_engine_available("elasticsearch")
        except RuntimeError:
            asyncio.run(detector.detect_all_storage_engines())
            return detector.is_engine_available("elasticsearch")
        
    except Exception as e:
        logger.warning(f"Elasticsearch检测失败: {str(e)}")
        return False


def check_milvus():
    """
    检查Milvus是否可用
    保持与原接口兼容
    """
    try:
        detector = _get_detector()
        
        # 异步检测
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，返回缓存结果或默认值
                status = detector.get_engine_status("milvus")
                return status.get("available", False) if status else False
            else:
                loop.run_until_complete(detector.detect_all_storage_engines())
                return detector.is_engine_available("milvus")
        except RuntimeError:
            asyncio.run(detector.detect_all_storage_engines())
            return detector.is_engine_available("milvus")
        
    except Exception as e:
        logger.warning(f"Milvus检测失败: {str(e)}")
        return False


def determine_storage_strategy():
    """
    基于可用存储引擎确定最佳存储策略
    保持与原接口兼容
    """
    try:
        detector = _get_detector()
        
        # 异步确定策略
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，返回简化的策略
                es_available = check_elasticsearch()
                milvus_available = check_milvus()
                
                if es_available and milvus_available:
                    return "hybrid"
                elif es_available:
                    return "elasticsearch"
                elif milvus_available:
                    return "milvus"
                else:
                    return "database"
            else:
                result = loop.run_until_complete(detector.determine_best_storage_strategy())
                return result.get("strategy", "database")
        except RuntimeError:
            result = asyncio.run(detector.determine_best_storage_strategy())
            return result.get("strategy", "database")
        
    except Exception as e:
        logger.error(f"存储策略确定失败: {str(e)}")
        return "database"


def get_vector_store_info():
    """
    获取向量存储详细信息
    保持与原接口兼容
    """
    try:
        detector = _get_detector()
        
        # 异步获取信息
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，返回简化的信息
                strategy = determine_storage_strategy()
                es_available = check_elasticsearch()
                milvus_available = check_milvus()
                
                # 尝试导入settings获取配置
                try:
                    from app.config import settings
                    return {
                        "strategy": strategy,
                        "elasticsearch": {
                            "available": es_available,
                            "url": getattr(settings, 'ELASTICSEARCH_URL', ''),
                            "index": getattr(settings, 'ELASTICSEARCH_INDEX', ''),
                            "hybrid_search": getattr(settings, 'ELASTICSEARCH_HYBRID_SEARCH', True),
                            "hybrid_weight": getattr(settings, 'ELASTICSEARCH_HYBRID_WEIGHT', 0.5)
                        },
                        "milvus": {
                            "available": milvus_available,
                            "host": getattr(settings, 'MILVUS_HOST', ''),
                            "port": getattr(settings, 'MILVUS_PORT', 19530),
                            "collection": getattr(settings, 'MILVUS_COLLECTION', '')
                        }
                    }
                except ImportError:
                    return {"strategy": strategy, "elasticsearch": {}, "milvus": {}}
            else:
                strategy_result = loop.run_until_complete(detector.determine_best_storage_strategy())
                engine_results = strategy_result.get("available_engines", {})
                
                # 格式化为原始格式
                info = {
                    "strategy": strategy_result.get("strategy", "database"),
                    "elasticsearch": {
                        "available": engine_results.get("elasticsearch", {}).get("available", False),
                    },
                    "milvus": {
                        "available": engine_results.get("milvus", {}).get("available", False),
                    }
                }
                
                # 添加配置信息
                es_config = engine_results.get("elasticsearch", {}).get("config", {})
                milvus_config = engine_results.get("milvus", {}).get("config", {})
                
                info["elasticsearch"].update(es_config)
                info["milvus"].update(milvus_config)
                
                return info
                
        except RuntimeError:
            strategy_result = asyncio.run(detector.determine_best_storage_strategy())
            engine_results = strategy_result.get("available_engines", {})
            
            info = {
                "strategy": strategy_result.get("strategy", "database"),
                "elasticsearch": engine_results.get("elasticsearch", {}).get("config", {}),
                "milvus": engine_results.get("milvus", {}).get("config", {})
            }
            
            # 添加可用性信息
            info["elasticsearch"]["available"] = engine_results.get("elasticsearch", {}).get("available", False)
            info["milvus"]["available"] = engine_results.get("milvus", {}).get("available", False)
            
            return info
        
    except Exception as e:
        logger.error(f"获取向量存储信息失败: {str(e)}")
        return {
            "strategy": "database",
            "elasticsearch": {"available": False},
            "milvus": {"available": False}
        } 