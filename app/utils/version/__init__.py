"""
版本管理工具模块
提供工具版本跟踪、兼容性检查、升级管理等功能
"""

from .tool_version_manager import (
    ToolVersionManager,
    ToolVersion,
    VersionCompatibility,
    VersionMigrationPlan,
    tool_version_manager
)

__all__ = [
    "ToolVersionManager",
    "ToolVersion", 
    "VersionCompatibility",
    "VersionMigrationPlan",
    "tool_version_manager"
]

__version__ = "1.0.0" 