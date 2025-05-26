"""
问答助手API: 提供问答助手管理、问题卡片管理和文档关联操作
[迁移桥接] - 该文件已迁移至 app/api/frontend/assistants/qa.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.assistants.qa import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/assistant_qa.py，该文件已迁移至app/api/frontend/assistants/qa.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
