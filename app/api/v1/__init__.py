"""
API V1版本
定义API的统一入口和路由组织
"""

from fastapi import APIRouter

from app.api.v1.routes import (
    assistants,
    chat, 
    knowledge,
    model_provider,
    voice,
    mcp,
    assistant_qa,
    settings,
    lightrag
)

# 创建主路由
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(assistants.router, prefix="/assistants", tags=["助手管理"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(model_provider.router, prefix="/models", tags=["模型管理"])
api_router.include_router(voice.router, prefix="/voice", tags=["语音服务"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP工具链"])
api_router.include_router(assistant_qa.router, prefix="/assistant-qa", tags=["问答助手"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
api_router.include_router(lightrag.router, prefix="/lightrag", tags=["知识图谱"])
