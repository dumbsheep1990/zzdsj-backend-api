"""
知识库模块：提供知识库管理、文档处理和知识图谱功能
"""

from fastapi import APIRouter

from app.api.frontend.knowledge import manage, base, ai_knowledge_graph

# 创建知识库模块路由
router = APIRouter()

# 注册子路由
router.include_router(manage.router, prefix="/manage", tags=["知识库管理"])
router.include_router(base.router, prefix="/base", tags=["知识库基础服务"])
router.include_router(ai_knowledge_graph.router, prefix="/ai-knowledge-graph", tags=["AI知识图谱"]) 