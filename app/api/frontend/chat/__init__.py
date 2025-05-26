"""
对话模块：提供对话管理、记忆和上下文压缩功能
"""

from fastapi import APIRouter

from app.api.frontend.chat import conversations, memory, compression

# 创建对话模块路由
router = APIRouter()

# 注册子路由
router.include_router(conversations.router, prefix="/conversations", tags=["对话管理"])
router.include_router(memory.router, prefix="/memory", tags=["对话记忆"])
router.include_router(compression.router, prefix="/compression", tags=["上下文压缩"]) 