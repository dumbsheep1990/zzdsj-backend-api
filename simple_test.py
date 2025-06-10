#!/usr/bin/env python3
"""简单的系统状态检查"""

import asyncio
import sys
import os

# 添加应用路径到系统路径
sys.path.insert(0, '/Users/wxn/Desktop/ZZDSJ/zzdsj-backend-api')

async def test_system():
    try:
        print("=== 统一工具系统状态检查 ===")
        
        # 导入必要模块
        from app.registry.unified_registry import UnifiedToolRegistry
        
        # 创建注册中心
        registry = UnifiedToolRegistry()
        
        # 初始化
        print("🔧 初始化统一工具注册中心...")
        await registry.initialize()
        
        # 获取统计信息
        stats = registry.get_registry_stats()
        print(f"总框架数: {stats['frameworks_count']}")
        print(f"总工具数: {stats['total_tools']}")
        
        # 发现所有工具
        all_tools = await registry.discover_tools()
        
        # 按框架分组
        tools_by_provider = {}
        for tool in all_tools:
            provider = tool.provider
            if provider not in tools_by_provider:
                tools_by_provider[provider] = []
            tools_by_provider[provider].append(tool)
        
        for provider, tools in tools_by_provider.items():
            print(f"\n🔧 {provider} ({len(tools)}个工具):")
            for tool in tools:
                print(f"  • {tool.name}: {tool.description}")
        
        # 关闭
        await registry.shutdown()
        print("\n✅ 检查完成！")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_system()) 