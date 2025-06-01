"""
速率限制器: 为API端点提供速率限制功能，
防止滥用并确保公平的资源分配
"""

import time
from typing import Dict, Tuple, Any
import threading

class RateLimiter:
    """
    使用令牌桶算法限制请求的速率限制器
    支持突发请求和按客户端的速率限制
    """
    
    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        """
        初始化速率限制器
        
        参数:
            requests_per_minute: 每分钟允许的请求数
            burst_limit: 突发请求允许的最大数量
        """
        self.rate = requests_per_minute / 60.0  # 每秒令牌数
        self.burst_limit = burst_limit
        self.clients: Dict[str, Tuple[float, float]] = {}  # client_id -> (tokens, last_update)
        self.lock = threading.Lock()
    
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
