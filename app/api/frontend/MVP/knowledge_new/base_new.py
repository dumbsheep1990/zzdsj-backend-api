"""
统一的知识库基础API
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.deps import get_db, get_current_user
from app.services.knowledge import KnowledgeService
from app.schemas_new.knowledge_base import *
from app.utils.response import success_response, error_response

logger = logging.getLogger(__name__)
router = APIRouter()


# 依赖注入
def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)


# ========== 知识库管理 ==========
@router.post("/", response_model=BaseResponse)
async def create_knowledge_base(
        request: KnowledgeBaseCreate,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """创建知识库"""
    try:
        kb = await service.create_knowledge_base(request, current_user.id)
        return success_response(data=kb, message="知识库创建成功")
    except ValueError as e:
        return error_response(error=str(e), message="创建失败")
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        return error_response(error="内部错误", message="创建失败")


@router.get("/", response_model=BaseResponse)
async def list_knowledge_bases(
        page: int = 1,
        page_size: int = 20,
        type: Optional[KnowledgeBaseType] = None,
        search: Optional[str] = None,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """获取知识库列表"""
    try:
        result = await service.list_knowledge_bases(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            kb_type=type,
            search=search
        )
        return success_response(data=result)
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return error_response(error="获取失败")


@router.get("/{kb_id}", response_model=BaseResponse)
async def get_knowledge_base(
        kb_id: str,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """获取知识库详情"""
    try:
        kb = await service.get_knowledge_base(kb_id, current_user.id)
        if not kb:
            return error_response(error="知识库不存在", message="未找到")
        return success_response(data=kb)
    except Exception as e:
        logger.error(f"获取知识库失败: {e}")
        return error_response(error="获取失败")


@router.delete("/{kb_id}", response_model=BaseResponse)
async def delete_knowledge_base(
        kb_id: str,
        permanent: bool = False,
        background_tasks: BackgroundTasks,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """删除知识库"""
    try:
        # 添加后台清理任务
        if permanent:
            background_tasks.add_task(service.cleanup_knowledge_base, kb_id)

        result = await service.delete_knowledge_base(kb_id, current_user.id, permanent)
        return success_response(message="知识库删除成功")
    except ValueError as e:
        return error_response(error=str(e), message="删除失败")
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        return error_response(error="删除失败")


# ========== 文档管理 ==========
@router.post("/{kb_id}/documents", response_model=BaseResponse)
async def upload_document(
        kb_id: str,
        request: DocumentUpload,
        file: Optional[UploadFile] = File(None),
        background_tasks: BackgroundTasks,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """上传文档到知识库"""
    try:
        # 验证权限
        if not await service.check_write_permission(kb_id, current_user.id):
            return error_response(error="无写入权限", message="权限不足")

        # 处理文件上传
        if file:
            file_url = await service.upload_file(file, kb_id)
            request.file_url = file_url

        # 添加文档
        document = await service.add_document(kb_id, request)

        # 后台处理
        if request.auto_chunk or request.auto_vectorize:
            background_tasks.add_task(
                service.process_document,
                kb_id,
                document.id,
                request.auto_chunk,
                request.auto_vectorize,
                request.auto_extract
            )

        return success_response(data=document, message="文档上传成功")
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        return error_response(error="上传失败")


@router.delete("/{kb_id}/documents/{doc_id}", response_model=BaseResponse)
async def delete_document(
        kb_id: str,
        doc_id: str,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """删除文档"""
    try:
        # 验证权限
        if not await service.check_write_permission(kb_id, current_user.id):
            return error_response(error="无写入权限", message="权限不足")

        await service.delete_document(kb_id, doc_id)
        return success_response(message="文档删除成功")
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return error_response(error="删除失败")


# ========== 查询接口 ==========
@router.post("/query", response_model=BaseResponse)
async def query_knowledge(
        request: QueryRequest,
        service: KnowledgeService = Depends(get_knowledge_service),
        current_user=Depends(get_current_user)
):
    """查询知识库"""
    try:
        # 验证读取权限
        for kb_id in request.knowledge_base_ids:
            if not await service.check_read_permission(kb_id, current_user.id):
                return error_response(error=f"无权访问知识库 {kb_id}", message="权限不足")

        # 执行查询
        results = await service.query(request)
        return success_response(data=results)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return error_response(error="查询失败")