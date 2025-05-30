"""
OWL框架工具API端点: 提供OWL框架工具的HTTP API接口
[迁移桥接] - 该文件已迁移至 app/api/frontend/frameworks/owl/api.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.frameworks.owl.api import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/owl_api.py，该文件已迁移至app/api/frontend/frameworks/owl/api.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
