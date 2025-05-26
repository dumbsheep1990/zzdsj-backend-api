"""
前端API响应格式化工具
提供统一的响应格式，便于前端处理
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import status
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """
    前端API统一响应格式化工具
    提供标准化的成功/错误响应格式
    """
    
    @staticmethod
    def format_success(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = status.HTTP_200_OK,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        格式化成功响应
        
        参数:
            data: 返回的数据
            message: 成功信息
            status_code: HTTP状态码
            metadata: 元数据
            
        返回:
            Dict[str, Any]: 格式化的响应字典
        """
        response = {
            "code": 0,
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            response["metadata"] = metadata
            
        return response
    
    @staticmethod
    def format_error(
        message: str,
        code: int = 1000,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        格式化错误响应
        
        参数:
            message: 错误信息
            code: 错误代码
            status_code: HTTP状态码
            details: 错误详情
            
        返回:
            Dict[str, Any]: 格式化的错误响应字典
        """
        response = {
            "code": code,
            "success": False,
            "message": message,
            "data": None,
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            response["details"] = details
            
        return response
    
    @staticmethod
    def format_paginated(
        data: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        message: str = "查询成功"
    ) -> Dict[str, Any]:
        """
        格式化分页响应
        
        参数:
            data: 分页数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页大小
            message: 成功信息
            
        返回:
            Dict[str, Any]: 格式化的分页响应字典
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        
        pagination = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        return ResponseFormatter.format_success(
            data=data,
            message=message,
            metadata={"pagination": pagination}
        )
    
    # 便捷方法
    
    @staticmethod
    def success_response(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = status.HTTP_200_OK,
        metadata: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """返回JSONResponse格式的成功响应"""
        return JSONResponse(
            content=ResponseFormatter.format_success(data, message, status_code, metadata),
            status_code=status_code
        )
    
    @staticmethod
    def error_response(
        message: str,
        code: int = 1000,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """返回JSONResponse格式的错误响应"""
        return JSONResponse(
            content=ResponseFormatter.format_error(message, code, status_code, details),
            status_code=status_code
        )
    
    @staticmethod
    def not_found(
        message: str = "资源不存在",
        code: int = 1004
    ) -> Dict[str, Any]:
        """格式化资源不存在错误"""
        return ResponseFormatter.format_error(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def unauthorized(
        message: str = "未授权访问",
        code: int = 1001
    ) -> Dict[str, Any]:
        """格式化未授权错误"""
        return ResponseFormatter.format_error(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    @staticmethod
    def forbidden(
        message: str = "权限不足",
        code: int = 1003
    ) -> Dict[str, Any]:
        """格式化权限不足错误"""
        return ResponseFormatter.format_error(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    @staticmethod
    def validation_error(
        message: str = "数据验证失败",
        errors: List[Dict[str, Any]] = None,
        code: int = 1002
    ) -> Dict[str, Any]:
        """格式化数据验证错误"""
        return ResponseFormatter.format_error(
            message=message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"validation_errors": errors or []}
        ) 