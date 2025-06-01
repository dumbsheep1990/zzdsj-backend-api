"""
速率限制器实现
使用令牌桶算法进行速率控制
"""

import time
from typing import Dict, Tuple, Any, Optional
import threading

from ..core.base import SecurityComponent
from ..core.exceptions import RateLimitExceeded


class RateLimiter(SecurityComponent):
    """
    使用令牌桶算法的速率限制器
    支持突发请求和按客户端的速率限制
    """
    
    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10, **kwargs):
        """
        初始化速率限制器
        
        参数:
            requests_per_minute: 每分钟允许的请求数
            burst_limit: 突发请求允许的最大数量
        """
        super().__init__(kwargs)
        self.rate = requests_per_minute / 60.0  # 每秒令牌数
        self.burst_limit = burst_limit
        self.clients: Dict[str, Tuple[float, float]] = {}  # client_id -> (tokens, last_update)
        self.lock = threading.Lock()
    
    async def initialize(self) -> None:
        """初始化组件"""
        self._initialized = True
        self.logger.info(f"速率限制器初始化完成: {self.rate:.2f}请求/秒, 突发限制: {self.burst_limit}")
    
    async def check(self, client_id: str, raise_exception: bool = False) -> bool:
        """
        检查是否允许客户端的请求
        
        参数:
            client_id: 客户端标识符（例如IP地址）
            raise_exception: 是否在限制时抛出异常
            
        返回:
            如果允许请求则返回True，否则返回False
            
        异常:
            RateLimitExceeded: 当raise_exception=True且超出限制时
        """
        allowed = self.allow_request(client_id)
        
        if not allowed and raise_exception:
            status = self.get_client_status(client_id)
            raise RateLimitExceeded(
                message=f"Rate limit exceeded for client {client_id}",
                remaining=status["remaining"],
                reset_time=status["reset"]
            )
        
        return allowed
    
    def allow_request(self, client_id: str) -> bool:
        """
        检查是否允许客户端的请求
        
        参数:
            client_id: 客户端标识符（例如IP地址）
            
        返回:
            如果允许请求则返回True，否则返回False
        """
        with self.lock:
            current_time = time.time()
            
            if client_id not in self.clients:
                # 新客户端，初始化为最大令牌数
                self.clients[client_id] = (self.burst_limit, current_time)
                return True
            
            # 获取当前令牌数和最后更新时间
            tokens, last_update = self.clients[client_id]
            
            # 根据经过的时间计算要添加的令牌数
            time_passed = current_time - last_update
            tokens_to_add = time_passed * self.rate
            
            # 更新令牌数，但不超过突发限制
            new_tokens = min(self.burst_limit, tokens + tokens_to_add)
            
            if new_tokens < 1:
                # 令牌不足
                self.clients[client_id] = (new_tokens, current_time)
                return False
            
            # 消耗一个令牌并允许请求
            self.clients[client_id] = (new_tokens - 1, current_time)
            return True
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """
        获取客户端的速率限制状态
        
        参数:
            client_id: 客户端标识符
            
        返回:
            包含速率限制状态的字典
        """
        with self.lock:
            current_time = time.time()
            
            if client_id not in self.clients:
                return {
                    "remaining": self.burst_limit,
                    "limit": self.burst_limit,
                    "reset": current_time
                }
            
            tokens, last_update = self.clients[client_id]
            time_passed = current_time - last_update
            tokens_to_add = time_passed * self.rate
            new_tokens = min(self.burst_limit, tokens + tokens_to_add)
            
            # 计算重置时间（客户端将有1个令牌的时间）
            reset_time = current_time
            if new_tokens < 1:
                reset_time = current_time + (1 - new_tokens) / self.rate
            
            return {
                "remaining": max(0, int(new_tokens)),
                "limit": self.burst_limit,
                "reset": reset_time
            }
    
    def clear_stale_clients(self, max_age_seconds: int = 3600):
        """
        清除长时间未发出请求的客户端
        
        参数:
            max_age_seconds: 保留客户端记录的最大时间（秒）
        """
        with self.lock:
            current_time = time.time()
            stale_clients = [
                client_id for client_id, (_, last_update) in self.clients.items()
                if current_time - last_update > max_age_seconds
            ]
            
            for client_id in stale_clients:
                del self.clients[client_id]
            
            if stale_clients:
                self.logger.info(f"清除了 {len(stale_clients)} 个过期客户端记录")


# 全局速率限制器实例
_default_rate_limiter: Optional[RateLimiter] = None


def create_rate_limiter(requests_per_minute: int = 60, burst_limit: int = 10) -> RateLimiter:
    """
    创建速率限制器实例
    
    参数:
        requests_per_minute: 每分钟允许的请求数
        burst_limit: 突发请求允许的最大数量
        
    返回:
        速率限制器实例
    """
    return RateLimiter(requests_per_minute=requests_per_minute, burst_limit=burst_limit)


async def check_rate_limit(client_id: str, limiter: Optional[RateLimiter] = None) -> bool:
    """
    检查客户端是否超出速率限制
    
    参数:
        client_id: 客户端标识符
        limiter: 速率限制器实例，如果不提供则使用默认实例
        
    返回:
        是否允许请求
    """
    global _default_rate_limiter
    
    if limiter is None:
        if _default_rate_limiter is None:
            _default_rate_limiter = create_rate_limiter()
            await _default_rate_limiter.initialize()
        limiter = _default_rate_limiter
    
    return await limiter.check(client_id) 