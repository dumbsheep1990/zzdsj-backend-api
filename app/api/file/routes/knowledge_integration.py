#!/usr/bin/env python3
"""
知识库集成接口
专门处理与知识库相关的文件操作，包括文档向量化、知识库同步等
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Path, BackgroundTasks
from datetime import datetime
import json

from app.middleware.file_upload_middleware import get_upload_middleware, UnifiedFileUploadMiddleware
from app.core.deps import get_current_user_optional
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 知识库文档操作接口 ==========

@router.post("/bases/{kb_id}/documents/upload", response_model=Dict[str, Any])
async def upload_knowledge_document(
    kb_id: str = Path(..., description="知识库ID"),
    file: UploadFile = File(..., description="上传的文档文件"),
    title: str = Form(None, description="文档标题"),
    category: str = Form("general", description="文档分类"),
    tags: str = Form("[]", description="文档标签（JSON字符串）"),
    auto_vectorize: bool = Form(True, description="是否自动向量化"),
    auto_index: bool = Form(True, description="是否自动建立索引"),
    chunk_strategy: str = Form("sentence", description="切分策略"),
    chunk_size: int = Form(1000, description="切片大小"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    上传文档到知识库
    
    - 专门用于知识库文档上传
    - 支持自动向量化和索引
    - 支持自定义切分策略
    - 与知识库系统深度集成
    """
    try:
        # 解析标签
        try:
            tags_list = json.loads(tags) if tags else []
        except:
            tags_list = []
        
        # 准备知识库专用元数据
        metadata = {
            "title": title or file.filename,
            "category": category,
            "tags": tags_list,
            "auto_vectorize": auto_vectorize,
            "auto_index": auto_index,
            "chunk_strategy": chunk_strategy,
            "chunk_size": chunk_size,
            "source_api": "backend_knowledge_integration",
            "kb_integration": True
        }
        
        # 确定用户ID
        effective_user_id = user_id or (str(current_user.id) if current_user else None)
        if effective_user_id:
            metadata["uploaded_by"] = effective_user_id
        
        # 使用统一中间件上传
        result = await middleware.upload_document(
            file=file,
            kb_id=kb_id,
            category=category,
            metadata=metadata,
            auto_vectorize=auto_vectorize,
            user_id=effective_user_id
        )
        
        logger.info(f"知识库文档上传: {file.filename} -> {result['file_id']}, 知识库: {kb_id}")
        
        return {
            "success": True,
            "data": {
                "file_id": result["file_id"],
                "document_id": result["file_id"],  # 兼容字段
                "filename": result["filename"],
                "title": metadata["title"],
                "category": category,
                "tags": tags_list,
                "kb_id": kb_id,
                "file_size": result["file_size"],
                "file_hash": result["file_hash"],
                "storage_path": result["storage_path"],
                "upload_time": result["upload_time"],
                "auto_vectorize": auto_vectorize,
                "auto_index": auto_index,
                "chunk_strategy": chunk_strategy,
                "chunk_size": chunk_size,
                "processing_status": "queued" if auto_vectorize else "completed"
            },
            "message": "知识库文档上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"知识库文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"知识库文档上传失败: {str(e)}")

@router.post("/bases/{kb_id}/documents/batch-upload", response_model=Dict[str, Any])
async def batch_upload_knowledge_documents(
    kb_id: str = Path(..., description="知识库ID"),
    files: List[UploadFile] = File(..., description="上传的文档文件列表"),
    category: str = Form("batch_upload", description="文档分类"),
    auto_vectorize: bool = Form(True, description="是否自动向量化"),
    auto_index: bool = Form(True, description="是否自动建立索引"),
    chunk_strategy: str = Form("sentence", description="切分策略"),
    chunk_size: int = Form(1000, description="切片大小"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    批量上传文档到知识库
    
    - 支持一次性上传多个文档
    - 统一的知识库处理配置
    - 详细的批量处理结果
    """
    try:
        # 确定用户ID
        effective_user_id = user_id or (str(current_user.id) if current_user else None)
        
        # 准备批量上传配置
        batch_metadata = {
            "category": category,
            "auto_vectorize": auto_vectorize,
            "auto_index": auto_index,
            "chunk_strategy": chunk_strategy,
            "chunk_size": chunk_size,
            "source_api": "backend_knowledge_batch_upload",
            "kb_integration": True
        }
        
        # 使用统一中间件批量上传
        result = await middleware.batch_upload_documents(
            files=files,
            kb_id=kb_id,
            category=category,
            auto_vectorize=auto_vectorize,
            user_id=effective_user_id
        )
        
        logger.info(f"知识库批量上传: {result['success_count']}/{result['total_files']}, 知识库: {kb_id}")
        
        return {
            "success": result["success"],
            "data": {
                "kb_id": kb_id,
                "total_files": result["total_files"],
                "success_count": result["success_count"],
                "error_count": result["error_count"],
                "results": result["results"],
                "category": category,
                "auto_vectorize": auto_vectorize,
                "auto_index": auto_index,
                "chunk_strategy": chunk_strategy,
                "chunk_size": chunk_size,
                "processing_status": "queued" if auto_vectorize else "completed"
            },
            "message": f"知识库批量上传完成: 成功{result['success_count']}个，失败{result['error_count']}个"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"知识库批量上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"知识库批量上传失败: {str(e)}")

# ========== 知识库文档删除接口 ==========

@router.delete("/bases/{kb_id}/documents/{file_id}", response_model=Dict[str, Any])
async def delete_knowledge_document(
    kb_id: str = Path(..., description="知识库ID"),
    file_id: str = Path(..., description="文件ID"),
    force: bool = Query(False, description="是否强制删除"),
    cleanup_vectors: bool = Query(True, description="是否清理向量数据"),
    user_id: str = Query(None, description="用户ID（后台调用时可指定）"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    从知识库删除文档
    
    - 删除文档文件
    - 清理向量数据
    - 更新知识库索引
    - 支持强制删除模式
    """
    try:
        # 检查文件是否属于指定知识库
        file_info = middleware.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 验证知识库归属
        if file_info.get("metadata", {}).get("kb_id") != kb_id:
            raise HTTPException(status_code=400, detail="文件不属于指定知识库")
        
        # 使用统一中间件删除文档
        result = await middleware.delete_document(file_id, force=force)
        
        # 确定操作用户
        effective_user_id = user_id or (str(current_user.id) if current_user else "system")
        
        logger.info(f"知识库文档删除: {file_id} - {'成功' if result['success'] else '失败'}, 知识库: {kb_id}")
        
        return {
            "success": result["success"],
            "data": {
                "kb_id": kb_id,
                "file_id": file_id,
                "deletion_details": result.get("deletion_results", {}),
                "force_delete": force,
                "cleanup_vectors": cleanup_vectors,
                "operated_by": effective_user_id
            },
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"知识库文档删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"知识库文档删除失败: {str(e)}")

# ========== 知识库向量化管理接口 ==========

@router.post("/bases/{kb_id}/documents/{file_id}/vectorize", response_model=Dict[str, Any])
async def vectorize_document(
    kb_id: str = Path(..., description="知识库ID"),
    file_id: str = Path(..., description="文件ID"),
    force_revectorize: bool = Form(False, description="是否强制重新向量化"),
    chunk_strategy: str = Form("sentence", description="切分策略"),
    chunk_size: int = Form(1000, description="切片大小"),
    chunk_overlap: int = Form(200, description="切片重叠"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    对文档进行向量化处理
    
    - 支持重新向量化
    - 自定义切分策略
    - 异步处理任务
    """
    try:
        # 检查文件是否存在
        file_info = middleware.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 验证知识库归属
        if file_info.get("metadata", {}).get("kb_id") != kb_id:
            raise HTTPException(status_code=400, detail="文件不属于指定知识库")
        
        # 确定操作用户
        effective_user_id = user_id or (str(current_user.id) if current_user else "system")
        
        # TODO: 实现向量化任务
        # 这里应该启动异步向量化任务
        
        # 添加后台任务
        def vectorization_task():
            logger.info(f"开始向量化任务: file_id={file_id}, kb_id={kb_id}")
            # TODO: 实际的向量化处理逻辑
            
        background_tasks.add_task(vectorization_task)
        
        logger.info(f"启动文档向量化: {file_id}, 知识库: {kb_id}, 操作者: {effective_user_id}")
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "file_id": file_id,
                "task_status": "queued",
                "force_revectorize": force_revectorize,
                "chunk_strategy": chunk_strategy,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "started_by": effective_user_id,
                "started_at": datetime.now().isoformat()
            },
            "message": "向量化任务已启动"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动向量化任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动向量化任务失败: {str(e)}")

@router.get("/bases/{kb_id}/documents/{file_id}/vectorization-status", response_model=Dict[str, Any])
async def get_vectorization_status(
    kb_id: str = Path(..., description="知识库ID"),
    file_id: str = Path(..., description="文件ID"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware)
):
    """
    获取文档向量化状态
    
    - 查询向量化进度
    - 检查向量化结果
    """
    try:
        # 检查文件是否存在
        file_info = middleware.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # TODO: 实现向量化状态查询
        # 这里应该查询实际的向量化状态
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "file_id": file_id,
                "vectorization_status": "pending",  # pending, processing, completed, failed
                "progress": 0,
                "total_chunks": 0,
                "processed_chunks": 0,
                "failed_chunks": 0,
                "started_at": None,
                "completed_at": None,
                "error_message": None
            },
            "message": "向量化状态查询功能待实现"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询向量化状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询向量化状态失败: {str(e)}")

# ========== 知识库同步接口 ==========

@router.post("/bases/{kb_id}/sync", response_model=Dict[str, Any])
async def sync_knowledge_base(
    kb_id: str = Path(..., description="知识库ID"),
    sync_type: str = Form("incremental", description="同步类型: incremental, full"),
    include_vectors: bool = Form(True, description="是否包含向量数据"),
    include_metadata: bool = Form(True, description="是否包含元数据"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    同步知识库数据
    
    - 支持增量同步和全量同步
    - 同步文件、向量和元数据
    - 异步处理任务
    """
    try:
        # 确定操作用户
        effective_user_id = user_id or (str(current_user.id) if current_user else "system")
        
        # TODO: 实现知识库同步
        # 这里应该启动异步同步任务
        
        # 添加后台任务
        def sync_task():
            logger.info(f"开始知识库同步: kb_id={kb_id}, sync_type={sync_type}")
            # TODO: 实际的同步处理逻辑
            
        background_tasks.add_task(sync_task)
        
        logger.info(f"启动知识库同步: {kb_id}, 类型: {sync_type}, 操作者: {effective_user_id}")
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "sync_type": sync_type,
                "task_status": "queued",
                "include_vectors": include_vectors,
                "include_metadata": include_metadata,
                "started_by": effective_user_id,
                "started_at": datetime.now().isoformat()
            },
            "message": "知识库同步任务已启动"
        }
        
    except Exception as e:
        logger.error(f"启动知识库同步失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动知识库同步失败: {str(e)}")

# ========== 知识库统计接口 ==========

@router.get("/bases/{kb_id}/stats", response_model=Dict[str, Any])
async def get_knowledge_base_stats(
    kb_id: str = Path(..., description="知识库ID"),
    include_file_details: bool = Query(False, description="是否包含文件详情"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware)
):
    """
    获取知识库统计信息
    
    - 文档数量统计
    - 存储空间统计
    - 向量化状态统计
    """
    try:
        # TODO: 实现知识库统计
        # 这里需要查询知识库的实际统计数据
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "total_documents": 0,
                "total_size": 0,
                "vectorized_documents": 0,
                "pending_vectorization": 0,
                "failed_vectorization": 0,
                "by_category": {},
                "by_file_type": {},
                "storage_breakdown": {
                    "files": 0,
                    "vectors": 0,
                    "metadata": 0
                },
                "last_updated": datetime.now().isoformat(),
                "file_details": [] if include_file_details else None
            },
            "message": "知识库统计功能待实现"
        }
        
    except Exception as e:
        logger.error(f"获取知识库统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识库统计失败: {str(e)}")

# ========== 知识库维护接口 ==========

@router.post("/bases/{kb_id}/rebuild", response_model=Dict[str, Any])
async def rebuild_knowledge_base(
    kb_id: str = Path(..., description="知识库ID"),
    rebuild_type: str = Form("index", description="重建类型: index, vectors, all"),
    force: bool = Form(False, description="是否强制重建"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    重建知识库
    
    - 重建索引
    - 重建向量数据
    - 全量重建
    """
    try:
        # 确定操作用户
        effective_user_id = user_id or (str(current_user.id) if current_user else "system")
        
        # TODO: 实现知识库重建
        # 这里应该启动异步重建任务
        
        # 添加后台任务
        def rebuild_task():
            logger.info(f"开始知识库重建: kb_id={kb_id}, rebuild_type={rebuild_type}")
            # TODO: 实际的重建处理逻辑
            
        background_tasks.add_task(rebuild_task)
        
        logger.info(f"启动知识库重建: {kb_id}, 类型: {rebuild_type}, 操作者: {effective_user_id}")
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "rebuild_type": rebuild_type,
                "task_status": "queued",
                "force": force,
                "started_by": effective_user_id,
                "started_at": datetime.now().isoformat()
            },
            "message": "知识库重建任务已启动"
        }
        
    except Exception as e:
        logger.error(f"启动知识库重建失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动知识库重建失败: {str(e)}") 