"""
知识库基础服务API模块: 提供系统级别的知识库管理功能，包括创建、配置、监控、维护等
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

# 导入依赖
from app.utils.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.api.frontend.dependencies import ResponseFormatter

# 导入统一知识库管理工具
from app.tools.base.knowledge_management import (
    get_knowledge_manager,
    KnowledgeBaseConfig,
    DocumentProcessingConfig,
    KnowledgeBaseStatus
)

# 导入统一切分工具
from app.tools.base.document_chunking import (
    get_chunking_tool,
    ChunkingConfig
)

# 导入Pydantic模型
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic 模型定义
class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., description="知识库名称")
    description: str = Field("", description="知识库描述")
    chunking_strategy: str = Field("sentence", description="切分策略")
    chunk_size: int = Field(1000, description="切片大小")
    chunk_overlap: int = Field(200, description="切片重叠")
    language: str = Field("zh", description="语言")
    embedding_model: str = Field("text-embedding-ada-002", description="嵌入模型")
    vector_store: str = Field("agno", description="向量存储")
    is_active: bool = Field(True, description="是否激活")
    agno_config: Dict[str, Any] = Field(default_factory=dict, description="Agno配置")
    public_read: bool = Field(False, description="公开读权限")
    public_write: bool = Field(False, description="公开写权限")

class KnowledgeBaseUpdateRequest(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    chunking_strategy: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    language: Optional[str] = None
    embedding_model: Optional[str] = None
    is_active: Optional[bool] = None
    agno_config: Optional[Dict[str, Any]] = None

class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    auto_chunk: bool = Field(True, description="自动切分")
    auto_vectorize: bool = Field(True, description="自动向量化")
    auto_index: bool = Field(True, description="自动索引")

class DocumentSearchRequest(BaseModel):
    """文档搜索请求"""
    query: str = Field(..., description="搜索查询")
    top_k: int = Field(5, description="返回数量")
    filter_criteria: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    include_metadata: bool = Field(True, description="包含元数据")

class ChunkingConfigRequest(BaseModel):
    """切分配置请求"""
    strategy: str = Field("sentence", description="切分策略")
    chunk_size: int = Field(1000, description="切片大小")
    chunk_overlap: int = Field(200, description="切片重叠")
    language: str = Field("zh", description="语言")
    preserve_structure: bool = Field(True, description="保持结构")

# ========== 知识库管理接口 ==========

@router.post("/create", response_model=Dict[str, Any])
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的知识库
    """
    try:
        # 创建配置对象
        kb_config = KnowledgeBaseConfig(
            name=request.name,
            description=request.description,
            chunking_strategy=request.chunking_strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            language=request.language,
            embedding_model=request.embedding_model,
            vector_store=request.vector_store,
            is_active=request.is_active,
            agno_config=request.agno_config,
            public_read=request.public_read,
            public_write=request.public_write
        )
        
        # 创建知识库
        manager = get_knowledge_manager(db)
        result = await manager.create_knowledge_base(kb_config, current_user.id)
        
        logger.info(f"系统创建知识库: {request.name}, 用户: {current_user.id}")
        
        return ResponseFormatter.format_success(
            result,
            message="知识库创建成功"
        )
        
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建知识库失败: {str(e)}")

@router.get("/list", response_model=Dict[str, Any])
async def list_knowledge_bases(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    列出系统中的所有知识库
    """
    try:
        manager = get_knowledge_manager(db)
        all_kbs = await manager.list_knowledge_bases()
        
        # 过滤
        filtered_kbs = []
        for kb in all_kbs:
            # 状态过滤
            if status and kb.get("status") != status:
                continue
            
            # 搜索过滤
            if search and search.lower() not in kb.get("name", "").lower():
                continue
            
            filtered_kbs.append(kb)
        
        # 分页
        total = len(filtered_kbs)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_kbs = filtered_kbs[start:end]
        
        return ResponseFormatter.format_success({
            "knowledge_bases": paginated_kbs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }, message="获取知识库列表成功")
        
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取知识库列表失败: {str(e)}")

@router.get("/{kb_id}", response_model=Dict[str, Any])
async def get_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定知识库的详细信息
    """
    try:
        manager = get_knowledge_manager(db)
        kb_info = await manager.get_knowledge_base(kb_id)
        
        if not kb_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
        
        return ResponseFormatter.format_success(kb_info, message="获取知识库信息成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取知识库失败: {str(e)}")

@router.put("/{kb_id}", response_model=Dict[str, Any])
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新知识库配置
    """
    try:
        # 过滤非None值
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供更新内容")
        
        manager = get_knowledge_manager(db)
        result = await manager.update_knowledge_base(kb_id, updates)
        
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "更新失败"))
        
        logger.info(f"系统更新知识库: {kb_id}, 用户: {current_user.id}")
        
        return ResponseFormatter.format_success(result, message="知识库更新成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新知识库失败: {str(e)}")

@router.delete("/{kb_id}", response_model=Dict[str, Any])
async def delete_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除知识库
    """
    try:
        manager = get_knowledge_manager(db)
        result = await manager.delete_knowledge_base(kb_id)
        
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "删除失败"))
        
        logger.info(f"系统删除知识库: {kb_id}, 用户: {current_user.id}")
        
        return ResponseFormatter.format_success(result, message="知识库删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除知识库失败: {str(e)}")

# ========== 文档管理接口 ==========

@router.post("/{kb_id}/documents", response_model=Dict[str, Any])
async def add_document(
    kb_id: str,
    request: DocumentUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    向知识库添加文档
    """
    try:
        document = {
            "title": request.title,
            "content": request.content,
            "metadata": {
                **request.metadata,
                "uploaded_by": current_user.id,
                "uploaded_at": datetime.now().isoformat()
            }
        }
        
        config = DocumentProcessingConfig(
            auto_chunk=request.auto_chunk,
            auto_vectorize=request.auto_vectorize,
            auto_index=request.auto_index
        )
        
        manager = get_knowledge_manager(db)
        result = await manager.add_document(kb_id, document, config)
        
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "添加文档失败"))
        
        logger.info(f"系统添加文档到知识库: {kb_id}, 文档: {request.title}, 用户: {current_user.id}")
        
        return ResponseFormatter.format_success(result, message="文档添加成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"添加文档失败: {str(e)}")

@router.post("/{kb_id}/documents/upload", response_model=Dict[str, Any])
async def upload_document_file(
    kb_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    metadata: str = Form("{}"),
    auto_chunk: bool = Form(True),
    auto_vectorize: bool = Form(True),
    auto_index: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传文档文件到知识库
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 根据文件类型处理内容
        if file.content_type == "text/plain":
            content = file_content.decode("utf-8")
        elif file.content_type == "application/pdf":
            # 这里可以集成PDF解析
            content = "PDF内容解析功能待实现"
        else:
            content = file_content.decode("utf-8", errors="ignore")
        
        # 解析元数据
        try:
            metadata_dict = json.loads(metadata)
        except:
            metadata_dict = {}
        
        metadata_dict.update({
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": len(file_content),
            "uploaded_by": current_user.id,
            "uploaded_at": datetime.now().isoformat()
        })
        
        document = {
            "title": title,
            "content": content,
            "metadata": metadata_dict
        }
        
        config = DocumentProcessingConfig(
            auto_chunk=auto_chunk,
            auto_vectorize=auto_vectorize,
            auto_index=auto_index
        )
        
        manager = get_knowledge_manager(db)
        result = await manager.add_document(kb_id, document, config)
        
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "上传文档失败"))
        
        logger.info(f"系统上传文档文件到知识库: {kb_id}, 文件: {file.filename}, 用户: {current_user.id}")
        
        return ResponseFormatter.format_success(result, message="文档上传成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传文档失败: {str(e)}")

@router.post("/{kb_id}/search", response_model=Dict[str, Any])
async def search_documents(
    kb_id: str,
    request: DocumentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    在知识库中搜索文档
    """
    try:
        manager = get_knowledge_manager(db)
        results = await manager.search_documents(
            kb_id,
            request.query,
            request.filter_criteria,
            request.top_k
        )
        
        return ResponseFormatter.format_success({
            "results": results,
            "query": request.query,
            "total": len(results)
        }, message="搜索完成")
        
    except Exception as e:
        logger.error(f"搜索文档失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"搜索文档失败: {str(e)}")

@router.delete("/{kb_id}/documents/{document_id}", response_model=Dict[str, Any])
async def remove_document(
    kb_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从知识库中删除文档
    """
    try:
        manager = get_knowledge_manager(db)
        result = await manager.remove_document(kb_id, document_id)
        
        if result["status"] != "success":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "删除文档失败"))
        
        logger.info(f"系统删除文档: {document_id}, 知识库: {kb_id}, 用户: {current_user.id}")
        
        return ResponseFormatter.format_success(result, message="文档删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除文档失败: {str(e)}")

# ========== 切分工具接口 ==========

@router.get("/chunking/strategies", response_model=Dict[str, Any])
async def get_chunking_strategies():
    """
    获取可用的切分策略
    """
    try:
        chunking_tool = get_chunking_tool()
        strategies = chunking_tool.get_available_strategies()
        
        return ResponseFormatter.format_success({
            "strategies": strategies,
            "total": len(strategies)
        }, message="获取切分策略成功")
        
    except Exception as e:
        logger.error(f"获取切分策略失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取切分策略失败: {str(e)}") 