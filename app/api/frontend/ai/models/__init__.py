"""
AI模型API包
包含模型提供商和模型管理的API
"""

from fastapi import APIRouter
from app.api.frontend.ai.models.provider import router as provider_router
from app.api.frontend.ai.models.model import router as model_router

router = APIRouter(
    prefix="/ai/models",
    tags=["AI模型管理"]
)

# 包含子路由器
router.include_router(provider_router)
router.include_router(model_router) 