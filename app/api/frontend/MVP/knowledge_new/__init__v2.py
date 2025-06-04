from fastapi import APIRouter
from .base import router as base_router
from .lightrag import router as lightrag_router

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# 注册子路由
router.include_router(base_router)
router.include_router(lightrag_router, prefix="/lightrag", tags=["LightRAG"])