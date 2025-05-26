"""
搜索模块：提供统一的混合检索和搜索相关功能
"""

from fastapi import APIRouter

from app.api.frontend.search import main
from app.api.frontend.search import rerank
from app.api.frontend.search import advanced_retrieval

# 创建搜索模块路由
router = APIRouter()

# 注册子路由
router.include_router(main.router, prefix="", tags=["搜索管理"])
router.include_router(rerank.router, prefix="/rerank", tags=["重排序模型"])
router.include_router(advanced_retrieval.router, prefix="/advanced", tags=["高级检索"]) 