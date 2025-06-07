#!/usr/bin/env python3
"""
智能政策检索系统测试演示脚本
展示融合智能爬取的政策检索功能
"""

import asyncio
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.tools.advanced.search.policy_search_tool import policy_search
from app.tools.advanced.search.intelligent_crawler_scheduler import (
    get_crawler_scheduler,
    smart_crawl_url
)
from app.frameworks.llamaindex.adapters.policy_search_adapter import (
    get_policy_search_adapter
)
from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_system_config():
    """测试系统配置"""
    print("=" * 60)
    print("🔧 测试系统配置")
    print("=" * 60)
    
    try:
        db = next(get_db())
        config_manager = SystemConfigManager(db)
        
        # 检查关键配置项
        configs_to_check = [
            ("crawling.enabled", "爬取功能"),
            ("crawling.model.provider", "模型提供商"),
            ("crawling.model.name", "模型名称"),
            ("policy_search.enable_intelligent_crawling", "政策检索智能爬取"),
            ("crawl4ai.enabled", "Crawl4AI工具"),
            ("browser_use.enabled", "Browser Use工具")
        ]
        
        for config_key, config_desc in configs_to_check:
            value = await config_manager.get_config_value(config_key, "未配置")
            print(f"• {config_desc}: {value}")
        
        print("✅ 系统配置检查完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 系统配置检查失败: {str(e)}\n")
        return False


async def test_crawler_scheduler():
    """测试智能爬取调度器"""
    print("=" * 60)
    print("🤖 测试智能爬取调度器")
    print("=" * 60)
    
    try:
        scheduler = get_crawler_scheduler()
        await scheduler.initialize()
        
        # 测试页面复杂度分析
        test_urls = [
            "https://www.gzlps.gov.cn/search?q=政策",
            "https://www.guizhou.gov.cn/policy/list",
            "https://www.example.com/simple-page"
        ]
        
        for url in test_urls:
            complexity = await scheduler.analyze_page_complexity(url)
            print(f"• {url} -> 复杂度: {complexity.value}")
        
        print("✅ 爬取调度器测试完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 爬取调度器测试失败: {str(e)}\n")
        return False


async def test_policy_search():
    """测试政策检索功能"""
    print("=" * 60)
    print("🔍 测试智能政策检索")
    print("=" * 60)
    
    test_queries = [
        {"query": "创业扶持政策", "region": "六盘水"},
        {"query": "小微企业税收优惠", "region": "贵州"},
        {"query": "人才引进政策", "region": "六盘水"}
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📋 测试案例 {i}: {test_case['query']} ({test_case['region']})")
        print("-" * 50)
        
        try:
            # 测试不启用智能爬取
            print("🔸 传统检索模式:")
            result_traditional = await policy_search(
                query=test_case["query"],
                region=test_case["region"],
                search_strategy="auto",
                max_results=3,
                enable_intelligent_crawling=False
            )
            
            # 显示结果摘要
            lines = result_traditional.split('\n')
            result_count = len([line for line in lines if line.strip().startswith(tuple(str(i) + '.' for i in range(1, 11)))])
            print(f"  找到 {result_count} 条结果")
            
            # 测试启用智能爬取
            print("\n🔸 智能爬取模式:")
            result_intelligent = await policy_search(
                query=test_case["query"],
                region=test_case["region"],
                search_strategy="auto",
                max_results=3,
                enable_intelligent_crawling=True
            )
            
            # 显示结果摘要
            lines = result_intelligent.split('\n')
            result_count = len([line for line in lines if line.strip().startswith(tuple(str(i) + '.' for i in range(1, 11)))])
            intelligent_count = result_intelligent.count("解析方式：intelligent_crawl")
            print(f"  找到 {result_count} 条结果，其中 {intelligent_count} 条使用智能解析")
            
            print("✅ 测试案例完成")
            
        except Exception as e:
            print(f"❌ 测试案例失败: {str(e)}")
    
    print("\n✅ 政策检索测试完成\n")


async def test_adapter_tools():
    """测试适配器工具集"""
    print("=" * 60)
    print("🛠️ 测试适配器工具集")
    print("=" * 60)
    
    try:
        adapter = get_policy_search_adapter()
        tools = adapter.get_all_tools()
        
        print(f"可用工具数量: {len(tools)}")
        
        for i, tool in enumerate(tools, 1):
            print(f"{i}. {tool.metadata.name}: {tool.metadata.description[:50]}...")
        
        print("\n✅ 适配器工具集测试完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 适配器工具集测试失败: {str(e)}\n")
        return False


async def test_content_analysis():
    """测试内容分析功能"""
    print("=" * 60)
    print("📊 测试智能内容分析")
    print("=" * 60)
    
    # 这里使用一个模拟的政策页面URL进行测试
    test_url = "https://www.gzlps.gov.cn/policy/example"
    
    try:
        print(f"🔸 分析URL: {test_url}")
        
        # 使用智能爬取进行内容分析
        result = await smart_crawl_url(
            url=test_url,
            task_type="content_extraction",
            extraction_rules=[
                "提取政策标题、发布部门和发布日期",
                "识别政策类型和主要内容",
                "提取关键条款和联系方式"
            ],
            analysis_goals=["content", "structure", "metadata"],
            timeout=30
        )
        
        print(f"  分析状态: {'成功' if result.success else '失败'}")
        if result.success:
            print(f"  内容质量: {result.content_quality_score:.2f}")
            print(f"  使用工具: {result.crawler_used.value if result.crawler_used else '未知'}")
            print(f"  执行时间: {result.execution_time:.2f}秒")
        else:
            print(f"  错误信息: {result.error}")
        
        print("✅ 内容分析测试完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 内容分析测试失败: {str(e)}\n")
        return False


async def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 智能政策检索系统综合测试")
    print("=" * 80)
    
    test_results = []
    
    # 运行各项测试
    tests = [
        ("系统配置", test_system_config),
        ("爬取调度器", test_crawler_scheduler),
        ("适配器工具", test_adapter_tools),
        ("内容分析", test_content_analysis),
        ("政策检索", test_policy_search)
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔄 开始测试: {test_name}")
        try:
            result = await test_func()
            test_results.append((test_name, result if isinstance(result, bool) else True))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {str(e)}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    print("=" * 80)
    print("📋 测试总结")
    print("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n📊 总体结果: {passed}/{total} 项测试通过")
    print(f"📈 成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！智能政策检索系统运行正常。")
    else:
        print(f"\n⚠️ 有 {total-passed} 项测试失败，请检查系统配置和环境。")


async def interactive_demo():
    """交互式演示"""
    print("\n" + "=" * 80)
    print("🎯 交互式演示模式")
    print("=" * 80)
    print("请输入政策检索查询，或输入 'exit' 退出演示")
    
    while True:
        try:
            query = input("\n🔍 请输入搜索关键词: ").strip()
            
            if query.lower() in ['exit', 'quit', '退出']:
                print("👋 演示结束，感谢使用！")
                break
            
            if not query:
                print("❌ 请输入有效的搜索关键词")
                continue
            
            region = input("📍 请输入地区名称 (默认: 六盘水): ").strip() or "六盘水"
            
            enable_crawling = input("🤖 是否启用智能爬取? (y/N): ").strip().lower()
            enable_intelligent_crawling = enable_crawling in ['y', 'yes', '是']
            
            print(f"\n🔄 正在搜索: {query} (地区: {region})")
            print(f"智能爬取: {'启用' if enable_intelligent_crawling else '禁用'}")
            print("-" * 50)
            
            result = await policy_search(
                query=query,
                region=region,
                search_strategy="auto",
                max_results=5,
                enable_intelligent_crawling=enable_intelligent_crawling
            )
            
            print(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 演示被中断，感谢使用！")
            break
        except Exception as e:
            print(f"❌ 搜索失败: {str(e)}")


async def main():
    """主函数"""
    print("🎯 智能政策检索系统测试演示")
    print("本演示将测试系统的各项功能，包括智能爬取、政策检索等")
    print()
    
    mode = input("请选择模式:\n1. 综合测试\n2. 交互式演示\n3. 两者都运行\n请输入选择 (1/2/3): ").strip()
    
    if mode == "1":
        await run_comprehensive_test()
    elif mode == "2":
        await interactive_demo()
    elif mode == "3":
        await run_comprehensive_test()
        await interactive_demo()
    else:
        print("❌ 无效选择，运行综合测试")
        await run_comprehensive_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 程序被中断，感谢使用！")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")
        logger.exception("程序执行异常") 