"""
V1 API路由配置
统一管理第三方对外API的所有路由
"""

from fastapi import APIRouter, Depends
from app.api.v1.dependencies import V1Auth, V1AuthWithRateLimit, V1Context

# 创建V1主路由
router = APIRouter(
    prefix="/api/v1", 
    tags=["V1 API - 第三方对外接口"],
    dependencies=[Depends(V1AuthWithRateLimit)]  # 所有V1接口都需要认证和限流
)

# 导入子路由
from app.api.v1.core import assistants as core_assistants
from app.api.v1.core import chat as core_chat
from app.api.v1.core import knowledge as core_knowledge
from app.api.v1.core import search as core_search

from app.api.v1.ai import completion as ai_completion
from app.api.v1.ai import embedding as ai_embedding
from app.api.v1.ai import models as ai_models
from app.api.v1.ai import analysis as ai_analysis

from app.api.v1.tools import invoke as tools_invoke
from app.api.v1.tools import list as tools_list
from app.api.v1.tools import schemas as tools_schemas

from app.api.v1.webhooks import events as webhook_events
from app.api.v1.webhooks import callbacks as webhook_callbacks

# 注册核心业务路由
router.include_router(
    core_assistants.router,
    prefix="/assistants",
    tags=["核心功能 - 智能助手"]
)

router.include_router(
    core_chat.router,
    prefix="/chat",
    tags=["核心功能 - 对话聊天"]
)

router.include_router(
    core_knowledge.router,
    prefix="/knowledge",
    tags=["核心功能 - 知识查询"]
)

router.include_router(
    core_search.router,
    prefix="/search",
    tags=["核心功能 - 智能搜索"]
)

# 注册AI能力路由
router.include_router(
    ai_completion.router,
    prefix="/ai/completion",
    tags=["AI能力 - 文本生成"]
)

router.include_router(
    ai_embedding.router,
    prefix="/ai/embedding",
    tags=["AI能力 - 向量化"]
)

router.include_router(
    ai_models.router,
    prefix="/ai/models",
    tags=["AI能力 - 模型信息"]
)

router.include_router(
    ai_analysis.router,
    prefix="/ai/analysis",
    tags=["AI能力 - 文本分析"]
)

# 注册工具调用路由
router.include_router(
    tools_invoke.router,
    prefix="/tools/invoke",
    tags=["工具调用 - 执行工具"]
)

router.include_router(
    tools_list.router,
    prefix="/tools",
    tags=["工具调用 - 工具列表"]
)

router.include_router(
    tools_schemas.router,
    prefix="/tools/schemas",
    tags=["工具调用 - 工具定义"]
)

# 注册回调接口路由
router.include_router(
    webhook_events.router,
    prefix="/webhooks/events",
    tags=["回调接口 - 事件通知"]
)

router.include_router(
    webhook_callbacks.router,
    prefix="/webhooks/callbacks",
    tags=["回调接口 - 回调处理"]
)

# API状态检查接口
@router.get("/status", tags=["系统状态"])
async def get_api_status():
    """获取V1 API状态"""
    return {
        "status": "success",
        "data": {
            "api_version": "v1",
            "service_status": "healthy",
            "available_endpoints": [
                "/assistants",
                "/chat", 
                "/knowledge",
                "/search",
                "/ai/completion",
                "/ai/embedding",
                "/ai/models",
                "/ai/analysis",
                "/tools",
                "/webhooks"
            ]
        },
        "message": "V1 API服务正常运行",
        "timestamp": "2024-01-01T00:00:00Z"
    } 