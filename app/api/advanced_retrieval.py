"""
高级检索API桥接文件
(已弃用) - 请使用 app.api.frontend.search.advanced_retrieval 模块
此文件仅用于向后兼容，所有新代码都应该使用新的模块
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
import logging
from sqlalchemy.orm import Session

from app.services.advanced_retrieval_service import get_advanced_retrieval_service, AdvancedRetrievalConfig, SourceWeight, FusionConfig, RerankConfig
from app.utils.database import get_db

# 导入新的高级检索路由处理函数
from app.api.frontend.search.advanced_retrieval import (
    RetrievalRequest,
    advanced_search as new_advanced_search
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/advanced-retrieval",
    tags=["advanced-retrieval"],
    responses={404: {"description": "Not found"}},
)

@router.post("/search")
async def advanced_search(
    request: RetrievalRequest,
    db: Session = Depends(get_db)
):
    """执行高级检索"""
    logger.warning(
        "使用已弃用的高级检索端点: /api/advanced-retrieval/search，应使用新的端点: /api/frontend/search/advanced/search"
    )
    return await new_advanced_search(request=request, db=db)
