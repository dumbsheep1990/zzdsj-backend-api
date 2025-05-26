"""
助手模块：提供AI助手、智能体和问答助手等相关功能
"""

from fastapi import APIRouter

from app.api.frontend.assistants import assistant, manage, qa, agent

# 创建助手模块路由
router = APIRouter()

# 注册子路由
router.include_router(assistant.router, prefix="/ai", tags=["AI助手"])
router.include_router(manage.router, prefix="/manage", tags=["助手管理"])
router.include_router(qa.router, prefix="/qa", tags=["问答助手"])
router.include_router(agent.router, prefix="/agent", tags=["智能体服务"]) 