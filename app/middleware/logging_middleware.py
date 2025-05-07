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
                traceback=traceback.format_exc().split("\n")
            ).exception(f"请求处理异常 - {request.method} {request.url.path}")
            
            # 重新抛出异常，让FastAPI的异常处理器处理
            raise


class LoggingManager:
    """
    日志管理器：负责配置和初始化日志系统
    """
    
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
        # 创建日志目录（如果需要）
        if log_to_file:
            log_dir = os.path.dirname(log_file_path)
            os.makedirs(log_dir, exist_ok=True)
        
        # 设置根日志级别
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)
        
        # 添加控制台处理器
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            
            if log_format.lower() == "json":
                formatter = CustomJSONFormatter()
            else:
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
            
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # 添加文件处理器
        if log_to_file:
            try:
                # 导入第三方日志轮转库
                from logging.handlers import TimedRotatingFileHandler
                
                rotation_map = {
                    "daily": "D",
                    "weekly": "W0",  # 周一轮转
                    "monthly": "M"
                }
                
                file_handler = TimedRotatingFileHandler(
                    log_file_path,
                    when=rotation_map.get(log_rotation.lower(), "D"),
                    backupCount=log_retention
                )
                
                if log_format.lower() == "json":
                    formatter = CustomJSONFormatter()
                else:
                    formatter = logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S"
                    )
                    
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                logging.error(f"设置文件日志处理器失败: {str(e)}")
        
        # 添加请求日志中间件
        if app:
            app.add_middleware(
                RequestLoggingMiddleware,
                exclude_paths=exclude_paths or ["/docs", "/redoc", "/openapi.json", "/metrics", "/health"],
                log_request_body=log_request_body,
                log_response_body=log_response_body
            )
            
        # 重定向 FastAPI 日志到根日志
        fastapi_logger.handlers = root_logger.handlers
            
        # 创建并返回一个日志管理器实例
        return LoggingManager()
    
    @staticmethod
    def get_logger(name: str, **extra) -> StructuredLogger:
        """获取一个结构化日志记录器"""
        return StructuredLogger(name, extra)
        
    @staticmethod
    def log_execution_time(logger: Optional[StructuredLogger] = None, level: str = "info"):
        """记录函数执行时间的装饰器"""
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        log_level = level_map.get(level.lower(), logging.INFO)
        
        def decorator(func):
            # 如果没有提供logger，使用函数的模块作为日志名
            nonlocal logger
            if logger is None:
                logger = StructuredLogger(func.__module__)
                
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger._log(
                    log_level,
                    f"函数 {func.__name__} 执行完成，耗时: {execution_time:.4f}秒",
                    extra={"function": func.__name__, "execution_time": execution_time}
                )
                
                return result
                
            return wrapper
            
        return decorator


# 配置日志记录器的快捷方法
def setup_logging(app: FastAPI = None, **kwargs):
    """初始化日志配置的快捷方法"""
    return LoggingManager.setup_logging(app, **kwargs)


# 获取日志记录器的快捷方法
def get_logger(name: str, **extra) -> StructuredLogger:
    """获取日志记录器的快捷方法"""
    return LoggingManager.get_logger(name, **extra)


# 记录执行时间的装饰器快捷方法
def log_execution_time(logger: Optional[StructuredLogger] = None, level: str = "info"):
    """记录函数执行时间的装饰器快捷方法"""
    return LoggingManager.log_execution_time(logger, level)
