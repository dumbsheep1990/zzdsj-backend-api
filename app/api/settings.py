"""
系统设置管理API

提供系统设置的查询和更新接口，支持前端系统设置页面。
(桥接文件 - 仅用于向后兼容，所有新代码都应该使用app.api.frontend.system.settings模块)
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.schemas.settings import SystemSettings, MetricsSettings
from app.services.settings_service import get_system_settings_service

# 导入新的系统设置路由处理函数
from app.api.frontend.system.settings import (
    get_system_settings as new_get_system_settings,
    update_system_settings as new_update_system_settings,
    get_metrics_settings as new_get_metrics_settings,
    update_metrics_settings as new_update_metrics_settings
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter()


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
