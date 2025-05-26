"""
重排序模型API桥接文件
(已弃用) - 请使用 app.api.frontend.search.rerank 模块
此文件仅用于向后兼容，所有新代码都应该使用新的模块
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
import logging
import re

from app.config import settings

# 导入新的重排序模型路由处理函数
from app.api.frontend.search.rerank import (
    list_rerank_models as new_list_rerank_models,
    get_rerank_model as new_get_rerank_model
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/rerank-models",
    tags=["rerank-models"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def list_rerank_models():
    """获取可用的重排序模型列表"""
    logger.warning(
        "使用已弃用的重排序模型端点: /api/rerank-models/，应使用新的端点: /api/frontend/search/rerank/"
    )
    return await new_list_rerank_models()

@router.get("/{model_id}")
async def get_rerank_model(model_id: str):
    """获取特定重排序模型的详细信息"""
    logger.warning(
        f"使用已弃用的重排序模型端点: /api/rerank-models/{model_id}，应使用新的端点: /api/frontend/search/rerank/{model_id}"
    )
    return await new_get_rerank_model(model_id)
