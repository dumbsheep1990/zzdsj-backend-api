"""
工具版本管理API路由
提供工具版本查询、更新检查、迁移等接口
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.utils.version import (
    tool_version_manager,
    ToolVersion,
    VersionCompatibility,
    VersionMigrationPlan
)
from app.schemas.tool_schemas import BaseResponse

# 设置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/tools/version", tags=["Tool Version Management"])


# 响应模型
class ToolVersionResponse(BaseResponse):
    """工具版本响应模型"""
    data: Optional[Dict[str, Any]] = None


class VersionListResponse(BaseResponse):
    """版本列表响应模型"""
    data: List[Dict[str, Any]] = []


class UpdateCheckResponse(BaseResponse):
    """更新检查响应模型"""
    data: Dict[str, Dict[str, Any]] = {}


@router.get("/list", response_model=VersionListResponse)
async def list_tool_versions(
    tool_name: Optional[str] = Query(None, description="工具名称，不指定则返回所有工具版本")
):
    """
    获取工具版本列表
    """
    try:
        if tool_name:
            # 获取指定工具的所有版本
            versions = await tool_version_manager.get_tool_versions(tool_name)
            version_data = []
            
            for version in versions:
                version_data.append({
                    "tool_name": version.tool_name,
                    "version": version.version,
                    "release_date": version.release_date.isoformat(),
                    "provider": version.provider,
                    "description": version.description,
                    "breaking_changes": version.breaking_changes,
                    "new_features": version.new_features,
                    "bug_fixes": version.bug_fixes,
                    "deprecated_features": version.deprecated_features,
                    "dependencies": version.dependencies or {},
                    "metadata": version.metadata or {}
                })
            
            return VersionListResponse(
                success=True,
                message=f"Retrieved {len(version_data)} versions for {tool_name}",
                data=version_data
            )
        else:
            # 获取所有工具的当前版本
            all_versions = {}
            for tool in tool_version_manager._current_versions.keys():
                current_version = await tool_version_manager.get_current_version(tool)
                version_info = await tool_version_manager.get_tool_version(tool, current_version)
                
                if version_info:
                    all_versions[tool] = {
                        "current_version": current_version,
                        "release_date": version_info.release_date.isoformat(),
                        "provider": version_info.provider,
                        "description": version_info.description
                    }
            
            return VersionListResponse(
                success=True,
                message=f"Retrieved versions for {len(all_versions)} tools",
                data=[{"tool_name": k, **v} for k, v in all_versions.items()]
            )
            
    except Exception as e:
        logger.error(f"Failed to list tool versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current/{tool_name}", response_model=ToolVersionResponse)
async def get_current_version(tool_name: str):
    """
    获取工具当前版本信息
    """
    try:
        current_version = await tool_version_manager.get_current_version(tool_name)
        if not current_version:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        version_info = await tool_version_manager.get_tool_version(tool_name, current_version)
        if not version_info:
            raise HTTPException(status_code=404, detail=f"Version info not found for {tool_name}")
        
        return ToolVersionResponse(
            success=True,
            message=f"Current version for {tool_name}",
            data={
                "tool_name": version_info.tool_name,
                "version": version_info.version,
                "release_date": version_info.release_date.isoformat(),
                "provider": version_info.provider,
                "description": version_info.description,
                "breaking_changes": version_info.breaking_changes,
                "new_features": version_info.new_features,
                "bug_fixes": version_info.bug_fixes,
                "deprecated_features": version_info.deprecated_features,
                "dependencies": version_info.dependencies or {},
                "metadata": version_info.metadata or {}
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current version for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-updates", response_model=UpdateCheckResponse)
async def check_for_updates(
    tool_name: Optional[str] = Query(None, description="工具名称，不指定则检查所有工具")
):
    """
    检查工具更新
    """
    try:
        updates = await tool_version_manager.check_for_updates(tool_name)
        
        return UpdateCheckResponse(
            success=True,
            message=f"Checked updates for {len(updates)} tools",
            data=updates
        )
        
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compatibility/{tool_name}")
async def check_version_compatibility(
    tool_name: str,
    from_version: str = Query(..., description="源版本"),
    to_version: str = Query(..., description="目标版本")
):
    """
    检查版本兼容性
    """
    try:
        compatibility = await tool_version_manager.check_compatibility(
            tool_name, from_version, to_version
        )
        
        return ToolVersionResponse(
            success=True,
            message=f"Compatibility check for {tool_name}: {from_version} -> {to_version}",
            data={
                "tool_name": tool_name,
                "from_version": from_version,
                "to_version": to_version,
                "compatibility": compatibility.value,
                "description": _get_compatibility_description(compatibility)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to check compatibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migration/plan/{tool_name}")
async def plan_version_migration(
    tool_name: str,
    from_version: str = Query(..., description="源版本"),
    to_version: str = Query(..., description="目标版本")
):
    """
    规划版本迁移
    """
    try:
        migration_plan = await tool_version_manager.plan_version_migration(
            tool_name, from_version, to_version
        )
        
        if not migration_plan:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot create migration plan for {tool_name}: {from_version} -> {to_version}"
            )
        
        return ToolVersionResponse(
            success=True,
            message=f"Migration plan created for {tool_name}",
            data={
                "tool_name": tool_name,
                "from_version": migration_plan.from_version,
                "to_version": migration_plan.to_version,
                "compatibility": migration_plan.compatibility.value,
                "migration_steps": migration_plan.migration_steps,
                "rollback_steps": migration_plan.rollback_steps,
                "estimated_duration": migration_plan.estimated_duration,
                "risks": migration_plan.risks or [],
                "prerequisites": migration_plan.prerequisites or []
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to plan migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migration/execute/{tool_name}")
async def execute_version_migration(
    tool_name: str,
    from_version: str = Query(..., description="源版本"),
    to_version: str = Query(..., description="目标版本")
):
    """
    执行版本迁移
    """
    try:
        # 首先规划迁移
        migration_plan = await tool_version_manager.plan_version_migration(
            tool_name, from_version, to_version
        )
        
        if not migration_plan:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create migration plan for {tool_name}: {from_version} -> {to_version}"
            )
        
        # 执行迁移
        success = await tool_version_manager.execute_version_migration(
            tool_name, migration_plan
        )
        
        if success:
            return ToolVersionResponse(
                success=True,
                message=f"Migration completed successfully for {tool_name}",
                data={
                    "tool_name": tool_name,
                    "from_version": from_version,
                    "to_version": to_version,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Migration failed for {tool_name}: {from_version} -> {to_version}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deprecated", response_model=VersionListResponse)
async def get_deprecated_tools():
    """
    获取已弃用的工具版本
    """
    try:
        deprecated_tools = await tool_version_manager.get_deprecated_tools()
        
        return VersionListResponse(
            success=True,
            message=f"Found {len(deprecated_tools)} deprecated tool versions",
            data=deprecated_tools
        )
        
    except Exception as e:
        logger.error(f"Failed to get deprecated tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_version_report():
    """
    获取版本管理报告
    """
    try:
        report = tool_version_manager.export_version_report()
        
        return ToolVersionResponse(
            success=True,
            message="Version management report",
            data=report
        )
        
    except Exception as e:
        logger.error(f"Failed to generate version report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_compatibility_description(compatibility: VersionCompatibility) -> str:
    """获取兼容性描述"""
    descriptions = {
        VersionCompatibility.COMPATIBLE: "完全兼容，可以直接升级",
        VersionCompatibility.BACKWARD_COMPATIBLE: "向后兼容，升级后可能有新特性",
        VersionCompatibility.BREAKING_CHANGE: "有破坏性变更，需要谨慎迁移",
        VersionCompatibility.DEPRECATED: "版本已弃用，建议迁移到新版本"
    }
    return descriptions.get(compatibility, "兼容性未知")


# 注册路由
def register_version_routes(app):
    """注册版本管理路由"""
    app.include_router(router) 