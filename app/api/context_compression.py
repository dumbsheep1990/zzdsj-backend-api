"""
上下文压缩API模块
[迁移桥接] - 该文件已迁移至 app/api/frontend/chat/compression.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.chat.compression import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/context_compression.py，该文件已迁移至app/api/frontend/chat/compression.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
