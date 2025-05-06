"""
系统设置管理API

提供系统设置的查询和更新接口，支持前端系统设置页面。
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.schemas.settings import SystemSettings, MetricsSettings
from app.services.settings_service import get_system_settings_service

router = APIRouter()


@router.get("/system", response_model=SystemSettings)
async def get_system_settings():
    """
    获取系统设置
    """
    service = get_system_settings_service()
    return await service.get_settings()


@router.patch("/system", response_model=SystemSettings)
async def update_system_settings(settings_update: SystemSettings):
    """
    更新系统设置
    
    可以部分更新，仅提供需要修改的字段
    """
    service = get_system_settings_service()
    return await service.update_settings(settings_update)


@router.get("/metrics", response_model=MetricsSettings)
async def get_metrics_settings():
    """
    获取指标统计设置
    """
    service = get_system_settings_service()
    system_settings = await service.get_settings()
    # 如果指标设置不存在，则返回默认值
    if not system_settings.metrics:
        system_settings.metrics = MetricsSettings()
    return system_settings.metrics


@router.patch("/metrics", response_model=MetricsSettings)
async def update_metrics_settings(settings_update: MetricsSettings):
    """
    更新指标统计设置
    """
    service = get_system_settings_service()
    system_settings = await service.get_settings()
    
    # 创建系统设置更新
    update_data = SystemSettings(metrics=settings_update)
    
    # 更新设置
    updated = await service.update_settings(update_data)
    
    # 返回更新后的指标设置
    if not updated.metrics:
        updated.metrics = MetricsSettings()
    return updated.metrics
