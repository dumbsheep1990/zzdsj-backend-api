"""
日志工具模块
提供向后兼容的日志功能
"""

import logging
import sys
from typing import Optional, Dict, Any
from .logging_config import load_logging_config, LoggingConfig


def setup_logger(name: str = None, level: str = "INFO", format_type: str = "text") -> logging.Logger:
    """
    设置并返回一个配置好的logger
    
    参数:
        name: logger名称，如果为None则使用root logger
        level: 日志级别
        format_type: 格式类型（text或json）
        
    返回:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    
    # 如果logger已经有handler，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 创建控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 设置格式
    if format_type.lower() == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    获取logger实例
    
    参数:
        name: logger名称
        
    返回:
        logger实例
    """
    if name is None:
        name = __name__
    
    logger = logging.getLogger(name)
    
    # 如果logger没有handler，使用默认配置
    if not logger.handlers:
        config = load_logging_config()
        return setup_logger(name, config.level, config.format)
    
    return logger


# 为了向后兼容，提供一些常用的logger实例
default_logger = get_logger("app")
api_logger = get_logger("app.api")
service_logger = get_logger("app.services")
utils_logger = get_logger("app.utils") 