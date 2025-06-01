#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志配置模块：从环境变量和配置文件中加载日志系统配置
"""

import os
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field
from app.utils.core.config import ConfigManager


class LoggingConfig(BaseModel):
    """日志系统配置模型"""
    
    # 基本设置
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(default="text", description="日志格式（text或json）")
    
    # 控制台输出
    console_enabled: bool = Field(default=True, description="是否启用控制台日志")
    console_level: Optional[str] = Field(default=None, description="控制台日志级别（如不设置则使用全局level）")
    
    # 文件日志
    file_enabled: bool = Field(default=False, description="是否启用文件日志")
    file_level: Optional[str] = Field(default=None, description="文件日志级别（如不设置则使用全局level）")
    file_path: str = Field(default="logs/app.log", description="日志文件路径")
    file_rotation: str = Field(default="daily", description="日志轮转周期（daily、weekly、monthly）")
    file_retention: int = Field(default=30, description="日志保留天数")
    
    # 请求日志
    request_logging: bool = Field(default=True, description="是否启用请求日志中间件")
    request_level: Optional[str] = Field(default=None, description="请求日志级别（如不设置则使用全局level）")
    log_request_body: bool = Field(default=False, description="是否记录请求体内容")
    log_response_body: bool = Field(default=False, description="是否记录响应体内容")
    request_exclude_paths: List[str] = Field(
        default=["/docs", "/redoc", "/openapi.json", "/metrics", "/health"],
        description="不记录请求日志的路径"
    )
    
    # 特殊模块日志级别
    module_levels: Dict[str, str] = Field(
        default={},
        description="模块特定的日志级别，例如 {'app.api': 'DEBUG'}"
    )


def load_logging_config() -> LoggingConfig:
    """
    从环境变量加载日志配置
    
    环境变量映射:
    - LOG_LEVEL: 日志级别
    - LOG_FORMAT: 日志格式（text或json）
    - LOG_CONSOLE_ENABLED: 是否启用控制台日志
    - LOG_CONSOLE_LEVEL: 控制台日志级别
    - LOG_FILE_ENABLED: 是否启用文件日志
    - LOG_FILE_LEVEL: 文件日志级别
    - LOG_FILE_PATH: 日志文件路径
    - LOG_FILE_ROTATION: 日志轮转周期
    - LOG_FILE_RETENTION: 日志保留天数
    - LOG_REQUEST_ENABLED: 是否启用请求日志
    - LOG_REQUEST_LEVEL: 请求日志级别
    - LOG_REQUEST_BODY: 是否记录请求体
    - LOG_RESPONSE_BODY: 是否记录响应体
    - LOG_MODULE_LEVELS: 模块特定的日志级别（JSON格式）
    """
    # 构建默认配置
    config = LoggingConfig()
    
    # 从环境变量加载
    config.level = os.getenv("LOG_LEVEL", config.level)
    config.format = os.getenv("LOG_FORMAT", config.format)
    
    # 控制台日志
    console_enabled = os.getenv("LOG_CONSOLE_ENABLED")
    if console_enabled is not None:
        config.console_enabled = console_enabled.lower() in ("true", "1", "yes")
    config.console_level = os.getenv("LOG_CONSOLE_LEVEL", config.console_level)
    
    # 文件日志
    file_enabled = os.getenv("LOG_FILE_ENABLED")
    if file_enabled is not None:
        config.file_enabled = file_enabled.lower() in ("true", "1", "yes")
    config.file_level = os.getenv("LOG_FILE_LEVEL", config.file_level)
    config.file_path = os.getenv("LOG_FILE_PATH", config.file_path)
    config.file_rotation = os.getenv("LOG_FILE_ROTATION", config.file_rotation)
    retention = os.getenv("LOG_FILE_RETENTION")
    if retention is not None:
        config.file_retention = int(retention)
    
    # 请求日志
    request_logging = os.getenv("LOG_REQUEST_ENABLED")
    if request_logging is not None:
        config.request_logging = request_logging.lower() in ("true", "1", "yes")
    config.request_level = os.getenv("LOG_REQUEST_LEVEL", config.request_level)
    
    # 请求体和响应体日志
    request_body = os.getenv("LOG_REQUEST_BODY")
    if request_body is not None:
        config.log_request_body = request_body.lower() in ("true", "1", "yes")
    response_body = os.getenv("LOG_RESPONSE_BODY")
    if response_body is not None:
        config.log_response_body = response_body.lower() in ("true", "1", "yes")
    
    # 模块特定日志级别
    module_levels = os.getenv("LOG_MODULE_LEVELS")
    if module_levels:
        import json
        try:
            config.module_levels = json.loads(module_levels)
        except json.JSONDecodeError:
            pass
    
    return config


def register_logging_env_mappings(config_manager: ConfigManager) -> None:
    """
    向配置管理器注册日志相关的环境变量映射
    """
    logging_mappings = {
        "LOG_LEVEL": ["logging", "level"],
        "LOG_FORMAT": ["logging", "format"],
        "LOG_CONSOLE_ENABLED": ["logging", "console", "enabled"],
        "LOG_CONSOLE_LEVEL": ["logging", "console", "level"],
        "LOG_FILE_ENABLED": ["logging", "file", "enabled"],
        "LOG_FILE_LEVEL": ["logging", "file", "level"],
        "LOG_FILE_PATH": ["logging", "file", "path"],
        "LOG_FILE_ROTATION": ["logging", "file", "rotation"],
        "LOG_FILE_RETENTION": ["logging", "file", "retention"],
        "LOG_REQUEST_ENABLED": ["logging", "request", "enabled"],
        "LOG_REQUEST_LEVEL": ["logging", "request", "level"],
        "LOG_REQUEST_BODY": ["logging", "request", "log_request_body"],
        "LOG_RESPONSE_BODY": ["logging", "request", "log_response_body"],
        "LOG_MODULE_LEVELS": ["logging", "module_levels"],
    }
    
    config_manager.register_env_mappings(logging_mappings)
