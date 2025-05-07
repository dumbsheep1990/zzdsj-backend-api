#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
安全中间件集成模块：统一管理所有安全相关中间件
"""

import logging
from fastapi import FastAPI

from app.middleware.host_validator import add_host_validator_middleware
from app.middleware.rate_limiter import add_rate_limiter_middleware
from app.middleware.sensitive_word_middleware import SensitiveWordMiddleware
from app.utils.config_manager import get_config_manager

logger = logging.getLogger(__name__)


def setup_security_middleware(app: FastAPI) -> None:
    """
    设置所有安全相关中间件
    
    参数:
        app: FastAPI应用实例
    """
    config = get_config_manager().get_config()
    debug_mode = config.get("debug_mode", False)
    
    # 注册中间件的优先级：
    # 1. 首先是请求验证（域名验证）
    # 2. 然后是速率限制
    # 3. 最后是内容过滤（敏感词过滤）
    
    logger.info("正在设置安全中间件...")
    
    # 添加域名验证中间件
    add_host_validator_middleware(app)
    
    # 添加请求限流中间件
    add_rate_limiter_middleware(app)
    
    # 添加敏感词过滤中间件
    if not debug_mode:
        app.add_middleware(SensitiveWordMiddleware)
        logger.info("已添加敏感词过滤中间件")
    else:
        logger.warning("调试模式已开启，敏感词过滤已禁用")
    
    logger.info("所有安全中间件设置完成")
