"""
系统设置管理API
[迁移桥接] - 该文件已迁移至 app/api/frontend/system/settings.py
"""

from fastapi import APIRouter
import logging

# 导入新的API模块
from app.api.frontend.system.settings import router as new_router

# 创建路由
router = APIRouter()
logger = logging.getLogger(__name__)

# 记录迁移警告
logger.warning("使用已弃用的app/api/settings.py，该文件已迁移至app/api/frontend/system/settings.py")

# 将所有请求转发到新的路由处理器
for route in new_router.routes:
    router.routes.append(route)


@router.get("/system", response_model=SystemSettings)
async def get_system_settings():
    """
    获取系统设置
    """
    logger.warning(
        "使用已弃用的系统设置端点: /api/v1/settings/system，应使用新的端点: /api/frontend/system/settings/system"
    )
    return await new_get_system_settings()


@router.patch("/system", response_model=SystemSettings)
async def update_system_settings(settings_update: SystemSettings):
    """
    更新系统设置
    
    可以部分更新，仅提供需要修改的字段
    """
    logger.warning(
        "使用已弃用的系统设置端点: /api/v1/settings/system，应使用新的端点: /api/frontend/system/settings/system"
    )
    return await new_update_system_settings(settings_update=settings_update)


@router.get("/metrics", response_model=MetricsSettings)
async def get_metrics_settings():
    """
    获取指标统计设置
    """
    logger.warning(
        "使用已弃用的系统设置端点: /api/v1/settings/metrics，应使用新的端点: /api/frontend/system/settings/metrics"
    )
    return await new_get_metrics_settings()


@router.patch("/metrics", response_model=MetricsSettings)
async def update_metrics_settings(settings_update: MetricsSettings):
    """
    更新指标统计设置
    """
    logger.warning(
        "使用已弃用的系统设置端点: /api/v1/settings/metrics，应使用新的端点: /api/frontend/system/settings/metrics"
    )
    return await new_update_metrics_settings(settings_update=settings_update)
