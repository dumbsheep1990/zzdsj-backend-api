"""
性能优化组件
提供缓存管理、并发控制、查询优化和性能监控功能，提升检索系统性能
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, TypeVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
from collections import defaultdict, OrderedDict
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheStrategy(str, Enum):
    """缓存策略"""
    LRU = "lru"  # 最近最少使用
    TTL = "ttl"  # 基于时间过期
    LFU = "lfu"  # 最少使用频率
    HYBRID = "hybrid"  # 混合策略


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    hit_rate: float = 0.0
    
    def calculate_hit_rate(self):
        """计算命中率"""
        total = self.hits + self.misses
        self.hit_rate = self.hits / total if total > 0 else 0.0


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)
    
    def touch(self):
        """更新访问信息"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class QueryProfile:
    """查询性能画像"""
    query_hash: str
    execution_count: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    last_executed: Optional[datetime] = None
    errors: int = 0
    
    def add_execution(self, duration: float, error: bool = False):
        """添加执行记录"""
        self.execution_count += 1
        self.total_duration += duration
        self.avg_duration = self.total_duration / self.execution_count
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.last_executed = datetime.now()
        if error:
            self.errors += 1


class SmartCache:
    """智能缓存系统"""
    
    def __init__(
        self, 
        max_size: int = 1000,
        default_ttl: int = 3600,
        strategy: CacheStrategy = CacheStrategy.HYBRID
    ):
        """
        初始化智能缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            strategy: 缓存策略
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats(max_size=max_size)
        self._lock = threading.RLock()
        
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                self._stats.calculate_hit_rate()
                return None
            
            # 检查过期
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                self._stats.size = len(self._cache)
                self._stats.calculate_hit_rate()
                return None
            
            # 更新访问信息
            entry.touch()
            
            # LRU策略：移到末尾
            if self.strategy in [CacheStrategy.LRU, CacheStrategy.HYBRID]:
                self._cache.move_to_end(key)
            
            self._stats.hits += 1
            self._stats.calculate_hit_rate()
            return entry.value
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        with self._lock:
            ttl = ttl or self.default_ttl
            
            # 创建新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl
            )
            
            # 如果已存在，更新
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
                return True
            
            # 检查容量限制
            if len(self._cache) >= self.max_size:
                await self._evict()
            
            # 添加新条目
            self._cache[key] = entry
            self._stats.size = len(self._cache)
            
            return True
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False
    
    async def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats(max_size=self.max_size)
    
    async def _evict(self):
        """缓存淘汰"""
        if not self._cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # 删除最少使用的
            self._cache.popitem(last=False)
        
        elif self.strategy == CacheStrategy.LFU:
            # 删除访问频率最低的
            min_access_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].access_count
            )
            del self._cache[min_access_key]
        
        elif self.strategy == CacheStrategy.TTL:
            # 删除最早的
            self._cache.popitem(last=False)
        
        elif self.strategy == CacheStrategy.HYBRID:
            # 混合策略：优先删除过期的，然后是访问频率低的
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]
            
            if expired_keys:
                del self._cache[expired_keys[0]]
            else:
                # 删除访问频率低且时间久的
                candidate_key = min(
                    self._cache.keys(),
                    key=lambda k: (
                        self._cache[k].access_count,
                        self._cache[k].last_accessed
                    )
                )
                del self._cache[candidate_key]
        
        self._stats.evictions += 1
        self._stats.size = len(self._cache)
    
    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        with self._lock:
            self._stats.size = len(self._cache)
            return self._stats


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        """初始化查询优化器"""
        self._query_profiles: Dict[str, QueryProfile] = {}
        self._optimization_rules: List[Callable] = []
        self._lock = threading.RLock()
    
    def add_optimization_rule(self, rule: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """添加优化规则"""
        self._optimization_rules.append(rule)
        logger.info(f"已添加查询优化规则: {rule.__name__}")
    
    async def optimize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """优化查询"""
        optimized_query = query.copy()
        
        # 应用所有优化规则
        for rule in self._optimization_rules:
            try:
                optimized_query = rule(optimized_query)
            except Exception as e:
                logger.error(f"查询优化规则执行失败: {str(e)}")
        
        return optimized_query
    
    async def profile_query(
        self, 
        query: Dict[str, Any], 
        duration: float, 
        error: bool = False
    ):
        """记录查询性能"""
        query_hash = self._hash_query(query)
        
        with self._lock:
            if query_hash not in self._query_profiles:
                self._query_profiles[query_hash] = QueryProfile(query_hash=query_hash)
            
            self._query_profiles[query_hash].add_execution(duration, error)
    
    def _hash_query(self, query: Dict[str, Any]) -> str:
        """生成查询哈希"""
        # 移除变化的字段（如时间戳）
        stable_query = {
            k: v for k, v in query.items() 
            if k not in ['timestamp', 'request_id']
        }
        query_str = json.dumps(stable_query, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def get_slow_queries(self, threshold: float = 1.0) -> List[QueryProfile]:
        """获取慢查询"""
        with self._lock:
            return [
                profile for profile in self._query_profiles.values()
                if profile.avg_duration > threshold
            ]
    
    def get_query_stats(self) -> Dict[str, Any]:
        """获取查询统计"""
        with self._lock:
            if not self._query_profiles:
                return {
                    "total_queries": 0,
                    "avg_duration": 0.0,
                    "slow_queries": 0,
                    "error_rate": 0.0
                }
            
            total_executions = sum(p.execution_count for p in self._query_profiles.values())
            total_duration = sum(p.total_duration for p in self._query_profiles.values())
            total_errors = sum(p.errors for p in self._query_profiles.values())
            
            avg_duration = total_duration / total_executions if total_executions > 0 else 0.0
            error_rate = total_errors / total_executions if total_executions > 0 else 0.0
            
            slow_queries = len([p for p in self._query_profiles.values() if p.avg_duration > 1.0])
            
            return {
                "total_queries": len(self._query_profiles),
                "total_executions": total_executions,
                "avg_duration": avg_duration,
                "slow_queries": slow_queries,
                "error_rate": error_rate
            }


class ConcurrencyController:
    """并发控制器"""
    
    def __init__(self, max_concurrent: int = 10):
        """
        初始化并发控制器
        
        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_stats = defaultdict(int)
        self._lock = asyncio.Lock()
    
    async def execute_with_concurrency_control(
        self, 
        task_id: str, 
        coro: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """在并发控制下执行任务"""
        async with self._semaphore:
            async with self._lock:
                if task_id in self._active_tasks:
                    # 如果同样的任务正在执行，等待其完成
                    return await self._active_tasks[task_id]
            
            # 创建新任务
            task = asyncio.create_task(coro(*args, **kwargs))
            
            async with self._lock:
                self._active_tasks[task_id] = task
                self._task_stats[task_id] += 1
            
            try:
                result = await task
                return result
            finally:
                async with self._lock:
                    self._active_tasks.pop(task_id, None)
    
    def get_concurrency_stats(self) -> Dict[str, Any]:
        """获取并发统计"""
        return {
            "max_concurrent": self.max_concurrent,
            "active_tasks": len(self._active_tasks),
            "available_slots": self._semaphore._value,
            "task_execution_counts": dict(self._task_stats)
        }


class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(
        self,
        cache_size: int = 1000,
        cache_ttl: int = 3600,
        max_concurrent: int = 10
    ):
        """
        初始化性能优化器
        
        Args:
            cache_size: 缓存大小
            cache_ttl: 缓存TTL
            max_concurrent: 最大并发数
        """
        self.cache = SmartCache(cache_size, cache_ttl)
        self.query_optimizer = QueryOptimizer()
        self.concurrency_controller = ConcurrencyController(max_concurrent)
        
        # 注册默认优化规则
        self._register_default_optimization_rules()
    
    def _register_default_optimization_rules(self):
        """注册默认优化规则"""
        
        def limit_optimization_rule(query: Dict[str, Any]) -> Dict[str, Any]:
            """限制优化规则"""
            # 确保查询有合理的限制
            if 'limit' not in query or query['limit'] > 100:
                query['limit'] = 100
            return query
        
        def field_selection_rule(query: Dict[str, Any]) -> Dict[str, Any]:
            """字段选择优化"""
            # 如果没有指定字段，添加常用字段
            if 'fields' not in query:
                query['fields'] = ['id', 'content', 'metadata', 'score']
            return query
        
        def cache_key_rule(query: Dict[str, Any]) -> Dict[str, Any]:
            """缓存键优化"""
            # 标准化查询键的顺序
            if 'sort' in query and isinstance(query['sort'], list):
                query['sort'] = sorted(query['sort'])
            return query
        
        self.query_optimizer.add_optimization_rule(limit_optimization_rule)
        self.query_optimizer.add_optimization_rule(field_selection_rule)
        self.query_optimizer.add_optimization_rule(cache_key_rule)
    
    async def cached_search(
        self,
        cache_key: str,
        search_func: Callable,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """带缓存的搜索"""
        # 尝试从缓存获取
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"缓存命中: {cache_key}")
            return cached_result
        
        # 缓存未命中，执行实际搜索
        start_time = time.time()
        try:
            result = await search_func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 缓存结果
            await self.cache.set(cache_key, result, ttl)
            
            # 记录性能
            await self.query_optimizer.profile_query(
                {'cache_key': cache_key}, duration
            )
            
            logger.debug(f"搜索完成并缓存: {cache_key}, 耗时: {duration:.3f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            await self.query_optimizer.profile_query(
                {'cache_key': cache_key}, duration, error=True
            )
            raise
    
    def _generate_cache_key(self, query: Dict[str, Any]) -> str:
        """生成缓存键"""
        query_str = json.dumps(query, sort_keys=True)
        return f"search_{hashlib.md5(query_str.encode()).hexdigest()}"
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "cache_stats": self.cache.get_stats().__dict__,
            "query_stats": self.query_optimizer.get_query_stats(),
            "concurrency_stats": self.concurrency_controller.get_concurrency_stats(),
            "slow_queries": [
                {
                    "query_hash": q.query_hash,
                    "avg_duration": q.avg_duration,
                    "execution_count": q.execution_count,
                    "error_rate": q.errors / q.execution_count if q.execution_count > 0 else 0
                }
                for q in self.query_optimizer.get_slow_queries()
            ]
        }


# 全局性能优化器实例
_performance_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取性能优化器实例"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


def performance_optimized(cache_ttl: Optional[int] = None):
    """性能优化装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args, **kwargs) -> T:
            optimizer = get_performance_optimizer()
            
            # 生成缓存键
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            return await optimizer.cached_search(
                cache_key, func, *args, ttl=cache_ttl, **kwargs
            )
        
        return wrapper
    return decorator 