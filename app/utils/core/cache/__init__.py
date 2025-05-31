"""
缓存核心模块
提供Redis缓存、异步Redis缓存和内存缓存的统一接口
"""

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
]

# 如果异步Redis可用，添加到导出列表
if AsyncRedisClient is not None:
    __all__.extend([
        "AsyncRedisClient",
        "get_async_redis_client"
    ])

# 便捷函数
def get_cache_client(cache_type: str = "redis", **kwargs):
    """
    获取缓存客户端的便捷函数
    
    Args:
        cache_type: 缓存类型 ("redis", "memory", "async_redis")
        **kwargs: 初始化参数
        
    Returns:
        缓存客户端实例
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
    from app.utils.core.config import get_config
    
    cache_config = get_config("cache", default={})
    
    # 检查Redis配置
    redis_config = cache_config.get("redis", {})
    if redis_config.get("enabled", True):
        try:
            # 尝试创建Redis客户端
            redis_client = get_redis_client()
            if redis_client.health_check():
                return CacheManager(primary=redis_client, fallback=get_memory_cache())
        except Exception:
            pass
    
    # 回退到内存缓存
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
    
    def get(self, key: str):
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        try:
            value = self.primary.get(key)
            if value is not None:
                return value
        except Exception:
            pass
        
        if self.fallback:
            try:
                return self.fallback.get(key)
            except Exception:
                pass
        
        return None
    
    def set(self, key: str, value, ttl=None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间
            
        Returns:
            操作是否成功
        """
        success = False
        
        try:
            if hasattr(self.primary, 'set_json'):
                success = self.primary.set_json(key, value, ttl)
            else:
                success = self.primary.set(key, value, ttl)
        except Exception:
            pass
        
        if self.fallback and not success:
            try:
                if hasattr(self.fallback, 'set'):
                    return self.fallback.set(key, value, ttl)
            except Exception:
                pass
        
        return success
    
    def delete(self, key: str):
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            操作是否成功
        """
        success = False
        
        try:
            success = bool(self.primary.delete(key))
        except Exception:
            pass
        
        if self.fallback:
            try:
                fallback_success = self.fallback.delete(key)
                success = success or fallback_success
            except Exception:
                pass
        
        return success
    
    def exists(self, key: str):
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        try:
            if self.primary.exists(key):
                return True
        except Exception:
            pass
        
        if self.fallback:
            try:
                return self.fallback.exists(key)
            except Exception:
                pass
        
        return False
    
    def clear(self):
        """清空所有缓存"""
        try:
            if hasattr(self.primary, 'flushdb'):
                self.primary.flushdb()
            elif hasattr(self.primary, 'clear'):
                self.primary.clear()
        except Exception:
            pass
        
        if self.fallback:
            try:
                self.fallback.clear()
            except Exception:
                pass
    
    def health_check(self):
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        primary_healthy = False
        fallback_healthy = False
        
        try:
            primary_healthy = self.primary.health_check()
        except Exception:
            pass
        
        if self.fallback:
            try:
                fallback_healthy = hasattr(self.fallback, 'health_check') and self.fallback.health_check()
            except Exception:
                fallback_healthy = True  # 内存缓存假设总是健康的
        
        return {
            "primary_healthy": primary_healthy,
            "fallback_healthy": fallback_healthy,
            "overall_healthy": primary_healthy or fallback_healthy
        }


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
