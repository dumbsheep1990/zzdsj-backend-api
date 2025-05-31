"""
内存缓存模块
提供基于内存的缓存功能，支持LRU和TTL
"""

import time
import threading
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """LRU（最近最少使用）缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存大小
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self.lock:
            if key in self.cache:
                # 移动到最后（最近使用）
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self.lock:
            if key in self.cache:
                # 更新现有键
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # 移除最少使用的项
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        with self.lock:
            return key in self.cache
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def keys(self) -> list:
        """获取所有键"""
        with self.lock:
            return list(self.cache.keys())


class TTLCache:
    """支持TTL（生存时间）的缓存实现"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        初始化TTL缓存
        
        Args:
            default_ttl: 默认TTL（秒）
        """
        self.default_ttl = default_ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key: (value, expire_time)
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self.lock:
            if key in self.cache:
                value, expire_time = self.cache[key]
                if time.time() < expire_time:
                    return value
                else:
                    # 过期，删除
                    del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None使用默认值
        """
        ttl = ttl or self.default_ttl
        expire_time = time.time() + ttl
        
        with self.lock:
            self.cache[key] = (value, expire_time)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        return self.get(key) is not None
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余TTL（秒），-1表示不存在或已过期
        """
        with self.lock:
            if key in self.cache:
                _, expire_time = self.cache[key]
                remaining = int(expire_time - time.time())
                return max(0, remaining) if remaining > 0 else -1
            return -1
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        清理过期项
        
        Returns:
            清理的项目数量
        """
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, (_, expire_time) in self.cache.items():
                if current_time >= expire_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
        
        return len(expired_keys)
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def keys(self) -> list:
        """获取所有未过期的键"""
        current_time = time.time()
        valid_keys = []
        
        with self.lock:
            for key, (_, expire_time) in self.cache.items():
                if current_time < expire_time:
                    valid_keys.append(key)
        
        return valid_keys


class MemoryCache:
    """内存缓存管理器，结合LRU和TTL功能"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        初始化内存缓存
        
        Args:
            max_size: 最大缓存大小
            default_ttl: 默认TTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key: (value, expire_time)
        self.access_order = OrderedDict()  # 用于LRU
        self.lock = threading.RLock()
        
        # 启动后台清理线程
        self._start_cleanup_thread()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self.lock:
            if key in self.cache:
                value, expire_time = self.cache[key]
                if time.time() < expire_time:
                    # 更新访问顺序
                    self.access_order.move_to_end(key)
                    return value
                else:
                    # 过期，删除
                    self._remove_key(key)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None使用默认值
        """
        ttl = ttl or self.default_ttl
        expire_time = time.time() + ttl
        
        with self.lock:
            # 如果是新键且已达到最大大小，移除最少使用的项
            if key not in self.cache and len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = (value, expire_time)
            self.access_order[key] = None  # 添加到访问顺序末尾
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self.cache:
                self._remove_key(key)
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            键是否存在
        """
        return self.get(key) is not None
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余TTL（秒），-1表示不存在或已过期
        """
        with self.lock:
            if key in self.cache:
                _, expire_time = self.cache[key]
                remaining = int(expire_time - time.time())
                return max(0, remaining) if remaining > 0 else -1
            return -1
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def keys(self) -> list:
        """获取所有未过期的键"""
        current_time = time.time()
        valid_keys = []
        
        with self.lock:
            for key, (_, expire_time) in self.cache.items():
                if current_time < expire_time:
                    valid_keys.append(key)
        
        return valid_keys
    
    def stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            total_keys = len(self.cache)
            current_time = time.time()
            expired_count = 0
            
            for _, expire_time in self.cache.values():
                if current_time >= expire_time:
                    expired_count += 1
            
            return {
                "total_keys": total_keys,
                "valid_keys": total_keys - expired_count,
                "expired_keys": expired_count,
                "max_size": self.max_size,
                "usage_percent": (total_keys / self.max_size * 100) if self.max_size > 0 else 0
            }
    
    def _remove_key(self, key: str) -> None:
        """删除键（内部方法）"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            del self.access_order[key]
    
    def _evict_lru(self) -> None:
        """移除最少使用的项"""
        if self.access_order:
            lru_key = next(iter(self.access_order))
            self._remove_key(lru_key)
    
    def _cleanup_expired(self) -> int:
        """清理过期项"""
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, (_, expire_time) in self.cache.items():
                if current_time >= expire_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_key(key)
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")
        
        return len(expired_keys)
    
    def _start_cleanup_thread(self) -> None:
        """启动后台清理线程"""
        import threading
        
        def cleanup_worker():
            while True:
                try:
                    time.sleep(60)  # 每分钟清理一次
                    self._cleanup_expired()
                except Exception as e:
                    logger.error(f"缓存清理线程出错: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


# 全局内存缓存实例
_memory_cache = None


def get_memory_cache(max_size: int = None, default_ttl: int = None) -> MemoryCache:
    """
    获取全局内存缓存实例
    
    Args:
        max_size: 最大缓存大小
        default_ttl: 默认TTL
        
    Returns:
        内存缓存实例
    """
    global _memory_cache
    
    if _memory_cache is None:
        # 从配置获取默认值
        from app.utils.core.config import get_config
        
        max_size = max_size or get_config("cache", "memory", "max_size", default=1000)
        default_ttl = default_ttl or get_config("cache", "memory", "default_ttl", default=3600)
        
        _memory_cache = MemoryCache(max_size=max_size, default_ttl=default_ttl)
    
    return _memory_cache 