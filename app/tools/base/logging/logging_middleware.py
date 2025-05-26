#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志中间件模块：提供统一的日志记录、格式化和管理功能
"""

import os
import sys
import time
import json
import logging
import traceback
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional, Union, Callable

import yaml
from fastapi import FastAPI, Request, Response
from fastapi.logger import logger as fastapi_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# 配置根日志记录器关联到 uvicorn 的日志处理器
root_logger = logging.getLogger()
gunicorn_logger = logging.getLogger('gunicorn.error')
uvicorn_logger = logging.getLogger('uvicorn')

if root_logger.handlers:
    # 清除所有处理器，避免重复处理
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)


class CustomJSONFormatter(logging.Formatter):
    """
    自定义JSON格式的日志格式化器
    - 支持结构化日志输出
    - 包含额外的上下文信息
    - 适合ELK等日志系统集成
    """
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        
        # 添加异常信息（如果有）
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exc().split("\n")
            }
        
        # 添加额外字段
        if hasattr(record, "extra"):
            log_record.update(record.extra)
            
        # 添加请求ID（如果有）
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
            
        return json.dumps(log_record, ensure_ascii=False)


class StructuredLogger:
    """结构化日志记录器，支持添加上下文信息"""
    
    def __init__(self, name: str, extra: Dict[str, Any] = None):
        self.logger = logging.getLogger(name)
        self.extra = extra or {}
        
    def bind(self, **kwargs) -> 'StructuredLogger':
        """创建一个绑定额外上下文的新日志记录器"""
        return StructuredLogger(
            self.logger.name, 
            {**self.extra, **kwargs}
        )
        
    def _log(self, level: int, msg: str, *args, **kwargs):
        extra = {**self.extra, **kwargs.pop("extra", {})}
        self.logger.log(level, msg, *args, extra=extra, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
        
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
        
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
        
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
        
    def exception(self, msg: str, *args, **kwargs):
        kwargs["exc_info"] = kwargs.get("exc_info", True)
        self._log(logging.ERROR, msg, *args, **kwargs)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件：记录所有HTTP请求的详细信息
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        exclude_paths: list = None, 
        log_request_body: bool = False,
        log_response_body: bool = False
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.logger = StructuredLogger("http.request")
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否需要忽略此路径
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
            
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "-")
        
        # 准备请求日志
        request_log = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("User-Agent", "-"),
        }
        
        # 可选地记录请求体
        if self.log_request_body:
            try:
                body = await request.body()
                if body:
                    try:
                        # 尝试解析为JSON
                        request_log["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        # 非JSON内容则记录字节长度
                        request_log["body_size"] = len(body)
            except Exception as e:
                request_log["body_error"] = str(e)
        
        # 处理请求前记录日志
        logger = self.logger.bind(**request_log)
        logger.info(f"开始处理请求 - {request.method} {request.url.path}")
        
        # 执行请求并捕获响应
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 准备响应日志
            response_log = {
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2)
            }
            
            # 可选地记录响应体
            if self.log_response_body and response.status_code >= 400:
                # 只记录错误响应的内容
                response_body = response.body
                if response_body:
                    try:
                        # 尝试解析为JSON
                        response_log["response_body"] = json.loads(response_body)
                    except json.JSONDecodeError:
                        # 非JSON内容则记录字节长度
                        response_log["response_body_size"] = len(response_body)
                        
            # 处理请求后记录日志
            logger = logger.bind(**response_log)
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger._log(log_level, f"完成请求处理 - {request.method} {request.url.path} - 状态码: {response.status_code} - 耗时: {response_log['process_time_ms']}ms")
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            
            # 记录异常日志
            logger.bind(
                process_time_ms=round(process_time * 1000, 2),
                error=str(exc),
                exception=traceback.format_exc().split("\n")
            ).exception(f"请求处理出错 - {request.method} {request.url.path}")
            
            # 重新抛出异常，让FastAPI的异常处理器处理
            raise


class LoggingManager:
    """日志管理器：负责配置和初始化日志系统"""
    
    @staticmethod
    def setup_logging(
        app: FastAPI = None,
        log_level: str = "INFO",
        log_to_console: bool = True,
        log_to_file: bool = False,
        log_file_path: str = "logs/app.log",
        log_format: str = "json",
        log_retention: int = 30,
        log_rotation: str = "daily",
        exclude_paths: list = None,
        log_request_body: bool = False,
        log_response_body: bool = False
    ):
        """
        设置日志系统
        
        Args:
            app: FastAPI应用实例（如果要添加请求日志中间件）
            log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            log_to_console: 是否输出到控制台
            log_to_file: 是否输出到文件
            log_file_path: 日志文件路径
            log_format: 日志格式（json或text）
            log_retention: 日志保留天数
            log_rotation: 日志轮转周期（daily, weekly, monthly）
            exclude_paths: 请求日志中间件需要排除的路径
            log_request_body: 是否记录请求体
            log_response_body: 是否记录响应体
        """
        # 设置日志级别
        level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(level)
        
        # 创建格式化器
        if log_format.lower() == "json":
            formatter = CustomJSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # 配置控制台输出
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # 配置文件输出
        if log_to_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            # 使用 RotatingFileHandler 或 TimedRotatingFileHandler
            if log_rotation.lower() == "size":
                # 按大小轮转
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=log_retention
                )
            else:
                # 按时间轮转
                from logging.handlers import TimedRotatingFileHandler
                when_map = {
                    "daily": "D",
                    "weekly": "W0",
                    "monthly": "M"
                }
                when = when_map.get(log_rotation.lower(), "D")
                file_handler = TimedRotatingFileHandler(
                    log_file_path,
                    when=when,
                    backupCount=log_retention
                )
            
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # 配置FastAPI请求日志中间件
        if app is not None:
            exclude_paths = exclude_paths or [
                "/docs", 
                "/redoc", 
                "/openapi.json",
                "/metrics",
                "/health"
            ]
            app.add_middleware(
                RequestLoggingMiddleware,
                exclude_paths=exclude_paths,
                log_request_body=log_request_body,
                log_response_body=log_response_body
            )
            
        # 设置其他流行库的日志级别
        for logger_name in ["uvicorn", "uvicorn.access", "fastapi"]:
            logging.getLogger(logger_name).setLevel(level)
            
        # 输出初始化信息
        root_logger.info(f"日志系统初始化完成，级别: {log_level}, 格式: {log_format}")
        
    @staticmethod
    def get_logger(name: str, **extra) -> StructuredLogger:
        """
        获取一个结构化日志记录器
        
        Args:
            name: 日志记录器名称
            **extra: 要绑定到日志记录器的额外上下文数据
            
        Returns:
            结构化日志记录器实例
        """
        return StructuredLogger(name, extra)
    
    @staticmethod
    def log_execution_time(logger: Optional[StructuredLogger] = None, level: str = "info"):
        """
        记录函数执行时间的装饰器
        
        Args:
            logger: 结构化日志记录器，如果为None则自动创建
            level: 日志级别，可选值：debug, info, warning, error, critical
        
        Returns:
            装饰器函数
        """
        def decorator(func):
            func_logger = logger or StructuredLogger(func.__module__)
            log_func = getattr(func_logger, level.lower(), func_logger.info)
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    log_func(
                        f"函数 {func.__name__} 执行完成",
                        execution_time_ms=round(execution_time * 1000, 2)
                    )
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    func_logger.exception(
                        f"函数 {func.__name__} 执行出错: {str(e)}",
                        execution_time_ms=round(execution_time * 1000, 2)
                    )
                    raise
            return wrapper
        return decorator


# 配置日志记录器的快捷方法
def setup_logging(app: FastAPI = None, **kwargs):
    """初始化日志配置的快捷方法"""
    return LoggingManager.setup_logging(app, **kwargs)


# 获取日志记录器的快捷方法
def get_logger(name: str, **extra):
    """获取日志记录器的快捷方法"""
    return LoggingManager.get_logger(name, **extra)


# 记录执行时间的装饰器快捷方法
def log_execution_time(logger: Optional[StructuredLogger] = None, level: str = "info"):
    """记录函数执行时间的装饰器快捷方法"""
    return LoggingManager.log_execution_time(logger, level)
