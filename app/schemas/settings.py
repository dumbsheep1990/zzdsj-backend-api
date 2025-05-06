"""
系统设置相关的Pydantic模型
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field


class MetricsSettings(BaseModel):
    """指标统计设置"""
    enabled: bool = Field(default=True, description="是否启用指标统计")
    token_statistics: bool = Field(default=True, description="是否启用token统计")
    
    class Config:
        schema_extra = {
            "example": {
                "enabled": True,
                "token_statistics": True
            }
        }


class SystemSettings(BaseModel):
    """系统设置"""
    metrics: Optional[MetricsSettings] = None
    
    class Config:
        schema_extra = {
            "example": {
                "metrics": {
                    "enabled": True,
                    "token_statistics": True
                }
            }
        }
