"""
工具版本管理系统
提供工具版本跟踪、兼容性检查、升级管理等功能
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
from packaging import version


class VersionCompatibility(Enum):
    """版本兼容性级别"""
    COMPATIBLE = "compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING_CHANGE = "breaking_change"
    DEPRECATED = "deprecated"


@dataclass
class ToolVersion:
    """工具版本信息"""
    tool_name: str
    version: str
    release_date: datetime
    provider: str
    description: str
    breaking_changes: List[str]
    new_features: List[str]
    bug_fixes: List[str]
    deprecated_features: List[str]
    minimum_supported_version: Optional[str] = None
    maximum_supported_version: Optional[str] = None
    dependencies: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VersionMigrationPlan:
    """版本迁移计划"""
    from_version: str
    to_version: str
    compatibility: VersionCompatibility
    migration_steps: List[str]
    rollback_steps: List[str]
    estimated_duration: Optional[int] = None  # minutes
    risks: List[str] = None
    prerequisites: List[str] = None


class ToolVersionManager:
    """工具版本管理器"""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # 版本存储
        self._tool_versions: Dict[str, List[ToolVersion]] = {}
        self._current_versions: Dict[str, str] = {}
        
        # 兼容性矩阵
        self._compatibility_matrix: Dict[str, Dict[str, VersionCompatibility]] = {}
        
        # 迁移计划
        self._migration_plans: Dict[str, List[VersionMigrationPlan]] = {}
        
        # 版本策略配置
        self._version_policies = {
            "auto_update_patch": True,
            "auto_update_minor": False,
            "auto_update_major": False,
            "deprecated_version_grace_period": 90,  # days
            "minimum_supported_versions": 3
        }
    
    async def register_tool_version(self, tool_version: ToolVersion) -> bool:
        """注册工具版本"""
        try:
            tool_name = tool_version.tool_name
            
            # 初始化工具版本列表
            if tool_name not in self._tool_versions:
                self._tool_versions[tool_name] = []
            
            # 检查版本是否已存在
            existing_versions = [v.version for v in self._tool_versions[tool_name]]
            if tool_version.version in existing_versions:
                self._logger.warning(f"Tool version {tool_name}:{tool_version.version} already exists")
                return False
            
            # 添加版本并排序
            self._tool_versions[tool_name].append(tool_version)
            self._tool_versions[tool_name].sort(
                key=lambda v: version.parse(v.version), reverse=True
            )
            
            # 更新当前版本（最新版本）
            self._current_versions[tool_name] = self._tool_versions[tool_name][0].version
            
            # 更新兼容性矩阵
            await self._update_compatibility_matrix(tool_name, tool_version.version)
            
            self._logger.info(f"Registered tool version: {tool_name}:{tool_version.version}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register tool version {tool_version.tool_name}:{tool_version.version}: {e}")
            return False
    
    async def get_tool_version(self, tool_name: str, version_str: str = None) -> Optional[ToolVersion]:
        """获取工具版本信息"""
        if tool_name not in self._tool_versions:
            return None
        
        # 如果未指定版本，返回当前版本
        if version_str is None:
            version_str = self._current_versions.get(tool_name)
            if not version_str:
                return None
        
        # 查找指定版本
        for tool_version in self._tool_versions[tool_name]:
            if tool_version.version == version_str:
                return tool_version
        
        return None
    
    async def get_tool_versions(self, tool_name: str) -> List[ToolVersion]:
        """获取工具所有版本"""
        return self._tool_versions.get(tool_name, [])
    
    async def get_current_version(self, tool_name: str) -> Optional[str]:
        """获取工具当前版本"""
        return self._current_versions.get(tool_name)
    
    async def check_compatibility(self, tool_name: str, from_version: str, to_version: str) -> VersionCompatibility:
        """检查版本兼容性"""
        try:
            # 检查兼容性矩阵
            if tool_name in self._compatibility_matrix:
                version_key = f"{from_version}->{to_version}"
                if version_key in self._compatibility_matrix[tool_name]:
                    return self._compatibility_matrix[tool_name][version_key]
            
            # 基于语义版本进行兼容性推断
            from_ver = version.parse(from_version)
            to_ver = version.parse(to_version)
            
            if from_ver == to_ver:
                return VersionCompatibility.COMPATIBLE
            
            # 主版本号变化 - 可能有破坏性变更
            if from_ver.major != to_ver.major:
                return VersionCompatibility.BREAKING_CHANGE
            
            # 次版本号变化 - 向后兼容
            if from_ver.minor != to_ver.minor:
                return VersionCompatibility.BACKWARD_COMPATIBLE
            
            # 修订版本变化 - 完全兼容
            return VersionCompatibility.COMPATIBLE
            
        except Exception as e:
            self._logger.error(f"Failed to check compatibility for {tool_name} {from_version}->{to_version}: {e}")
            return VersionCompatibility.BREAKING_CHANGE  # 保守估计
    
    async def plan_version_migration(self, tool_name: str, from_version: str, to_version: str) -> Optional[VersionMigrationPlan]:
        """规划版本迁移"""
        try:
            # 检查版本兼容性
            compatibility = await self.check_compatibility(tool_name, from_version, to_version)
            
            # 查找预定义的迁移计划
            if tool_name in self._migration_plans:
                for plan in self._migration_plans[tool_name]:
                    if plan.from_version == from_version and plan.to_version == to_version:
                        return plan
            
            # 生成默认迁移计划
            migration_plan = VersionMigrationPlan(
                from_version=from_version,
                to_version=to_version,
                compatibility=compatibility,
                migration_steps=self._generate_default_migration_steps(compatibility),
                rollback_steps=self._generate_default_rollback_steps(compatibility),
                estimated_duration=self._estimate_migration_duration(compatibility),
                risks=self._assess_migration_risks(compatibility),
                prerequisites=["backup_current_state", "validate_dependencies"]
            )
            
            return migration_plan
            
        except Exception as e:
            self._logger.error(f"Failed to plan migration for {tool_name} {from_version}->{to_version}: {e}")
            return None
    
    async def execute_version_migration(self, tool_name: str, migration_plan: VersionMigrationPlan) -> bool:
        """执行版本迁移"""
        try:
            self._logger.info(f"Starting migration for {tool_name}: {migration_plan.from_version} -> {migration_plan.to_version}")
            
            # 执行迁移步骤
            for i, step in enumerate(migration_plan.migration_steps):
                self._logger.info(f"Executing migration step {i+1}/{len(migration_plan.migration_steps)}: {step}")
                
                # 这里可以根据具体步骤执行相应操作
                if not await self._execute_migration_step(tool_name, step):
                    self._logger.error(f"Migration step failed: {step}")
                    # 执行回滚
                    await self._rollback_migration(tool_name, migration_plan, i)
                    return False
                
                await asyncio.sleep(0.1)  # 短暂暂停
            
            # 更新当前版本
            self._current_versions[tool_name] = migration_plan.to_version
            
            self._logger.info(f"Migration completed successfully for {tool_name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Migration failed for {tool_name}: {e}")
            await self._rollback_migration(tool_name, migration_plan, len(migration_plan.migration_steps))
            return False
    
    async def check_for_updates(self, tool_name: str = None) -> Dict[str, Dict[str, Any]]:
        """检查工具更新"""
        updates = {}
        
        tools_to_check = [tool_name] if tool_name else list(self._current_versions.keys())
        
        for tool in tools_to_check:
            current_version = self._current_versions.get(tool)
            if not current_version:
                continue
            
            available_versions = self._tool_versions.get(tool, [])
            if not available_versions:
                continue
            
            latest_version = available_versions[0].version
            
            # 检查是否有更新
            if current_version != latest_version:
                compatibility = await self.check_compatibility(tool, current_version, latest_version)
                
                # 根据策略决定是否推荐更新
                recommend_update = self._should_recommend_update(
                    current_version, latest_version, compatibility
                )
                
                updates[tool] = {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "compatibility": compatibility.value,
                    "recommend_update": recommend_update,
                    "release_notes": self._get_release_notes(tool, current_version, latest_version)
                }
        
        return updates
    
    async def get_deprecated_tools(self) -> List[Dict[str, Any]]:
        """获取已弃用的工具版本"""
        deprecated_tools = []
        
        for tool_name, versions in self._tool_versions.items():
            current_version = self._current_versions.get(tool_name)
            
            for tool_version in versions:
                # 检查是否在弃用宽限期内
                days_since_release = (datetime.now() - tool_version.release_date).days
                grace_period = self._version_policies["deprecated_version_grace_period"]
                
                if (tool_version.deprecated_features and 
                    tool_version.version != current_version and 
                    days_since_release > grace_period):
                    
                    deprecated_tools.append({
                        "tool_name": tool_name,
                        "version": tool_version.version,
                        "deprecated_features": tool_version.deprecated_features,
                        "days_since_release": days_since_release,
                        "current_version": current_version
                    })
        
        return deprecated_tools
    
    async def _update_compatibility_matrix(self, tool_name: str, new_version: str):
        """更新兼容性矩阵"""
        if tool_name not in self._compatibility_matrix:
            self._compatibility_matrix[tool_name] = {}
        
        # 与所有已存在版本进行兼容性计算
        existing_versions = [v.version for v in self._tool_versions[tool_name]]
        
        for existing_version in existing_versions:
            if existing_version != new_version:
                # 计算双向兼容性
                compat_forward = await self.check_compatibility(tool_name, existing_version, new_version)
                compat_backward = await self.check_compatibility(tool_name, new_version, existing_version)
                
                self._compatibility_matrix[tool_name][f"{existing_version}->{new_version}"] = compat_forward
                self._compatibility_matrix[tool_name][f"{new_version}->{existing_version}"] = compat_backward
    
    def _generate_default_migration_steps(self, compatibility: VersionCompatibility) -> List[str]:
        """生成默认迁移步骤"""
        if compatibility == VersionCompatibility.COMPATIBLE:
            return ["update_tool_version", "validate_functionality"]
        
        elif compatibility == VersionCompatibility.BACKWARD_COMPATIBLE:
            return [
                "backup_current_state",
                "update_tool_version",
                "run_compatibility_tests",
                "validate_functionality"
            ]
        
        elif compatibility == VersionCompatibility.BREAKING_CHANGE:
            return [
                "backup_current_state",
                "analyze_breaking_changes",
                "update_dependent_code",
                "update_tool_version",
                "run_comprehensive_tests",
                "validate_functionality",
                "update_documentation"
            ]
        
        else:  # DEPRECATED
            return [
                "backup_current_state",
                "find_replacement_tool",
                "migrate_to_replacement",
                "remove_deprecated_tool",
                "validate_functionality"
            ]
    
    def _generate_default_rollback_steps(self, compatibility: VersionCompatibility) -> List[str]:
        """生成默认回滚步骤"""
        return [
            "stop_current_version",
            "restore_previous_version",
            "restore_backup_state",
            "validate_rollback",
            "notify_rollback_completion"
        ]
    
    def _estimate_migration_duration(self, compatibility: VersionCompatibility) -> int:
        """估算迁移时长（分钟）"""
        duration_map = {
            VersionCompatibility.COMPATIBLE: 5,
            VersionCompatibility.BACKWARD_COMPATIBLE: 15,
            VersionCompatibility.BREAKING_CHANGE: 60,
            VersionCompatibility.DEPRECATED: 120
        }
        return duration_map.get(compatibility, 30)
    
    def _assess_migration_risks(self, compatibility: VersionCompatibility) -> List[str]:
        """评估迁移风险"""
        risk_map = {
            VersionCompatibility.COMPATIBLE: ["minimal_risk"],
            VersionCompatibility.BACKWARD_COMPATIBLE: ["potential_minor_issues"],
            VersionCompatibility.BREAKING_CHANGE: [
                "api_breaking_changes",
                "functionality_changes",
                "performance_impact"
            ],
            VersionCompatibility.DEPRECATED: [
                "tool_discontinuation",
                "loss_of_functionality",
                "major_workflow_changes"
            ]
        }
        return risk_map.get(compatibility, ["unknown_risks"])
    
    async def _execute_migration_step(self, tool_name: str, step: str) -> bool:
        """执行单个迁移步骤"""
        try:
            # 这里可以根据具体步骤执行相应操作
            # 目前返回成功，实际实现时需要具体的步骤执行逻辑
            self._logger.debug(f"Executing step for {tool_name}: {step}")
            await asyncio.sleep(0.1)  # 模拟执行时间
            return True
        except Exception as e:
            self._logger.error(f"Failed to execute migration step {step}: {e}")
            return False
    
    async def _rollback_migration(self, tool_name: str, migration_plan: VersionMigrationPlan, failed_step: int):
        """回滚迁移"""
        self._logger.warning(f"Rolling back migration for {tool_name} at step {failed_step}")
        
        for step in migration_plan.rollback_steps:
            try:
                await self._execute_migration_step(tool_name, step)
            except Exception as e:
                self._logger.error(f"Rollback step failed: {step}, error: {e}")
    
    def _should_recommend_update(self, current_version: str, latest_version: str, compatibility: VersionCompatibility) -> bool:
        """根据策略决定是否推荐更新"""
        try:
            current_ver = version.parse(current_version)
            latest_ver = version.parse(latest_version)
            
            # 主版本更新 - 不自动推荐
            if current_ver.major != latest_ver.major:
                return self._version_policies["auto_update_major"]
            
            # 次版本更新
            if current_ver.minor != latest_ver.minor:
                return self._version_policies["auto_update_minor"]
            
            # 修订版本更新
            if current_ver.micro != latest_ver.micro:
                return self._version_policies["auto_update_patch"]
            
            return False
            
        except Exception:
            return False
    
    def _get_release_notes(self, tool_name: str, from_version: str, to_version: str) -> Dict[str, List[str]]:
        """获取版本发布说明"""
        release_notes = {
            "new_features": [],
            "bug_fixes": [],
            "breaking_changes": [],
            "deprecated_features": []
        }
        
        # 收集从 from_version 到 to_version 之间的所有变更
        if tool_name in self._tool_versions:
            for tool_version in self._tool_versions[tool_name]:
                ver = version.parse(tool_version.version)
                from_ver = version.parse(from_version)
                to_ver = version.parse(to_version)
                
                if from_ver < ver <= to_ver:
                    release_notes["new_features"].extend(tool_version.new_features)
                    release_notes["bug_fixes"].extend(tool_version.bug_fixes)
                    release_notes["breaking_changes"].extend(tool_version.breaking_changes)
                    release_notes["deprecated_features"].extend(tool_version.deprecated_features)
        
        return release_notes
    
    def export_version_report(self) -> Dict[str, Any]:
        """导出版本报告"""
        return {
            "tools_count": len(self._tool_versions),
            "total_versions": sum(len(versions) for versions in self._tool_versions.values()),
            "current_versions": self._current_versions.copy(),
            "compatibility_matrix_size": sum(len(matrix) for matrix in self._compatibility_matrix.values()),
            "version_policies": self._version_policies.copy(),
            "generated_at": datetime.now().isoformat()
        }


# 全局工具版本管理器实例
tool_version_manager = ToolVersionManager() 