"""
缓存核心模块
提供Redis缓存、异步Redis缓存和内存缓存的统一接口
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

# 核心组件导入
from .redis_client import (
    RedisClient,
    get_redis_client
)

from .memory_cache import (
    LRUCache,
    TTLCache,
    MemoryCache,
    get_memory_cache
)

try:
    from .async_redis import (
        AsyncRedisClient,
        get_async_redis_client
    )
except ImportError:
    # 如果异步Redis模块不可用
    AsyncRedisClient = None
    get_async_redis_client = None

logger = logging.getLogger(__name__)

# 导出所有公共接口
__all__ = [
    # Redis缓存
    "RedisClient",
    "get_redis_client",
    
    # 内存缓存
    "LRUCache",
    "TTLCache", 
    "MemoryCache",
    "get_memory_cache",
    
    # 缓存管理器
    "CacheManager",
    "get_cache_manager",
    "create_cache_manager",
    "get_cache_client",
]

# 如果异步Redis可用，添加到导出列表
if AsyncRedisClient is not None:
    __all__.extend([
        "AsyncRedisClient",
        "get_async_redis_client"
    ])


def get_cache_client(cache_type: str = "redis", **kwargs):
    """
    获取缓存客户端的便捷函数
    
    Args:
        cache_type: 缓存类型 ("redis", "memory", "async_redis")
        **kwargs: 初始化参数
        
    Returns:
        缓存客户端实例
        
    Raises:
        ValueError: 不支持的缓存类型
    """
    if cache_type == "redis":
        return get_redis_client(**kwargs)
    elif cache_type == "memory":
        return get_memory_cache(**kwargs)
    elif cache_type == "async_redis" and AsyncRedisClient is not None:
        return get_async_redis_client(**kwargs)
    else:
        raise ValueError(f"不支持的缓存类型: {cache_type}")


def create_cache_manager():
    """
    创建缓存管理器，根据配置自动选择缓存类型
    
    Returns:
        缓存管理器实例
    """
    try:
        from app.utils.core.config import get_config
        cache_config = get_config("cache", default={})
    except ImportError:
        cache_config = {}
    
    # 检查Redis配置
    redis_config = cache_config.get("redis", {})
    if redis_config.get("enabled", True):
        try:
            # 尝试创建Redis客户端
            redis_client = get_redis_client()
            if redis_client.health_check():
                logger.info("使用Redis作为主缓存，内存缓存作为备用")
                return CacheManager(primary=redis_client, fallback=get_memory_cache())
        except Exception as e:
            logger.warning(f"Redis连接失败，使用内存缓存: {str(e)}")
    
    # 回退到内存缓存
    logger.info("使用内存缓存")
    return CacheManager(primary=get_memory_cache())


class CacheManager:
    """缓存管理器，支持主缓存和备用缓存"""
    
    def __init__(self, primary, fallback=None):
        """
        初始化缓存管理器
        
        Args:
            primary: 主缓存客户端
            fallback: 备用缓存客户端
        """
        self.primary = primary
        self.fallback = fallback
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        self.logger.info(f"缓存管理器初始化完成，主缓存: {type(primary).__name__}, "
                        f"备用缓存: {type(fallback).__name__ if fallback else None}")
    
    def get(self, key: str, default=None):
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            缓存值或默认值
        """
        if not key:
            self.logger.warning("尝试获取空键的缓存")
            return default
            
        try:
            # 首先尝试从主缓存获取
            value = self.primary.get(key)
            if value is not None:
                self._stats["hits"] += 1
                self.logger.debug(f"主缓存命中: {key}")
                return value
        except Exception as e:
            self.logger.error(f"主缓存获取失败 {key}: {str(e)}")
            self._stats["errors"] += 1
        
        # 尝试从备用缓存获取
        if self.fallback:
            try:
                value = self.fallback.get(key)
                if value is not None:
                    self._stats["hits"] += 1
                    self.logger.debug(f"备用缓存命中: {key}")
                    
                    # 回写到主缓存
                    try:
                        self.primary.set(key, value)
                        self.logger.debug(f"回写主缓存: {key}")
                    except Exception:
                        pass
                    
                    return value
            except Exception as e:
                self.logger.error(f"备用缓存获取失败 {key}: {str(e)}")
                self._stats["errors"] += 1
        
        self._stats["misses"] += 1
        self.logger.debug(f"缓存未命中: {key}")
        return default
    
    def get_json(self, key: str, default=None):
        """
        获取JSON格式的缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            解析后的JSON对象或默认值
        """
        if hasattr(self.primary, 'get_json'):
            try:
                value = self.primary.get_json(key)
                if value is not None:
                    self._stats["hits"] += 1
                    return value
            except Exception as e:
                self.logger.error(f"主缓存JSON获取失败 {key}: {str(e)}")
                self._stats["errors"] += 1
        
        # 备用缓存处理
        if self.fallback and hasattr(self.fallback, 'get_json'):
            try:
                return self.fallback.get_json(key, default)
            except Exception as e:
                self.logger.error(f"备用缓存JSON获取失败 {key}: {str(e)}")
                self._stats["errors"] += 1
        
        self._stats["misses"] += 1
        return default
    
    def set(self, key: str, value, ttl=None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            
        Returns:
            操作是否成功
        """
        if not key:
            self.logger.warning("尝试设置空键的缓存")
            return False
            
        primary_success = False
        fallback_success = False
        
        # 设置主缓存
        try:
            if hasattr(self.primary, 'set_json') and isinstance(value, (dict, list)):
                primary_success = self.primary.set_json(key, value, ttl)
            else:
                primary_success = self.primary.set(key, value, ttl)
            
            if primary_success:
                self.logger.debug(f"主缓存设置成功: {key}")
        except Exception as e:
            self.logger.error(f"主缓存设置失败 {key}: {str(e)}")
            self._stats["errors"] += 1
        
        # 设置备用缓存
        if self.fallback:
            try:
                if hasattr(self.fallback, 'set_json') and isinstance(value, (dict, list)):
                    fallback_success = self.fallback.set_json(key, value, ttl)
                elif hasattr(self.fallback, 'set'):
                    fallback_success = self.fallback.set(key, value, ttl)
                
                if fallback_success:
                    self.logger.debug(f"备用缓存设置成功: {key}")
            except Exception as e:
                self.logger.error(f"备用缓存设置失败 {key}: {str(e)}")
                self._stats["errors"] += 1
        
        success = primary_success or fallback_success
        if success:
            self._stats["sets"] += 1
        
        return success
    
    def set_json(self, key: str, value: Union[dict, list], ttl=None):
        """
        设置JSON格式的缓存值
        
        Args:
            key: 缓存键
            value: JSON对象
            ttl: 过期时间（秒）
            
        Returns:
            操作是否成功
        """
        return self.set(key, value, ttl)
    
    def set_many(self, mapping: Dict[str, Any], ttl=None):
        """
        批量设置缓存值
        
        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒）
            
        Returns:
            设置成功的键列表
        """
        success_keys = []
        
        for key, value in mapping.items():
            if self.set(key, value, ttl):
                success_keys.append(key)
        
        self.logger.info(f"批量设置缓存: {len(success_keys)}/{len(mapping)} 成功")
        return success_keys
    
    def delete(self, key: str):
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            操作是否成功
        """
        if not key:
            self.logger.warning("尝试删除空键的缓存")
            return False
            
        primary_success = False
        fallback_success = False
        
        # 删除主缓存
        try:
            primary_success = bool(self.primary.delete(key))
            if primary_success:
                self.logger.debug(f"主缓存删除成功: {key}")
        except Exception as e:
            self.logger.error(f"主缓存删除失败 {key}: {str(e)}")
            self._stats["errors"] += 1
        
        # 删除备用缓存
        if self.fallback:
            try:
                fallback_success = bool(self.fallback.delete(key))
                if fallback_success:
                    self.logger.debug(f"备用缓存删除成功: {key}")
            except Exception as e:
                self.logger.error(f"备用缓存删除失败 {key}: {str(e)}")
                self._stats["errors"] += 1
        
        success = primary_success or fallback_success
        if success:
            self._stats["deletes"] += 1
        
        return success
    
    def delete_many(self, keys: List[str]):
        """
        批量删除缓存项
        
        Args:
            keys: 缓存键列表
            
        Returns:
            删除成功的键列表
        """
        success_keys = []
        
        for key in keys:
            if self.delete(key):
                success_keys.append(key)
        
        self.logger.info(f"批量删除缓存: {len(success_keys)}/{len(keys)} 成功")
        return success_keys
    
    def exists(self, key: str):
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        if not key:
            return False
            
        try:
            if self.primary.exists(key):
                return True
        except Exception as e:
            self.logger.error(f"主缓存存在检查失败 {key}: {str(e)}")
            self._stats["errors"] += 1
        
        if self.fallback:
            try:
                return self.fallback.exists(key)
            except Exception as e:
                self.logger.error(f"备用缓存存在检查失败 {key}: {str(e)}")
                self._stats["errors"] += 1
        
        return False
    
    def clear(self, pattern: str = None):
        """
        清空缓存
        
        Args:
            pattern: 键的模式，如果指定则只清空匹配的键
        """
        try:
            if pattern:
                # 模式清空
                if hasattr(self.primary, 'delete_pattern'):
                    self.primary.delete_pattern(pattern)
                    self.logger.info(f"主缓存模式清空: {pattern}")
                else:
                    self.logger.warning("主缓存不支持模式清空")
            else:
                # 全部清空
                if hasattr(self.primary, 'flushdb'):
                    self.primary.flushdb()
                    self.logger.info("主缓存已清空")
                elif hasattr(self.primary, 'clear'):
                    self.primary.clear()
                    self.logger.info("主缓存已清空")
        except Exception as e:
            self.logger.error(f"主缓存清空失败: {str(e)}")
            self._stats["errors"] += 1
        
        if self.fallback:
            try:
                if pattern and hasattr(self.fallback, 'delete_pattern'):
                    self.fallback.delete_pattern(pattern)
                    self.logger.info(f"备用缓存模式清空: {pattern}")
                elif hasattr(self.fallback, 'clear'):
                    self.fallback.clear()
                    self.logger.info("备用缓存已清空")
            except Exception as e:
                self.logger.error(f"备用缓存清空失败: {str(e)}")
                self._stats["errors"] += 1
    
    def get_ttl(self, key: str):
        """
        获取键的剩余过期时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余过期时间（秒），-1表示永不过期，None表示键不存在
        """
        try:
            if hasattr(self.primary, 'ttl'):
                return self.primary.ttl(key)
        except Exception as e:
            self.logger.error(f"获取TTL失败 {key}: {str(e)}")
        
        return None
    
    def expire(self, key: str, seconds: int):
        """
        设置键的过期时间
        
        Args:
            key: 缓存键
            seconds: 过期时间（秒）
            
        Returns:
            操作是否成功
        """
        try:
            if hasattr(self.primary, 'expire'):
                return self.primary.expire(key, seconds)
        except Exception as e:
            self.logger.error(f"设置过期时间失败 {key}: {str(e)}")
        
        return False
    
    def health_check(self):
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        primary_healthy = False
        fallback_healthy = False
        
        # 检查主缓存健康状态
        try:
            if hasattr(self.primary, 'health_check'):
                primary_healthy = self.primary.health_check()
            else:
                # 简单的连通性测试
                test_key = f"health_check_{datetime.now().timestamp()}"
                primary_healthy = self.primary.set(test_key, "test", 1) and self.primary.delete(test_key)
        except Exception as e:
            self.logger.error(f"主缓存健康检查失败: {str(e)}")
            primary_healthy = False
        
        # 检查备用缓存健康状态
        if self.fallback:
            try:
                if hasattr(self.fallback, 'health_check'):
                    fallback_healthy = self.fallback.health_check()
                else:
                    # 内存缓存假设总是健康的
                    fallback_healthy = True
            except Exception as e:
                self.logger.error(f"备用缓存健康检查失败: {str(e)}")
                fallback_healthy = False
        
        overall_healthy = primary_healthy or fallback_healthy
        
        health_info = {
            "primary_healthy": primary_healthy,
            "fallback_healthy": fallback_healthy,
            "overall_healthy": overall_healthy,
            "primary_type": type(self.primary).__name__,
            "fallback_type": type(self.fallback).__name__ if self.fallback else None,
            "last_check": datetime.now().isoformat(),
            "stats": self.get_stats()
        }
        
        if not overall_healthy:
            self.logger.warning("缓存系统健康检查失败")
        
        return health_info
    
    def get_stats(self):
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_operations = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_operations * 100) if total_operations > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "errors": self._stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "total_operations": total_operations
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        self.logger.info("缓存统计信息已重置")


# 全局缓存管理器实例
_cache_manager = None


def get_cache_manager():
    """
    获取全局缓存管理器实例
    
    Returns:
        缓存管理器实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = create_cache_manager()
    return _cache_manager
