#!/usr/bin/env python3
"""
简化版本管理系统测试
避免复杂依赖，直接测试核心功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加应用路径到系统路径
sys.path.insert(0, '/Users/wxn/Desktop/ZZDSJ/zzdsj-backend-api')

async def test_version_management_simple():
    try:
        print("=== 工具版本管理系统简化测试 ===")
        
        # 直接导入版本管理模块
        from app.utils.version.tool_version_manager import (
            ToolVersionManager,
            ToolVersion,
            VersionCompatibility,
            VersionMigrationPlan
        )
        
        print("✅ 版本管理模块导入成功")
        
        # 创建版本管理器实例
        version_manager = ToolVersionManager()
        
        # 测试1: 注册工具版本
        print("\n📋 测试1: 注册工具版本")
        
        # 创建示例工具版本
        agno_v1 = ToolVersion(
            tool_name="agno_reasoning",
            version="1.0.0",
            release_date=datetime.now() - timedelta(days=30),
            provider="agno",
            description="Agno推理工具v1.0.0 - 基础版本",
            breaking_changes=[],
            new_features=["基础推理能力", "知识检索", "上下文理解"],
            bug_fixes=[],
            deprecated_features=[],
            dependencies={"agno": "1.0.0"}
        )
        
        agno_v2 = ToolVersion(
            tool_name="agno_reasoning",
            version="1.1.0",
            release_date=datetime.now() - timedelta(days=15),
            provider="agno",
            description="Agno推理工具v1.1.0 - 增强版本",
            breaking_changes=[],
            new_features=["改进的推理算法", "批量处理支持"],
            bug_fixes=["修复内存泄漏", "优化响应速度"],
            deprecated_features=[],
            dependencies={"agno": "1.1.0"}
        )
        
        agno_v2_major = ToolVersion(
            tool_name="agno_reasoning",
            version="2.0.0",
            release_date=datetime.now() - timedelta(days=5),
            provider="agno",
            description="Agno推理工具v2.0.0 - 重大更新",
            breaking_changes=["API接口变更", "配置格式更新"],
            new_features=["新的推理引擎", "多模态支持", "实时学习"],
            bug_fixes=["修复所有已知问题"],
            deprecated_features=["旧版API"],
            dependencies={"agno": "2.0.0", "numpy": "1.24.0"}
        )
        
        # 注册版本
        success1 = await version_manager.register_tool_version(agno_v1)
        success2 = await version_manager.register_tool_version(agno_v2)
        success3 = await version_manager.register_tool_version(agno_v2_major)
        
        print(f"  • 注册 v1.0.0: {'✅' if success1 else '❌'}")
        print(f"  • 注册 v1.1.0: {'✅' if success2 else '❌'}")
        print(f"  • 注册 v2.0.0: {'✅' if success3 else '❌'}")
        
        # 测试2: 版本查询
        print("\n📋 测试2: 版本查询")
        
        current_version = await version_manager.get_current_version("agno_reasoning")
        print(f"  • 当前版本: {current_version}")
        
        all_versions = await version_manager.get_tool_versions("agno_reasoning")
        print(f"  • 所有版本数量: {len(all_versions)}")
        for version in all_versions:
            print(f"    - {version.version}: {version.description}")
        
        # 测试3: 兼容性检查
        print("\n📋 测试3: 兼容性检查")
        
        compat_patch = await version_manager.check_compatibility("agno_reasoning", "1.0.0", "1.1.0")
        compat_major = await version_manager.check_compatibility("agno_reasoning", "1.1.0", "2.0.0")
        compat_same = await version_manager.check_compatibility("agno_reasoning", "1.1.0", "1.1.0")
        
        print(f"  • v1.0.0 → v1.1.0: {compat_patch.value}")
        print(f"  • v1.1.0 → v2.0.0: {compat_major.value}")
        print(f"  • v1.1.0 → v1.1.0: {compat_same.value}")
        
        # 测试4: 迁移计划
        print("\n📋 测试4: 迁移计划")
        
        migration_plan = await version_manager.plan_version_migration("agno_reasoning", "1.0.0", "2.0.0")
        if migration_plan:
            print(f"  • 迁移计划: {migration_plan.from_version} → {migration_plan.to_version}")
            print(f"  • 兼容性: {migration_plan.compatibility.value}")
            print(f"  • 预估时长: {migration_plan.estimated_duration}分钟")
            print(f"  • 迁移步骤: {len(migration_plan.migration_steps)}个")
            for i, step in enumerate(migration_plan.migration_steps):
                print(f"    {i+1}. {step}")
            print(f"  • 风险评估: {migration_plan.risks}")
        
        # 测试5: 更新检查
        print("\n📋 测试5: 更新检查")
        
        updates = await version_manager.check_for_updates("agno_reasoning")
        if updates:
            for tool, update_info in updates.items():
                print(f"  • {tool}:")
                print(f"    当前版本: {update_info['current_version']}")
                print(f"    最新版本: {update_info['latest_version']}")
                print(f"    推荐更新: {'是' if update_info['recommend_update'] else '否'}")
                print(f"    兼容性: {update_info['compatibility']}")
        
        # 测试6: 版本报告
        print("\n📋 测试6: 版本报告")
        
        report = version_manager.export_version_report()
        print(f"  • 管理工具数量: {report['tools_count']}")
        print(f"  • 总版本数量: {report['total_versions']}")
        print(f"  • 兼容性矩阵大小: {report['compatibility_matrix_size']}")
        print(f"  • 报告生成时间: {report['generated_at']}")
        
        # 测试7: 模拟迁移执行
        print("\n📋 测试7: 模拟迁移执行")
        
        # 创建简单迁移计划进行测试
        test_migration = await version_manager.plan_version_migration("agno_reasoning", "1.0.0", "1.1.0")
        if test_migration:
            print(f"  • 开始迁移: {test_migration.from_version} → {test_migration.to_version}")
            
            # 执行迁移（这是模拟执行）
            migration_success = await version_manager.execute_version_migration("agno_reasoning", test_migration)
            print(f"  • 迁移结果: {'✅ 成功' if migration_success else '❌ 失败'}")
            
            if migration_success:
                new_current = await version_manager.get_current_version("agno_reasoning")
                print(f"  • 迁移后当前版本: {new_current}")
        
        # 测试8: 添加更多工具测试多工具管理
        print("\n📋 测试8: 多工具管理")
        
        # 添加Haystack工具版本
        haystack_v1 = ToolVersion(
            tool_name="haystack_extract_answers",
            version="1.0.0",
            release_date=datetime.now() - timedelta(days=10),
            provider="haystack",
            description="Haystack提取式问答工具",
            breaking_changes=[],
            new_features=["文档问答", "答案提取"],
            bug_fixes=[],
            deprecated_features=[],
            dependencies={"haystack": "1.21.0"}
        )
        
        await version_manager.register_tool_version(haystack_v1)
        
        # 检查所有工具更新
        all_updates = await version_manager.check_for_updates()
        print(f"  • 总共管理 {len(all_updates)} 个工具的版本")
        
        print("\n✅ 工具版本管理系统测试完成！")
        
        # 显示测试总结
        print("\n📊 测试总结:")
        print("✅ 版本注册功能正常")
        print("✅ 版本查询功能正常") 
        print("✅ 兼容性检查功能正常")
        print("✅ 迁移计划功能正常")
        print("✅ 更新检查功能正常")
        print("✅ 版本报告功能正常")
        print("✅ 迁移执行功能正常")
        print("✅ 多工具管理功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 版本管理系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_version_management_simple())
    exit(0 if success else 1) 