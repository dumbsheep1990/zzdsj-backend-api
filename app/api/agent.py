"""
智能体服务API: 提供智能体任务处理和工具调用的接口
[迁移桥接] - 该文件已迁移至 app/api/frontend/assistants/agent.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.assistants.agent import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/agent.py，该文件已迁移至app/api/frontend/assistants/agent.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)
