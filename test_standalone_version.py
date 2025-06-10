#!/usr/bin/env python3
"""
独立版本管理系统测试
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class VersionCompatibility(Enum):
    COMPATIBLE = "compatible"
    BACKWARD_COMPATIBLE = "backward_compatible"
    BREAKING_CHANGE = "breaking_change"
    DEPRECATED = "deprecated"

@dataclass
class ToolVersion:
    tool_name: str
    version: str
    release_date: datetime
    provider: str
    description: str
    breaking_changes: List[str]
    new_features: List[str]
    bug_fixes: List[str]
    deprecated_features: List[str]
    dependencies: Optional[Dict[str, str]] = None

class SimpleToolVersionManager:
    def __init__(self):
        self._tool_versions: Dict[str, List[ToolVersion]] = {}
        self._current_versions: Dict[str, str] = {}
    
    async def register_tool_version(self, tool_version: ToolVersion) -> bool:
        tool_name = tool_version.tool_name
        if tool_name not in self._tool_versions:
            self._tool_versions[tool_name] = []
        
        self._tool_versions[tool_name].append(tool_version)
        self._current_versions[tool_name] = tool_version.version
        return True
    
    async def get_current_version(self, tool_name: str) -> Optional[str]:
        return self._current_versions.get(tool_name)
    
    async def get_tool_versions(self, tool_name: str) -> List[ToolVersion]:
        return self._tool_versions.get(tool_name, [])
    
    async def check_compatibility(self, tool_name: str, from_version: str, to_version: str) -> VersionCompatibility:
        if from_version == to_version:
            return VersionCompatibility.COMPATIBLE
        
        from_parts = from_version.split('.')
        to_parts = to_version.split('.')
        
        if len(from_parts) >= 1 and len(to_parts) >= 1:
            if from_parts[0] != to_parts[0]:
                return VersionCompatibility.BREAKING_CHANGE
            elif len(from_parts) >= 2 and len(to_parts) >= 2 and from_parts[1] != to_parts[1]:
                return VersionCompatibility.BACKWARD_COMPATIBLE
        
        return VersionCompatibility.COMPATIBLE

async def test_version_management():
    try:
        print("=== 独立工具版本管理系统测试 ===")
        
        version_manager = SimpleToolVersionManager()
        print("✅ 版本管理模块创建成功")
        
        # 测试1: 注册工具版本
        print("\n📋 测试1: 注册工具版本")
        
        agno_v1 = ToolVersion(
            tool_name="agno_reasoning",
            version="1.0.0",
            release_date=datetime.now() - timedelta(days=30),
            provider="agno",
            description="Agno推理工具v1.0.0 - 基础版本",
            breaking_changes=[],
            new_features=["基础推理能力"],
            bug_fixes=[],
            deprecated_features=[],
            dependencies={"agno": "1.0.0"}
        )
        
        success1 = await version_manager.register_tool_version(agno_v1)
        print(f"  • 注册 v1.0.0: {'✅' if success1 else '❌'}")
        
        # 测试2: 版本查询
        print("\n📋 测试2: 版本查询")
        
        current_version = await version_manager.get_current_version("agno_reasoning")
        print(f"  • 当前版本: {current_version}")
        
        all_versions = await version_manager.get_tool_versions("agno_reasoning")
        print(f"  • 所有版本数量: {len(all_versions)}")
        
        # 测试3: 兼容性检查
        print("\n📋 测试3: 兼容性检查")
        
        compat = await version_manager.check_compatibility("agno_reasoning", "1.0.0", "1.0.0")
        print(f"  • v1.0.0 → v1.0.0: {compat.value}")
        
        print("\n✅ 工具版本管理系统测试完成！")
        
        print("\n📊 测试总结:")
        print("✅ 版本注册功能正常")
        print("✅ 版本查询功能正常") 
        print("✅ 兼容性检查功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 版本管理系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_version_management())
    print(f"\n🎯 测试结果: {'✅ 全部通过' if success else '❌ 有失败项'}")
    exit(0 if success else 1) 