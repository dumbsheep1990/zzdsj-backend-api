#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
域名验证工具：拦截非法域名访问，增强系统安全性
"""

import json
import logging
from typing import List, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from fastapi import FastAPI, status

from app.utils.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class HostValidator(BaseHTTPMiddleware):
    """
    域名验证中间件：拦截非授权域名的请求
    - 验证请求的Host头是否在允许列表中
    - 调试模式下跳过验证
    - 支持通配符匹配
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        allowed_hosts: List[str] = None,
        debug_mode: bool = False
    ):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        self.debug_mode = debug_mode
        logger.info(f"域名验证中间件初始化完成，允许的域名: {', '.join(self.allowed_hosts)}")
        if self.debug_mode:
            logger.warning("调试模式已开启，域名验证已禁用")
    
    def is_valid_host(self, host: str) -> bool:
        """检查主机名是否在允许列表中"""
        if not host:
            return False
            
        # 移除端口号
        if ":" in host:
            host = host.split(":")[0]
            
        # 检查是否允许
        for allowed_host in self.allowed_hosts:
            # 精确匹配
            if host == allowed_host:
                return True
                
            # 通配符匹配（如 *.example.com）
            if allowed_host.startswith("*.") and host.endswith(allowed_host[1:]):
                return True
                
        return False
        
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求，验证域名"""
        # 调试模式下不进行验证
        if self.debug_mode:
            return await call_next(request)
            
        # 获取主机名
        host = request.headers.get("host", "")
        
        # 验证主机名
        if not self.is_valid_host(host):
            logger.warning(f"域名验证失败: {host}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "禁止访问：域名未授权"}
            )
            
        # 允许的域名，继续处理
        return await call_next(request)


def add_host_validator_middleware(app: FastAPI) -> None:
    """向FastAPI应用添加域名验证中间件"""
    config = get_config_manager().get_config()
    
    # 获取调试模式配置
    debug_mode = config.get("debug_mode", False)
    
    # 获取允许的域名列表
    allowed_hosts_str = config.get("allowed_hosts", '["localhost", "127.0.0.1"]')
    try:
        if isinstance(allowed_hosts_str, str):
            allowed_hosts = json.loads(allowed_hosts_str)
        else:
            allowed_hosts = allowed_hosts_str
    except json.JSONDecodeError:
        logger.error(f"域名列表解析失败: {allowed_hosts_str}，使用默认值")
        allowed_hosts = ["localhost", "127.0.0.1"]
    
    # 添加中间件
    app.add_middleware(
        HostValidator,
        allowed_hosts=allowed_hosts,
        debug_mode=debug_mode
    )
    
    logger.info("已添加域名验证中间件")
