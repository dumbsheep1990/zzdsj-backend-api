"""
助手管理API模块: 提供助手资源的CRUD操作
[迁移桥接] - 该文件已迁移至 app/api/frontend/assistants/manage.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.assistants.manage import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/assistants.py，该文件已迁移至app/api/frontend/assistants/manage.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
