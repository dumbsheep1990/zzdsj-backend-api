"""
V1 知识库API - 用户服务接口
为用户提供知识库相关的对外服务功能
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
import io
from datetime import datetime

# 导入依赖
from app.utils.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User

# 导入统一知识库管理工具
from app.tools.base.knowledge_management import (
    get_knowledge_manager,
    KnowledgeBaseConfig,
    DocumentProcessingConfig
)

# 导入统一切分工具
from app.tools.base.document_chunking import (
    get_chunking_tool,
    ChunkingConfig
)

# 导入Pydantic模型
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Base"])

# Pydantic 模型定义
class CreateKnowledgeBaseRequest(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., description="知识库名称", min_length=1, max_length=100)
    description: str = Field("", description="知识库描述", max_length=500)
    language: str = Field("zh", description="主要语言", regex="^(zh|en)$")
    
    # 可选的高级配置
    chunking_strategy: Optional[str] = Field(None, description="切分策略")
    chunk_size: Optional[int] = Field(None, description="切片大小", ge=100, le=5000)
    chunk_overlap: Optional[int] = Field(None, description="切片重叠", ge=0, le=1000)

class UploadDocumentRequest(BaseModel):
    """上传文档请求"""
    title: str = Field(..., description="文档标题", min_length=1, max_length=200)
    content: str = Field(..., description="文档内容", min_length=1)
    tags: List[str] = Field(default_factory=list, description="文档标签")
    category: str = Field("", description="文档分类", max_length=50)

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询", min_length=1, max_length=500)
    top_k: int = Field(5, description="返回数量", ge=1, le=20)
    category: Optional[str] = Field(None, description="限定分类")
    tags: Optional[List[str]] = Field(None, description="限定标签")

class UpdateKnowledgeBaseRequest(BaseModel):
    """更新知识库请求"""
    name: Optional[str] = Field(None, description="知识库名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="知识库描述", max_length=500)

# ========== 知识库基础操作 ==========

@router.post("/", response_model=Dict[str, Any])
async def create_knowledge_base(
    request: CreateKnowledgeBaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的知识库
    """
    try:
        # 构建配置
        kb_config = KnowledgeBaseConfig(
            name=request.name,
            description=request.description,
            language=request.language,
            chunking_strategy=request.chunking_strategy or "sentence",
            chunk_size=request.chunk_size or 1000,
            chunk_overlap=request.chunk_overlap or 200,
        )
        
        # 创建知识库
        manager = get_knowledge_manager(db)
        result = await manager.create_knowledge_base(kb_config, current_user.id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
        
        logger.info(f"用户 {current_user.id} 创建知识库: {request.name}")
        
        return {
            "success": True,
            "data": {
                "kb_id": result["kb_id"],
                "name": result["name"],
                "description": result["description"],
                "status": result["status"],
                "created_at": result["created_at"]
            },
            "message": "知识库创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建知识库失败")

@router.get("/", response_model=Dict[str, Any])
async def list_my_knowledge_bases(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的知识库列表
    """
    try:
        manager = get_knowledge_manager(db)
        all_kbs = await manager.list_knowledge_bases(current_user.id)
        
        # 搜索过滤
        if search:
            all_kbs = [
                kb for kb in all_kbs 
                if search.lower() in kb.get("name", "").lower() or 
                   search.lower() in kb.get("description", "").lower()
            ]
        
        # 分页
        total = len(all_kbs)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_kbs = all_kbs[start:end]
        
        # 简化返回数据
        simplified_kbs = []
        for kb in paginated_kbs:
            simplified_kbs.append({
                "kb_id": kb["kb_id"],
                "name": kb["name"],
                "description": kb["description"],
                "document_count": kb.get("document_count", 0),
                "created_at": kb.get("created_at"),
                "last_updated": kb.get("last_updated")
            })
        
        return {
            "success": True,
            "data": {
                "knowledge_bases": simplified_kbs,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            },
            "message": "获取知识库列表成功"
        }
        
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识库列表失败")

@router.get("/{kb_id}", response_model=Dict[str, Any])
async def get_knowledge_base_info(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取知识库详细信息
    """
    try:
        manager = get_knowledge_manager(db)
        kb_info = await manager.get_knowledge_base(kb_id)
        
        if not kb_info:
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 简化返回数据，隐藏敏感配置
        simplified_info = {
            "kb_id": kb_info["kb_id"],
            "name": kb_info["name"],
            "description": kb_info["description"],
            "document_count": kb_info.get("document_count", 0),
            "chunk_count": kb_info.get("chunk_count", 0),
            "created_at": kb_info.get("created_at"),
            "last_updated": kb_info.get("last_updated"),
            "language": kb_info.get("language", "zh"),
            "chunking_strategy": kb_info.get("chunking_strategy", "sentence")
        }
        
        return {
            "success": True,
            "data": simplified_info,
            "message": "获取知识库信息成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识库信息失败")

@router.put("/{kb_id}", response_model=Dict[str, Any])
async def update_knowledge_base_info(
    kb_id: str,
    request: UpdateKnowledgeBaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新知识库基本信息
    """
    try:
        # 过滤有效更新字段
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供更新内容")
        
        manager = get_knowledge_manager(db)
        result = await manager.update_knowledge_base(kb_id, updates)
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
        
        logger.info(f"用户 {current_user.id} 更新知识库: {kb_id}")
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "updated_at": result["updated_at"]
            },
            "message": "知识库更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新知识库失败")

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
            raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
        
        logger.info(f"用户 {current_user.id} 删除知识库: {kb_id}")
        
        return {
            "success": True,
            "data": {"kb_id": kb_id},
            "message": "知识库删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除知识库失败")

# ========== 文档管理 ==========

@router.post("/{kb_id}/documents", response_model=Dict[str, Any])
async def upload_document(
    kb_id: str,
    request: UploadDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    向知识库上传文档
    """
    try:
        # 构建文档数据
        document = {
            "title": request.title,
            "content": request.content,
            "metadata": {
                "tags": request.tags,
                "category": request.category,
                "uploaded_by": current_user.id,
                "uploaded_at": datetime.now().isoformat()
            }
        }
        
        # 使用默认处理配置
        config = DocumentProcessingConfig(
            auto_chunk=True,
            auto_vectorize=True,
            auto_index=True
        )
        
        manager = get_knowledge_manager(db)
        result = await manager.add_document(kb_id, document, config)
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("error", "文档上传失败"))
        
        logger.info(f"用户 {current_user.id} 上传文档到知识库 {kb_id}: {request.title}")
        
        return {
            "success": True,
            "data": {
                "document_id": result["document_id"],
                "chunks": result["chunks"],
                "processing_time": result.get("processing_time", 0)
            },
            "message": "文档上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文档上传失败")

@router.post("/{kb_id}/documents/upload-file", response_model=Dict[str, Any])
async def upload_document_file(
    kb_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    tags: str = Form("[]"),
    category: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传文档文件
    """
    try:
        # 文件大小限制 (10MB)
        max_size = 10 * 1024 * 1024
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(status_code=413, detail="文件大小超过限制(10MB)")
        
        # 支持的文件类型
        supported_types = ["text/plain", "application/pdf", "text/markdown"]
        if file.content_type not in supported_types:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 解析内容
        if file.content_type == "text/plain":
            content = file_content.decode("utf-8")
        elif file.content_type == "text/markdown":
            content = file_content.decode("utf-8")
        else:
            # PDF 解析（简化版本）
            content = "PDF内容解析功能待完善"
        
        # 解析标签
        try:
            tags_list = json.loads(tags) if tags else []
        except:
            tags_list = []
        
        # 构建文档
        document = {
            "title": title,
            "content": content,
            "metadata": {
                "tags": tags_list,
                "category": category,
                "file_name": file.filename,
                "file_type": file.content_type,
                "file_size": len(file_content),
                "uploaded_by": current_user.id,
                "uploaded_at": datetime.now().isoformat()
            }
        }
        
        config = DocumentProcessingConfig()
        manager = get_knowledge_manager(db)
        result = await manager.add_document(kb_id, document, config)
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("error", "文件上传失败"))
        
        logger.info(f"用户 {current_user.id} 上传文件到知识库 {kb_id}: {file.filename}")
        
        return {
            "success": True,
            "data": {
                "document_id": result["document_id"],
                "chunks": result["chunks"],
                "file_name": file.filename
            },
            "message": "文件上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件上传失败")

@router.delete("/{kb_id}/documents/{document_id}", response_model=Dict[str, Any])
async def remove_document(
    kb_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除文档
    """
    try:
        manager = get_knowledge_manager(db)
        result = await manager.remove_document(kb_id, document_id)
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("error", "文档删除失败"))
        
        logger.info(f"用户 {current_user.id} 删除文档: {document_id}")
        
        return {
            "success": True,
            "data": {"document_id": document_id},
            "message": "文档删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文档删除失败")

# ========== 搜索功能 ==========

@router.post("/{kb_id}/search", response_model=Dict[str, Any])
async def search_knowledge_base(
    kb_id: str,
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    在知识库中搜索
    """
    try:
        # 构建过滤条件
        filter_criteria = {}
        if request.category:
            filter_criteria["category"] = request.category
        if request.tags:
            filter_criteria["tags"] = {"$in": request.tags}
        
        manager = get_knowledge_manager(db)
        results = await manager.search_documents(
            kb_id,
            request.query,
            filter_criteria or None,
            request.top_k
        )
        
        # 简化搜索结果
        simplified_results = []
        for result in results:
            simplified_results.append({
                "content": result["content"],
                "score": result["score"],
                "metadata": {
                    "tags": result["metadata"].get("tags", []),
                    "category": result["metadata"].get("category", ""),
                    "document_id": result["metadata"].get("document_id")
                }
            })
        
        logger.info(f"用户 {current_user.id} 在知识库 {kb_id} 搜索: {request.query}")
        
        return {
            "success": True,
            "data": {
                "results": simplified_results,
                "query": request.query,
                "total": len(simplified_results),
                "kb_id": kb_id
            },
            "message": "搜索完成"
        }
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索失败")

# ========== 工具和配置 ==========

@router.get("/tools/chunking-strategies", response_model=Dict[str, Any])
async def get_available_chunking_strategies():
    """
    获取可用的文档切分策略
    """
    try:
        chunking_tool = get_chunking_tool()
        strategies = chunking_tool.get_available_strategies()
        
        # 简化策略信息，只保留用户需要的
        user_strategies = []
        for strategy in strategies:
            user_strategies.append({
                "value": strategy["value"],
                "label": strategy["label"],
                "description": strategy["description"]
            })
        
        return {
            "success": True,
            "data": {
                "strategies": user_strategies,
                "default": "sentence"
            },
            "message": "获取切分策略成功"
        }
        
    except Exception as e:
        logger.error(f"获取切分策略失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取切分策略失败")

@router.post("/tools/preview-chunking", response_model=Dict[str, Any])
async def preview_document_chunking(
    content: str = Form(..., description="文档内容"),
    strategy: str = Form("sentence", description="切分策略"),
    chunk_size: int = Form(1000, description="切片大小"),
    chunk_overlap: int = Form(200, description="切片重叠"),
    language: str = Form("zh", description="语言"),
    current_user: User = Depends(get_current_user)
):
    """
    预览文档切分效果
    """
    try:
        # 内容长度限制
        if len(content) > 10000:
            raise HTTPException(status_code=400, detail="预览内容过长，请限制在10000字符以内")
        
        chunking_tool = get_chunking_tool()
        
        # 创建切分配置
        chunk_config = ChunkingConfig(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            language=language
        )
        
        # 执行切分
        result = chunking_tool.chunk_document(content, chunk_config)
        
        # 限制预览数量
        preview_chunks = result.chunks[:3]  # 只显示前3个切片
        
        return {
            "success": True,
            "data": {
                "preview_chunks": [
                    {
                        "content": chunk.content[:200] + ("..." if len(chunk.content) > 200 else ""),
                        "char_count": len(chunk.content)
                    }
                    for chunk in preview_chunks
                ],
                "total_chunks": result.total_chunks,
                "strategy_used": result.strategy_used,
                "average_chunk_size": result.total_chars // result.total_chunks if result.total_chunks > 0 else 0
            },
            "message": "预览生成成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览切分失败: {str(e)}")
        raise HTTPException(status_code=500, detail="预览生成失败")

# ========== 外部创建知识库接口 ==========

@router.post("/create-or-bind", response_model=Dict[str, Any])
async def create_or_bind_knowledge_base(
    name: str = Form(..., description="知识库名称"),
    description: str = Form("", description="知识库描述"),
    bind_existing: bool = Form(False, description="是否绑定现有知识库"),
    existing_kb_id: Optional[str] = Form(None, description="现有知识库ID"),
    language: str = Form("zh", description="语言"),
    content: Optional[str] = Form(None, description="初始文档内容"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为外部数据提交创建知识库或绑定现有知识库
    """
    try:
        manager = get_knowledge_manager(db)
        
        if bind_existing and existing_kb_id:
            # 绑定现有知识库
            kb_info = await manager.get_knowledge_base(existing_kb_id)
            if not kb_info:
                raise HTTPException(status_code=404, detail="指定的知识库不存在")
            
            kb_id = existing_kb_id
            message = "绑定现有知识库成功"
            
        else:
            # 创建新知识库
            kb_config = KnowledgeBaseConfig(
                name=name,
                description=description,
                language=language
            )
            
            result = await manager.create_knowledge_base(kb_config, current_user.id)
            
            if result.get("status") == "error":
                raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
            
            kb_id = result["kb_id"]
            message = "知识库创建成功"
        
        # 如果提供了初始内容，添加文档
        document_result = None
        if content and content.strip():
            document = {
                "title": f"{name} - 初始文档",
                "content": content,
                "metadata": {
                    "type": "initial",
                    "created_by": current_user.id,
                    "created_at": datetime.now().isoformat()
                }
            }
            
            document_result = await manager.add_document(kb_id, document)
        
        logger.info(f"用户 {current_user.id} 创建/绑定知识库: {name} (ID: {kb_id})")
        
        response_data = {
            "kb_id": kb_id,
            "name": name,
            "description": description,
            "created_new": not bind_existing,
        }
        
        if document_result:
            response_data["initial_document"] = {
                "document_id": document_result["document_id"],
                "chunks": document_result.get("chunks", 0)
            }
        
        return {
            "success": True,
            "data": response_data,
            "message": message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建/绑定知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail="操作失败") 