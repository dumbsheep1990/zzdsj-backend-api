#!/usr/bin/env python3
"""
政策检索工具演示脚本
展示政策检索工具的各种使用方法和功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.tools.advanced.search.policy_search_tool import get_policy_search_tool, policy_search
from app.services.system.portal_config_service import get_portal_config_service
from app.frameworks.llamaindex.adapters.policy_search_adapter import (
    get_policy_search_adapter, 
    create_policy_search_tools
)


async def demo_basic_policy_search():
    """演示基础政策检索功能"""
    print("🔍 政策检索工具基础功能演示")
    print("=" * 50)
    
    # 创建政策检索工具实例
    tool = get_policy_search_tool()
    
    # 测试不同的搜索查询
    test_queries = [
        ("养老政策", "六盘水"),
        ("教育补贴", "贵州"),
        ("企业扶持", "六盘水"),
        ("医疗保障", "贵州")
    ]
    
    for query, region in test_queries:
        print(f"\n📋 查询: {query} | 地区: {region}")
        print("-" * 30)
        
        try:
            result = await tool._arun(
                query=query,
                region=region,
                search_strategy="auto",
                max_results=5
            )
            print(result)
        except Exception as e:
            print(f"❌ 检索失败: {str(e)}")
        
        print("\n" + "="*50)


async def demo_search_strategies():
    """演示不同的检索策略"""
    print("🎯 政策检索策略演示")
    print("=" * 50)
    
    tool = get_policy_search_tool()
    query = "惠民政策"
    region = "六盘水"
    
    strategies = [
        ("auto", "自动策略"),
        ("local_only", "仅地方门户"),
        ("provincial_only", "仅省级门户"),
        ("search_only", "仅搜索引擎")
    ]
    
    for strategy, description in strategies:
        print(f"\n🔸 策略: {description} ({strategy})")
        print("-" * 30)
        
        try:
            result = await tool._arun(
                query=query,
                region=region,
                search_strategy=strategy,
                max_results=3
            )
            print(result)
        except Exception as e:
            print(f"❌ 检索失败: {str(e)}")
        
        print("\n" + "="*30)


async def demo_portal_management():
    """演示门户配置管理功能"""
    print("⚙️ 门户配置管理演示")
    print("=" * 50)
    
    portal_service = get_portal_config_service()
    
    # 1. 列出所有门户配置
    print("\n📝 1. 当前可用的门户配置：")
    print("-" * 30)
    
    try:
        configs = await portal_service.list_portal_configs()
        for config in configs:
            region_name = config.get("region_name", "未知")
            name = config.get("name", "未知")
            level = config.get("level", "未知")
            is_custom = config.get("is_custom", False)
            config_type = "自定义" if is_custom else "内置"
            
            print(f"• {region_name}: {name} ({level}) - {config_type}")
    except Exception as e:
        print(f"❌ 获取配置失败: {str(e)}")
    
    # 2. 测试门户连接
    print("\n🔗 2. 测试门户连接性：")
    print("-" * 30)
    
    test_regions = ["六盘水", "贵州"]
    for region in test_regions:
        try:
            result = await portal_service.test_portal_connection(region)
            if result["success"]:
                print(f"✅ {region}: 连接正常")
            else:
                print(f"❌ {region}: {result.get('error', '连接失败')}")
        except Exception as e:
            print(f"❌ {region}: 测试失败 - {str(e)}")
    
    # 3. 创建自定义门户配置示例
    print("\n➕ 3. 创建自定义门户配置示例：")
    print("-" * 30)
    
    custom_config = {
        "name": "测试市政府门户",
        "level": "municipal",
        "parent_region": "贵州省",
        "base_url": "https://example.gov.cn",
        "search_endpoint": "/search",
        "search_params": {
            "q": "{query}",
            "type": "policy"
        },
        "encoding": "utf-8",
        "max_results": 10,
        "region_code": "520999"
    }
    
    try:
        success = await portal_service.set_portal_config("测试市", custom_config)
        if success:
            print("✅ 自定义门户配置创建成功")
            
            # 验证配置
            config = await portal_service.get_portal_config("测试市")
            if config:
                print(f"✅ 配置验证通过: {config['name']}")
            
            # 清理测试配置
            await portal_service.delete_portal_config("测试市")
            print("🗑️ 测试配置已清理")
        else:
            print("❌ 自定义门户配置创建失败")
    except Exception as e:
        print(f"❌ 配置管理失败: {str(e)}")


async def demo_llamaindex_integration():
    """演示LlamaIndex集成功能"""
    print("🤖 LlamaIndex工具集成演示")
    print("=" * 50)
    
    # 获取政策检索适配器
    adapter = get_policy_search_adapter()
    
    # 创建所有政策检索相关工具
    tools = create_policy_search_tools()
    
    print(f"\n📦 可用工具数量: {len(tools)}")
    print("-" * 30)
    
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.metadata.name}: {tool.metadata.description[:100]}...")
    
    # 演示工具调用
    print("\n🔧 工具调用演示:")
    print("-" * 30)
    
    # 查询可用地区
    print("1. 查询可用地区:")
    try:
        regions_tool = tools[1]  # query_policy_regions工具
        regions_result = regions_tool._run()
        print(regions_result[:500] + "..." if len(regions_result) > 500 else regions_result)
    except Exception as e:
        print(f"❌ 查询地区失败: {str(e)}")
    
    print("\n" + "-" * 30)
    
    # 测试门户连接
    print("2. 测试门户连接:")
    try:
        test_tool = tools[2]  # test_policy_portal工具
        test_result = test_tool._run(region="六盘水")
        print(test_result)
    except Exception as e:
        print(f"❌ 门户测试失败: {str(e)}")
    
    print("\n" + "-" * 30)
    
    # 增强政策检索
    print("3. 增强政策检索:")
    try:
        search_tool = tools[0]  # enhanced_policy_search工具
        search_result = search_tool._run(
            query="民生政策", 
            region="六盘水", 
            max_results=3,
            include_summary=True
        )
        print(search_result[:800] + "..." if len(search_result) > 800 else search_result)
    except Exception as e:
        print(f"❌ 政策检索失败: {str(e)}")


async def demo_mcp_tool_registration():
    """演示MCP工具注册功能"""
    print("🔌 MCP工具注册演示")
    print("=" * 50)
    
    try:
        # 调用MCP注册的政策检索函数
        print("\n📞 调用MCP注册的政策检索函数:")
        print("-" * 30)
        
        result = await policy_search(
            query="社会保障",
            region="六盘水",
            search_strategy="auto",
            max_results=3
        )
        
        print(result[:600] + "..." if len(result) > 600 else result)
        
    except Exception as e:
        print(f"❌ MCP工具调用失败: {str(e)}")


def main():
    """主函数"""
    print("🚀 政策检索工具完整演示")
    print("=" * 60)
    print("这个演示将展示政策检索工具的各种功能:")
    print("1. 基础政策检索")
    print("2. 不同检索策略")
    print("3. 门户配置管理")
    print("4. LlamaIndex工具集成") 
    print("5. MCP工具注册")
    print("=" * 60)
    
    async def run_demos():
        try:
            await demo_basic_policy_search()
            await asyncio.sleep(1)
            
            await demo_search_strategies()
            await asyncio.sleep(1)
            
            await demo_portal_management()
            await asyncio.sleep(1)
            
            await demo_llamaindex_integration()
            await asyncio.sleep(1)
            
            await demo_mcp_tool_registration()
            
            print("\n🎉 演示完成！")
            print("=" * 60)
            print("📖 使用说明:")
            print("1. 可通过后台管理界面配置新的门户网站")
            print("2. 支持多种检索策略，可根据需求选择")
            print("3. 已集成到LlamaIndex代理工具链中")
            print("4. 支持MCP工具标准，可与其他系统集成")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n⏹️ 演示被用户中断")
        except Exception as e:
            print(f"\n❌ 演示执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 运行演示
    asyncio.run(run_demos())


if __name__ == "__main__":
    main() 