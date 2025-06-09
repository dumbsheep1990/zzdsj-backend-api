"""
性能优化器
提供多级缓存、查询优化、并发控制和性能监控
"""

import asyncio
import logging
import time
import hashlib
import json
import pickle
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque, OrderedDict
import threading
import weakref
import statistics

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """缓存策略"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    TTL = "ttl"           # 时间到期
    HYBRID = "hybrid"     # 混合策略


class QueryOptimizationLevel(str, Enum):
    """查询优化级别"""
    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"


@dataclass
class CacheConfig:
    """缓存配置"""
    strategy: CacheStrategy = CacheStrategy.LRU
    max_size: int = 1000
    ttl_seconds: int = 3600
    enable_compression: bool = True
    enable_serialization: bool = True
    
    # LRU特定配置
    lru_capacity: int = 1000
    
    # LFU特定配置
    lfu_capacity: int = 1000
    lfu_window_size: int = 10000
    
    # TTL特定配置
    ttl_check_interval: int = 300  # 5分钟检查一次过期
    
    # 混合策略配置
    hybrid_lru_ratio: float = 0.6  # LRU部分占比
    hybrid_ttl_ratio: float = 0.4  # TTL部分占比


@dataclass
class PerformanceMetrics:
    """性能指标"""
    request_count: int = 0
    total_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # 响应时间统计
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    # 错误统计
    error_count: int = 0
    timeout_count: int = 0
    
    def add_request(self, response_time: float, cache_hit: bool = False, error: bool = False) -> None:
        """添加请求统计"""
        self.request_count += 1
        self.total_response_time += response_time
        self.response_times.append(response_time)
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        if error:
            self.error_count += 1
    
    def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        if self.request_count == 0:
            return 0.0
        return self.total_response_time / self.request_count
    
    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return self.cache_hits / total_cache_requests
    
    def get_percentile_response_time(self, percentile: float) -> float:
        """获取响应时间百分位数"""
        if not self.response_times:
            return 0.0
        
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
    
    def put(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            if key in self.cache:
                # 更新现有键
                self.cache.pop(key)
            elif len(self.cache) >= self.capacity:
                # 删除最老的键
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def remove(self, key: str) -> bool:
        """删除缓存键"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class LFUCache:
    """LFU缓存实现"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
        self.frequencies = defaultdict(int)
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self.cache:
                self.frequencies[key] += 1
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            if key in self.cache:
                self.cache[key] = value
                self.frequencies[key] += 1
            else:
                if len(self.cache) >= self.capacity:
                    # 删除频率最低的键
                    min_freq_key = min(self.frequencies, key=self.frequencies.get)
                    del self.cache[min_freq_key]
                    del self.frequencies[min_freq_key]
                
                self.cache[key] = value
                self.frequencies[key] = 1
    
    def remove(self, key: str) -> bool:
        """删除缓存键"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                del self.frequencies[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.frequencies.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class TTLCache:
    """TTL缓存实现"""
    
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.timestamps = {}
        self._lock = threading.RLock()
        
        # 启动清理任务
        self._cleanup_task = None
        self._running = True
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """启动清理任务"""
        def cleanup_expired():
            while self._running:
                time.sleep(300)  # 每5分钟清理一次
                self._cleanup_expired_items()
        
        self._cleanup_task = threading.Thread(target=cleanup_expired, daemon=True)
        self._cleanup_task.start()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self.cache:
                if self._is_expired(key):
                    del self.cache[key]
                    del self.timestamps[key]
                    return None
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        if key not in self.timestamps:
            return True
        
        return time.time() - self.timestamps[key] > self.ttl_seconds
    
    def _cleanup_expired_items(self) -> None:
        """清理过期项"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self.timestamps.items()
                if current_time - timestamp > self.ttl_seconds
            ]
            
            for key in expired_keys:
                if key in self.cache:
                    del self.cache[key]
                if key in self.timestamps:
                    del self.timestamps[key]
    
    def remove(self, key: str) -> bool:
        """删除缓存键"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.timestamps:
                    del self.timestamps[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)
    
    def stop(self) -> None:
        """停止清理任务"""
        self._running = False


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, optimization_level: QueryOptimizationLevel = QueryOptimizationLevel.BASIC):
        self.optimization_level = optimization_level
        self.query_patterns = {}
        self.optimization_rules = self._initialize_optimization_rules()
    
    def _initialize_optimization_rules(self) -> Dict[str, Callable]:
        """初始化优化规则"""
        return {
            'remove_stopwords': self._remove_stopwords,
            'normalize_whitespace': self._normalize_whitespace,
            'lowercase_conversion': self._lowercase_conversion,
            'query_expansion': self._query_expansion,
            'semantic_rewrite': self._semantic_rewrite
        }
    
    def optimize_query(self, query: str, query_type: str = "default") -> str:
        """优化查询"""
        if self.optimization_level == QueryOptimizationLevel.NONE:
            return query
        
        optimized_query = query
        
        # 基础优化
        if self.optimization_level in [QueryOptimizationLevel.BASIC, QueryOptimizationLevel.ADVANCED, QueryOptimizationLevel.AGGRESSIVE]:
            optimized_query = self._apply_basic_optimizations(optimized_query)
        
        # 高级优化
        if self.optimization_level in [QueryOptimizationLevel.ADVANCED, QueryOptimizationLevel.AGGRESSIVE]:
            optimized_query = self._apply_advanced_optimizations(optimized_query, query_type)
        
        # 激进优化
        if self.optimization_level == QueryOptimizationLevel.AGGRESSIVE:
            optimized_query = self._apply_aggressive_optimizations(optimized_query, query_type)
        
        return optimized_query
    
    def _apply_basic_optimizations(self, query: str) -> str:
        """应用基础优化"""
        # 标准化空白字符
        query = self.optimization_rules['normalize_whitespace'](query)
        
        # 转换为小写
        query = self.optimization_rules['lowercase_conversion'](query)
        
        return query
    
    def _apply_advanced_optimizations(self, query: str, query_type: str) -> str:
        """应用高级优化"""
        # 移除停用词
        query = self.optimization_rules['remove_stopwords'](query)
        
        # 查询扩展
        query = self.optimization_rules['query_expansion'](query)
        
        return query
    
    def _apply_aggressive_optimizations(self, query: str, query_type: str) -> str:
        """应用激进优化"""
        # 语义重写
        query = self.optimization_rules['semantic_rewrite'](query)
        
        return query
    
    def _remove_stopwords(self, query: str) -> str:
        """移除停用词"""
        stopwords = {'的', '是', '在', '有', '和', '与', '或', '了', '就', '都', '而', '及', '以', '为'}
        words = query.split()
        filtered_words = [word for word in words if word not in stopwords]
        return ' '.join(filtered_words)
    
    def _normalize_whitespace(self, query: str) -> str:
        """标准化空白字符"""
        return ' '.join(query.split())
    
    def _lowercase_conversion(self, query: str) -> str:
        """转换为小写"""
        return query.lower()
    
    def _query_expansion(self, query: str) -> str:
        """查询扩展"""
        # 简单的同义词扩展
        synonyms = {
            '人工智能': ['AI', '机器智能', '智能系统'],
            '机器学习': ['ML', '自动学习', '统计学习'],
            '深度学习': ['DL', '神经网络', '深层网络']
        }
        
        for term, syns in synonyms.items():
            if term in query:
                query += ' ' + ' '.join(syns)
        
        return query
    
    def _semantic_rewrite(self, query: str) -> str:
        """语义重写"""
        # 这里可以集成更复杂的语义重写逻辑
        return query


class ConcurrencyController:
    """并发控制器"""
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0
        self.queued_requests = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """获取并发锁"""
        async with self._lock:
            self.queued_requests += 1
        
        await self.semaphore.acquire()
        
        async with self._lock:
            self.queued_requests -= 1
            self.active_requests += 1
    
    async def release(self) -> None:
        """释放并发锁"""
        async with self._lock:
            self.active_requests -= 1
        
        self.semaphore.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
    
    def get_stats(self) -> Dict[str, int]:
        """获取并发统计"""
        return {
            'max_concurrent': self.max_concurrent,
            'active_requests': self.active_requests,
            'queued_requests': self.queued_requests,
            'available_slots': self.max_concurrent - self.active_requests
        }


class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """初始化性能优化器"""
        self.config = config or CacheConfig()
        
        # 缓存实例
        self.caches = self._initialize_caches()
        
        # 查询优化器
        self.query_optimizer = QueryOptimizer(QueryOptimizationLevel.ADVANCED)
        
        # 并发控制器
        self.concurrency_controller = ConcurrencyController()
        
        # 性能指标
        self.metrics = PerformanceMetrics()
        
        # 请求去重
        self.request_deduplication = {}
        self._dedup_lock = asyncio.Lock()
    
    def _initialize_caches(self) -> Dict[str, Any]:
        """初始化缓存"""
        caches = {}
        
        if self.config.strategy == CacheStrategy.LRU:
            caches['primary'] = LRUCache(self.config.lru_capacity)
        elif self.config.strategy == CacheStrategy.LFU:
            caches['primary'] = LFUCache(self.config.lfu_capacity)
        elif self.config.strategy == CacheStrategy.TTL:
            caches['primary'] = TTLCache(self.config.ttl_seconds)
        elif self.config.strategy == CacheStrategy.HYBRID:
            # 混合缓存策略
            lru_size = int(self.config.max_size * self.config.hybrid_lru_ratio)
            caches['lru'] = LRUCache(lru_size)
            caches['ttl'] = TTLCache(self.config.ttl_seconds)
        
        return caches
    
    def _generate_cache_key(self, query: str, parameters: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 组合查询和参数生成唯一键
        key_data = {
            'query': query,
            'parameters': sorted(parameters.items()) if parameters else []
        }
        
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def _serialize_value(self, value: Any) -> bytes:
        """序列化值"""
        if self.config.enable_serialization:
            return pickle.dumps(value)
        return value
    
    def _deserialize_value(self, data: bytes) -> Any:
        """反序列化值"""
        if self.config.enable_serialization and isinstance(data, bytes):
            return pickle.loads(data)
        return data
    
    def _compress_data(self, data: bytes) -> bytes:
        """压缩数据"""
        if self.config.enable_compression:
            import gzip
            return gzip.compress(data)
        return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """解压数据"""
        if self.config.enable_compression:
            import gzip
            try:
                return gzip.decompress(data)
            except:
                return data
        return data
    
    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        try:
            if self.config.strategy == CacheStrategy.HYBRID:
                # 混合策略：先查LRU，再查TTL
                result = self.caches['lru'].get(cache_key)
                if result is None:
                    result = self.caches['ttl'].get(cache_key)
                    if result is not None:
                        # 将TTL缓存的热数据移到LRU
                        self.caches['lru'].put(cache_key, result)
            else:
                result = self.caches['primary'].get(cache_key)
            
            if result is not None:
                # 解压和反序列化
                if isinstance(result, bytes):
                    result = self._decompress_data(result)
                    result = self._deserialize_value(result)
                
                return result
        
        except Exception as e:
            logger.warning(f"缓存获取失败: {str(e)}")
        
        return None
    
    async def set_cached_result(self, cache_key: str, value: Any) -> None:
        """设置缓存结果"""
        try:
            # 序列化和压缩
            serialized_value = self._serialize_value(value)
            if isinstance(serialized_value, bytes):
                compressed_value = self._compress_data(serialized_value)
            else:
                compressed_value = serialized_value
            
            if self.config.strategy == CacheStrategy.HYBRID:
                # 混合策略：同时存储到两个缓存
                self.caches['lru'].put(cache_key, compressed_value)
                self.caches['ttl'].put(cache_key, compressed_value)
            else:
                self.caches['primary'].put(cache_key, compressed_value)
        
        except Exception as e:
            logger.warning(f"缓存设置失败: {str(e)}")
    
    async def optimize_and_execute(
        self,
        query_func: Callable,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        use_query_optimization: bool = True,
        use_concurrency_control: bool = True,
        enable_deduplication: bool = True
    ) -> Any:
        """优化并执行查询"""
        start_time = time.time()
        parameters = parameters or {}
        
        try:
            # 1. 查询优化
            optimized_query = query
            if use_query_optimization:
                optimized_query = self.query_optimizer.optimize_query(query)
            
            # 2. 生成缓存键
            cache_key = self._generate_cache_key(optimized_query, parameters)
            
            # 3. 检查缓存
            if use_cache:
                cached_result = await self.get_cached_result(cache_key)
                if cached_result is not None:
                    response_time = (time.time() - start_time) * 1000
                    self.metrics.add_request(response_time, cache_hit=True)
                    return cached_result
            
            # 4. 请求去重
            if enable_deduplication:
                async with self._dedup_lock:
                    if cache_key in self.request_deduplication:
                        # 等待正在进行的相同请求
                        logger.info(f"等待重复请求完成: {cache_key[:8]}...")
                        return await self.request_deduplication[cache_key]
                    else:
                        # 创建Future用于去重
                        future = asyncio.Future()
                        self.request_deduplication[cache_key] = future
            
            try:
                # 5. 并发控制
                if use_concurrency_control:
                    async with self.concurrency_controller:
                        result = await query_func(optimized_query, **parameters)
                else:
                    result = await query_func(optimized_query, **parameters)
                
                # 6. 更新缓存
                if use_cache:
                    await self.set_cached_result(cache_key, result)
                
                # 7. 完成请求去重
                if enable_deduplication:
                    async with self._dedup_lock:
                        if cache_key in self.request_deduplication:
                            future = self.request_deduplication[cache_key]
                            if not future.done():
                                future.set_result(result)
                            del self.request_deduplication[cache_key]
                
                # 8. 记录性能指标
                response_time = (time.time() - start_time) * 1000
                self.metrics.add_request(response_time, cache_hit=False)
                
                return result
                
            except Exception as e:
                # 处理请求去重异常
                if enable_deduplication:
                    async with self._dedup_lock:
                        if cache_key in self.request_deduplication:
                            future = self.request_deduplication[cache_key]
                            if not future.done():
                                future.set_exception(e)
                            del self.request_deduplication[cache_key]
                
                raise
        
        except Exception as e:
            # 记录错误指标
            response_time = (time.time() - start_time) * 1000
            self.metrics.add_request(response_time, cache_hit=False, error=True)
            raise
    
    def cache_decorator(
        self,
        use_cache: bool = True,
        use_query_optimization: bool = True,
        use_concurrency_control: bool = True,
        enable_deduplication: bool = True
    ) -> Callable:
        """缓存装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # 提取查询参数
                query = args[0] if args else kwargs.get('query', '')
                parameters = kwargs
                
                return await self.optimize_and_execute(
                    func,
                    query,
                    parameters,
                    use_cache,
                    use_query_optimization,
                    use_concurrency_control,
                    enable_deduplication
                )
            return wrapper
        return decorator
    
    async def batch_process(
        self,
        batch_func: Callable,
        queries: List[str],
        batch_size: int = 10,
        max_concurrent_batches: int = 5
    ) -> List[Any]:
        """批量处理"""
        results = []
        
        # 分批处理
        batches = [queries[i:i + batch_size] for i in range(0, len(queries), batch_size)]
        
        # 限制并发批次数
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_batch(batch: List[str]) -> List[Any]:
            async with semaphore:
                return await batch_func(batch)
        
        # 并发执行所有批次
        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # 合并结果
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        cache_stats = {}
        
        if self.config.strategy == CacheStrategy.HYBRID:
            cache_stats = {
                'lru_size': self.caches['lru'].size(),
                'ttl_size': self.caches['ttl'].size(),
                'total_size': self.caches['lru'].size() + self.caches['ttl'].size()
            }
        else:
            cache_stats = {
                'size': self.caches['primary'].size(),
                'max_size': self.config.max_size
            }
        
        return {
            'request_metrics': {
                'total_requests': self.metrics.request_count,
                'avg_response_time': self.metrics.get_avg_response_time(),
                'p95_response_time': self.metrics.get_percentile_response_time(95),
                'p99_response_time': self.metrics.get_percentile_response_time(99),
                'error_rate': self.metrics.error_count / max(self.metrics.request_count, 1),
            },
            'cache_metrics': {
                'hit_rate': self.metrics.get_cache_hit_rate(),
                'hits': self.metrics.cache_hits,
                'misses': self.metrics.cache_misses,
                **cache_stats
            },
            'concurrency_metrics': self.concurrency_controller.get_stats(),
            'optimization_config': {
                'cache_strategy': self.config.strategy.value,
                'query_optimization': self.query_optimizer.optimization_level.value,
                'max_concurrent': self.concurrency_controller.max_concurrent
            }
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        if self.config.strategy == CacheStrategy.HYBRID:
            self.caches['lru'].clear()
            self.caches['ttl'].clear()
        else:
            self.caches['primary'].clear()
        
        logger.info("缓存已清空")
    
    def cleanup(self) -> None:
        """清理资源"""
        self.clear_cache()
        
        # 停止TTL缓存的清理任务
        if self.config.strategy in [CacheStrategy.TTL, CacheStrategy.HYBRID]:
            if 'ttl' in self.caches:
                self.caches['ttl'].stop()
            elif hasattr(self.caches.get('primary'), 'stop'):
                self.caches['primary'].stop()
        
        logger.info("性能优化器清理完成")


# 全局性能优化器实例
_performance_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer(config: Optional[CacheConfig] = None) -> PerformanceOptimizer:
    """获取全局性能优化器实例"""
    global _performance_optimizer
    
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer(config)
    
    return _performance_optimizer


# 便捷装饰器
def optimize_performance(**kwargs):
    """性能优化装饰器快捷方式"""
    optimizer = get_performance_optimizer()
    return optimizer.cache_decorator(**kwargs) 