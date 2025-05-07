#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
请求限流中间件：控制API的访问频率，防止滥用
"""

import time
import logging
import asyncio
from typing import Dict, Tuple, Callable, Optional
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from fastapi import FastAPI, status

from app.utils.config_manager import get_config_manager
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    速率限制器基类
    """
    async def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        raise NotImplementedError("子类必须实现此方法")


class InMemoryRateLimiter(RateLimiter):
    """
    内存型速率限制器：适合单实例部署
    - 使用内存字典保存请求记录
    - 支持按不同时间窗口限制
    """
    
    def __init__(self, rate_limit: str = "60/minute"):
        """
        初始化速率限制器
        
        参数:
            rate_limit: 速率限制规则，格式为"数量/时间单位"
                       例如: "60/minute", "1000/hour", "10/second"
        """
        self.requests: Dict[str, Dict[str, list]] = {}
        self.cleanup_task = None
        
        # 解析速率限制规则
        parts = rate_limit.split("/")
        if len(parts) != 2:
            raise ValueError(f"无效的速率限制格式: {rate_limit}")
            
        try:
            self.max_requests = int(parts[0])
        except ValueError:
            raise ValueError(f"无效的请求数量: {parts[0]}")
            
        # 将时间单位转换为秒
        time_unit = parts[1].lower()
        if time_unit == "second":
            self.window_seconds = 1
        elif time_unit == "minute":
            self.window_seconds = 60
        elif time_unit == "hour":
            self.window_seconds = 3600
        elif time_unit == "day":
            self.window_seconds = 86400
        else:
            raise ValueError(f"不支持的时间单位: {time_unit}")
            
        logger.info(f"内存型速率限制器初始化完成: {self.max_requests}请求/{time_unit}")
        
    async def start_cleanup_task(self):
        """启动清理任务，定期清理过期的请求记录"""
        if self.cleanup_task is not None:
            return
            
        async def cleanup():
            while True:
                try:
                    now = time.time()
                    keys_to_remove = []
                    
                    for key, windows in self.requests.items():
                        for window, timestamps in list(windows.items()):
                            # 移除窗口中的过期时间戳
                            self.requests[key][window] = [
                                ts for ts in timestamps
                                if now - ts < self.window_seconds
                            ]
                            
                            # 如果窗口为空，标记为删除
                            if not self.requests[key][window]:
                                del self.requests[key][window]
                                
                        # 如果没有窗口，标记整个键删除
                        if not self.requests[key]:
                            keys_to_remove.append(key)
                            
                    # 删除空键
                    for key in keys_to_remove:
                        del self.requests[key]
                        
                    # 等待下一次清理
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"清理过期请求时出错: {str(e)}")
                    await asyncio.sleep(10)
                    
        self.cleanup_task = asyncio.create_task(cleanup())
        
    async def is_allowed(self, key: str) -> bool:
        """
        检查请求是否在限制范围内
        
        参数:
            key: 请求的唯一标识，通常为IP或用户ID
            
        返回:
            bool: 是否允许请求
        """
        # 启动清理任务（如果尚未启动）
        if self.cleanup_task is None:
            await self.start_cleanup_task()
            
        now = time.time()
        # 当前时间窗口
        window = str(int(now / self.window_seconds))
        
        # 初始化请求记录
        if key not in self.requests:
            self.requests[key] = {}
            
        if window not in self.requests[key]:
            self.requests[key][window] = []
            
        # 统计当前窗口的请求数量
        count = len(self.requests[key][window])
        
        # 检查是否超过限制
        if count >= self.max_requests:
            return False
            
        # 记录请求时间戳
        self.requests[key][window].append(now)
        return True


class RedisRateLimiter(RateLimiter):
    """
    Redis速率限制器：适合分布式部署
    - 使用Redis保存请求记录
    - 通过原子操作保证并发安全
    """
    
    def __init__(self, rate_limit: str = "60/minute", redis_client=None):
        """
        初始化Redis速率限制器
        
        参数:
            rate_limit: 速率限制规则，格式为"数量/时间单位"
            redis_client: Redis客户端实例，如不提供则自动创建
        """
        self.redis = redis_client or get_redis_client()
        
        # 解析速率限制规则
        parts = rate_limit.split("/")
        if len(parts) != 2:
            raise ValueError(f"无效的速率限制格式: {rate_limit}")
            
        try:
            self.max_requests = int(parts[0])
        except ValueError:
            raise ValueError(f"无效的请求数量: {parts[0]}")
            
        # 将时间单位转换为秒
        time_unit = parts[1].lower()
        if time_unit == "second":
            self.window_seconds = 1
        elif time_unit == "minute":
            self.window_seconds = 60
        elif time_unit == "hour":
            self.window_seconds = 3600
        elif time_unit == "day":
            self.window_seconds = 86400
        else:
            raise ValueError(f"不支持的时间单位: {time_unit}")
            
        logger.info(f"Redis速率限制器初始化完成: {self.max_requests}请求/{time_unit}")
        
    async def is_allowed(self, key: str) -> bool:
        """
        使用Redis的滑动窗口算法检查请求是否允许
        
        参数:
            key: 请求的唯一标识
            
        返回:
            bool: 是否允许请求
        """
        now = int(time.time())
        # 当前时间窗口的Key
        redis_key = f"rate_limit:{key}:{int(now / self.window_seconds)}"
        
        # 使用Redis Pipeline执行原子操作
        async def process_request():
            # 获取当前请求数
            count = await self.redis.get(redis_key)
            count = int(count) if count else 0
            
            # 检查是否超过限制
            if count >= self.max_requests:
                return False
                
            # 递增请求计数并设置过期时间
            await self.redis.incr(redis_key)
            # 设置过期时间为窗口时间 + 1秒（避免窗口边界问题）
            await self.redis.expire(redis_key, self.window_seconds + 1)
            return True
            
        try:
            return await process_request()
        except Exception as e:
            logger.error(f"Redis速率限制出错: {str(e)}")
            # 出错时默认放行（避免阻断正常服务）
            return True


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    请求限流中间件：控制API访问频率
    """
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter = None,
        enabled: bool = True,
        debug_mode: bool = False,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.enabled = enabled
        self.debug_mode = debug_mode
        
        if self.debug_mode:
            logger.warning("调试模式已开启，请求限流已禁用")
        elif not self.enabled:
            logger.info("请求限流已手动禁用")
        else:
            logger.info("请求限流中间件初始化完成")
        
    def get_client_identifier(self, request: Request) -> str:
        """获取客户端标识：优先使用X-Forwarded-For，回退到客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 使用第一个IP（最接近用户的代理）
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # 直接使用客户端地址
            client_ip = request.client.host if request.client else "unknown"
            
        return client_ip
        
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求，执行速率限制"""
        # 调试模式或已禁用则跳过限流
        if self.debug_mode or not self.enabled or not self.rate_limiter:
            return await call_next(request)
            
        # 获取客户端标识
        client_id = self.get_client_identifier(request)
        
        # 检查是否允许请求
        allowed = await self.rate_limiter.is_allowed(client_id)
        if not allowed:
            logger.warning(f"请求速率超限: {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "请求频率过高，请稍后再试",
                    "type": "rate_limit_exceeded"
                }
            )
            
        # 允许请求，继续处理
        return await call_next(request)


def parse_rate_limit(rate_limit_str: str) -> Tuple[int, int]:
    """解析速率限制字符串，返回(最大请求数, 窗口秒数)"""
    parts = rate_limit_str.split("/")
    if len(parts) != 2:
        raise ValueError(f"无效的速率限制格式: {rate_limit_str}")
        
    try:
        max_requests = int(parts[0])
    except ValueError:
        raise ValueError(f"无效的请求数量: {parts[0]}")
        
    # 将时间单位转换为秒
    time_unit = parts[1].lower()
    if time_unit == "second":
        window_seconds = 1
    elif time_unit == "minute":
        window_seconds = 60
    elif time_unit == "hour":
        window_seconds = 3600
    elif time_unit == "day":
        window_seconds = 86400
    else:
        raise ValueError(f"不支持的时间单位: {time_unit}")
        
    return max_requests, window_seconds


def add_rate_limiter_middleware(app: FastAPI) -> None:
    """向FastAPI应用添加请求限流中间件"""
    config = get_config_manager().get_config()
    
    # 获取调试模式配置
    debug_mode = config.get("debug_mode", False)
    
    # 获取限流配置
    enabled = config.get("request_limiting_enabled", True)
    rate_limit = config.get("request_rate_limit", "60/minute")
    
    # 尝试使用Redis速率限制器，回退到内存限制器
    try:
        rate_limiter = RedisRateLimiter(rate_limit=rate_limit)
        logger.info("使用Redis速率限制器")
    except Exception as e:
        logger.warning(f"Redis速率限制器初始化失败: {str(e)}，回退到内存限制器")
        rate_limiter = InMemoryRateLimiter(rate_limit=rate_limit)
    
    # 添加中间件
    app.add_middleware(
        RateLimiterMiddleware,
        rate_limiter=rate_limiter,
        enabled=enabled,
        debug_mode=debug_mode
    )
    
    logger.info("已添加请求限流中间件")
