"""
搜索API模块: 提供统一的混合检索接口
支持跨知识库搜索、多引擎搜索、自定义参数
能够自动检测环境并适配最佳检索策略
(桥接文件 - 仅用于向后兼容，所有新代码都应该使用app.api.frontend.search.main模块)
"""

import logging
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
import time

from app.services.hybrid_search_service import get_hybrid_search_service, SearchConfig
from app.services.unified_knowledge_service import get_unified_knowledge_service
from app.schemas.search import SearchRequest as SchemaSearchRequest, SearchResponse as SchemaSearchResponse, SearchResultItem, SearchStrategy
from app.utils.storage_detector import StorageDetector
from app.utils.database import get_db

# 导入新的搜索路由处理函数
from app.api.frontend.search.main import (
    search as new_search,
    list_searchable_knowledge_bases as new_list_searchable_knowledge_bases,
    reindex_knowledge_base as new_reindex_knowledge_base,
    get_storage_info as new_get_storage_info,
    convert_search_request as new_convert_search_request,
    SearchRequest,
    SearchResult,
    SearchResponse
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/search",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    混合搜索接口，支持跨知识库搜索、混合检索和参数自定义
    具备自动检测环境并选择最佳搜索策略的能力
    """
    logger.warning(
        "使用已弃用的搜索端点: /api/search/，应使用新的端点: /api/frontend/search/"
    )
    return await new_search(request=request, db=db)

@router.get("/knowledge_bases", response_model=List[Dict[str, Any]])
async def list_searchable_knowledge_bases(
    db: Session = Depends(get_db)
):
    """
    获取可搜索的知识库列表
    """
    logger.warning(
        "使用已弃用的搜索端点: /api/search/knowledge_bases，应使用新的端点: /api/frontend/search/knowledge_bases"
    )
    return await new_list_searchable_knowledge_bases(db=db)

@router.post("/reindex_knowledge_base", status_code=status.HTTP_202_ACCEPTED)
async def reindex_knowledge_base(
    kb_id: str = Body(..., embed=True),
    rebuild_vectors: bool = Body(False, embed=True),
    force_recreate: bool = Body(False, embed=True),
    db: Session = Depends(get_db)
):
    """
    重新索引知识库，可选是否重建向量
    """
    logger.warning(
        "使用已弃用的搜索端点: /api/search/reindex_knowledge_base，应使用新的端点: /api/frontend/search/reindex_knowledge_base"
    )
    return await new_reindex_knowledge_base(
        kb_id=kb_id, 
        rebuild_vectors=rebuild_vectors, 
        force_recreate=force_recreate, 
        db=db
    )

@router.get("/storage_info", response_model=Dict[str, Any])
async def get_storage_info():
    """
    获取当前环境的存储引擎信息和可用状态
    """
    logger.warning(
        "使用已弃用的搜索端点: /api/search/storage_info，应使用新的端点: /api/frontend/search/storage_info"
    )
    return await new_get_storage_info()

@router.post("/schema_adapter")
async def convert_search_request(
    request: SchemaSearchRequest
) -> Dict[str, Any]:
    """
    将标准搜索请求模式转换为内部搜索请求
    这对于前端或外部系统集成很有用
    """
    logger.warning(
        "使用已弃用的搜索端点: /api/search/schema_adapter，应使用新的端点: /api/frontend/search/schema_adapter"
    )
    return await new_convert_search_request(request=request)
