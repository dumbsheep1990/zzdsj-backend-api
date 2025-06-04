"""
助手模块路由注册
"""
from fastapi import APIRouter
from app.api.v1.assistants import assistant, agent, qa


def register_assistant_routes() -> APIRouter:
    """注册所有助手相关路由"""
    router = APIRouter(prefix="/assistants", tags=["assistants"])

    # 注册子路由
    router.include_router(assistant.router, tags=["AI助手"])
    router.include_router(agent.router, prefix="/agents", tags=["智能体"])
    router.include_router(qa.router, prefix="/qa", tags=["问答助手"])

    return router