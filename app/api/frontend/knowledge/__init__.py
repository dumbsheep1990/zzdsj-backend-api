"""
知识库模块：提供知识库管理、文档处理和知识图谱功能
"""

from fastapi import APIRouter

from app.api.frontend.knowledge import manage, base, lightrag

# 创建知识库模块路由
router = APIRouter()

# 注册子路由
router.include_router(manage.router, prefix="/manage", tags=["知识库管理"])
router.include_router(base.router, prefix="/base", tags=["知识库基础服务"])
router.include_router(lightrag.router, prefix="/lightrag", tags=["LightRAG知识图谱"]) 