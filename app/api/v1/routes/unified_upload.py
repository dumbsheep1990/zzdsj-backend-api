#!/usr/bin/env python3
"""
统一文件上传API路由
基于统一文件上传中间件，提供标准化的文件上传接口
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from datetime import datetime

from app.middleware.file_upload_middleware import get_upload_middleware, UnifiedFileUploadMiddleware
from app.core.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload", tags=["unified_upload"])

# ========== 文档上传接口 ==========

@router.post("/documents", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(..., description="上传的文档文件"),
    kb_id: str = Form(..., description="知识库ID"),
    title: str = Form(None, description="文档标题"),
    category: str = Form("general", description="文档分类"),
    auto_vectorize: bool = Form(True, description="是否自动向量化"),
    metadata: str = Form("{}", description="额外元数据(JSON字符串)"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    统一文档上传接口
    
    - 自动文件类型验证
    - 统一文件ID管理
    - 集成MinIO存储
    - 支持自动向量化
    """
    try:
        # 解析额外元数据
        import json
        try:
            extra_metadata = json.loads(metadata)
        except:
            extra_metadata = {}
        
        # 添加标题信息
        if title:
            extra_metadata["title"] = title
        
        # 使用统一中间件上传
        result = await middleware.upload_document(
            file=file,
            kb_id=kb_id,
            category=category,
            metadata=extra_metadata,
            auto_vectorize=auto_vectorize,
            user_id=str(current_user.id)
        )
        
        logger.info(f"用户{current_user.id}上传文档: {file.filename} -> {result['file_id']}")
        
        return {
            "success": True,
            "data": result,
            "message": "文档上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"统一文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

@router.post("/documents/batch", response_model=Dict[str, Any])
async def batch_upload_documents(
    files: List[UploadFile] = File(..., description="上传的文档文件列表"),
    kb_id: str = Form(..., description="知识库ID"),
    category: str = Form("batch_upload", description="文档分类"),
    auto_vectorize: bool = Form(True, description="是否自动向量化"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    批量文档上传接口
    
    - 支持多文件同时上传
    - 并行处理提高效率
    - 详细的上传结果报告
    """
    try:
        # 使用统一中间件批量上传
        result = await middleware.batch_upload_documents(
            files=files,
            kb_id=kb_id,
            category=category,
            auto_vectorize=auto_vectorize,
            user_id=str(current_user.id)
        )
        
        logger.info(f"用户{current_user.id}批量上传: {result['success_count']}/{result['total_files']}")
        
        return {
            "success": result["success"],
            "data": result,
            "message": f"批量上传完成: 成功{result['success_count']}个，失败{result['error_count']}个"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量文档上传失败: {str(e)}")

# ========== 用户文件上传接口 ==========

@router.post("/user-files", response_model=Dict[str, Any])
async def upload_user_file(
    file: UploadFile = File(..., description="用户文件"),
    folder: str = Form("user_files", description="存储文件夹"),
    max_size_mb: int = Form(10, description="最大文件大小(MB)"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    用户文件上传接口
    
    - 支持头像、附件等用户文件
    - 灵活的文件类型限制
    - 自定义存储文件夹
    """
    try:
        # 使用统一中间件上传用户文件
        result = await middleware.upload_user_file(
            file=file,
            folder=folder,
            user_id=str(current_user.id),
            max_size_mb=max_size_mb
        )
        
        logger.info(f"用户{current_user.id}上传文件: {file.filename} -> {result['file_id']}")
        
        return {
            "success": True,
            "data": result,
            "message": "文件上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"用户文件上传失败: {str(e)}")

@router.post("/avatars", response_model=Dict[str, Any])
async def upload_avatar(
    avatar: UploadFile = File(..., description="头像文件"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    用户头像上传接口
    
    - 专用头像上传
    - 自动图片类型验证
    - 5MB大小限制
    """
    try:
        # 头像专用类型限制
        allowed_types = [
            "image/jpeg", 
            "image/jpg", 
            "image/png", 
            "image/gif",
            "image/webp"
        ]
        
        # 使用统一中间件上传头像
        result = await middleware.upload_user_file(
            file=avatar,
            folder="avatars",
            user_id=str(current_user.id),
            allowed_types=allowed_types,
            max_size_mb=5
        )
        
        logger.info(f"用户{current_user.id}上传头像: {avatar.filename} -> {result['file_id']}")
        
        return {
            "success": True,
            "data": result,
            "message": "头像上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"头像上传失败: {str(e)}")

# ========== 文件删除接口 ==========

@router.delete("/documents/{file_id}", response_model=Dict[str, Any])
async def delete_document(
    file_id: str,
    force: bool = Query(False, description="是否强制删除"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    删除文档（关联删除）
    
    - 删除MinIO中的文件
    - 删除向量数据库中的向量
    - 删除PostgreSQL中的记录
    """
    try:
        # 检查文件权限（简化版本）
        file_info = middleware.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 使用统一中间件删除文档
        result = await middleware.delete_document(file_id, force=force)
        
        logger.info(f"用户{current_user.id}删除文档: {file_id} - {'成功' if result['success'] else '失败'}")
        
        return {
            "success": result["success"],
            "data": result,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")

@router.delete("/user-files/{file_id}", response_model=Dict[str, Any])
async def delete_user_file(
    file_id: str,
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    删除用户文件
    
    - 删除用户上传的文件
    - 简单的权限检查
    """
    try:
        # 检查文件权限（简化版本）
        file_info = middleware.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 使用统一中间件删除用户文件
        result = await middleware.delete_user_file(file_id)
        
        logger.info(f"用户{current_user.id}删除文件: {file_id} - {'成功' if result['success'] else '失败'}")
        
        return {
            "success": result["success"],
            "data": result,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除用户文件失败: {str(e)}")

# ========== 文件信息接口 ==========

@router.get("/files/{file_id}", response_model=Dict[str, Any])
async def get_file_info(
    file_id: str,
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user)
):
    """
    获取文件信息
    
    - 统一的文件信息查询
    - 包含存储状态和元数据
    """
    try:
        file_info = middleware.get_file_info(file_id)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return {
            "success": True,
            "data": file_info,
            "message": "获取文件信息成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")

@router.get("/supported-types", response_model=Dict[str, Any])
async def get_supported_file_types(
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware)
):
    """
    获取支持的文件类型
    
    - 返回所有支持的文件类型
    - 按分类组织
    """
    try:
        supported_types = middleware.get_supported_types()
        
        return {
            "success": True,
            "data": supported_types,
            "message": "获取支持的文件类型成功"
        }
        
    except Exception as e:
        logger.error(f"获取支持的文件类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取支持的文件类型失败: {str(e)}") 