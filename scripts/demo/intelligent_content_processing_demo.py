#!/usr/bin/env python3
"""
智能内容处理演示脚本
展示markitdown框架集成、智能爬虫和内容分析功能
"""

import sys
import os
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from app.tools.advanced.content.markitdown_adapter import get_markitdown_adapter
from app.tools.advanced.search.enhanced_web_crawler import get_enhanced_web_crawler
from app.tools.advanced.search.intelligent_crawler_scheduler import IntelligentCrawlerScheduler


class ContentProcessingDemo:
    """智能内容处理演示类"""
    
    def __init__(self):
        """初始化演示"""
        self.markitdown_adapter = None
        self.web_crawler = None
        self.crawler_scheduler = None
        
    async def initialize(self):
        """初始化所有组件"""
        print("🚀 初始化智能内容处理组件...")
        
        try:
            # 初始化MarkItDown适配器
            self.markitdown_adapter = get_markitdown_adapter()
            await self.markitdown_adapter.initialize()
            print("✅ MarkItDown适配器初始化完成")
            
            # 初始化增强网页爬虫
            self.web_crawler = get_enhanced_web_crawler()
            await self.web_crawler.initialize()
            print("✅ 增强网页爬虫初始化完成")
            
            # 初始化智能爬虫调度器
            self.crawler_scheduler = IntelligentCrawlerScheduler()
            await self.crawler_scheduler.initialize()
            print("✅ 智能爬虫调度器初始化完成")
            
            print("🎉 所有组件初始化成功！\n")
            
        except Exception as e:
            print(f"❌ 组件初始化失败: {str(e)}")
            raise
    
    async def demo_markitdown_conversion(self):
        """演示MarkItDown内容转换"""
        print("=" * 60)
        print("📄 MarkItDown内容转换演示")
        print("=" * 60)
        
        # 测试HTML转换
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试页面</title>
            <meta name="description" content="这是一个测试页面">
        </head>
        <body>
            <h1>主标题</h1>
            <p>这是第一段内容，包含了一些<strong>重要</strong>的信息。</p>
            
            <h2>子标题</h2>
            <ul>
                <li>列表项目1</li>
                <li>列表项目2</li>
                <li>列表项目3</li>
            </ul>
            
            <h3>数据表格</h3>
            <table>
                <tr>
                    <th>姓名</th>
                    <th>年龄</th>
                    <th>职业</th>
                </tr>
                <tr>
                    <td>张三</td>
                    <td>25</td>
                    <td>工程师</td>
                </tr>
                <tr>
                    <td>李四</td>
                    <td>30</td>
                    <td>设计师</td>
                </tr>
            </table>
            
            <p>这是最后一段内容，包含一个<a href="https://example.com">外部链接</a>。</p>
        </body>
        </html>
        """
        
        print("🔄 转换HTML内容为Markdown...")
        
        try:
            start_time = time.time()
            result = self.markitdown_adapter.convert_to_markdown(
                html_content, 
                "html", 
                "https://example.com/test"
            )
            end_time = time.time()
            
            print(f"⏱️  转换耗时: {end_time - start_time:.2f}秒")
            print(f"✅ 转换成功: {result['conversion_success']}")
            print(f"📝 提取标题: {result.get('title', 'N/A')}")
            print(f"📊 元数据: {len(result.get('metadata', {}))} 项")
            
            print("\n📄 转换后的Markdown内容:")
            print("-" * 40)
            print(result.get('markdown', '转换失败')[:500] + "...")
            print("-" * 40)
            
            if result.get('metadata'):
                print("\n📊 提取的元数据:")
                for key, value in result['metadata'].items():
                    print(f"  • {key}: {value}")
            
        except Exception as e:
            print(f"❌ 转换失败: {str(e)}")
        
        print("\n")
    
    async def demo_enhanced_web_crawling(self):
        """演示增强网页爬虫"""
        print("=" * 60)
        print("🕷️  增强网页爬虫演示")
        print("=" * 60)
        
        # 测试URL列表
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/json",
            "https://example.com"
        ]
        
        print(f"🎯 准备爬取 {len(test_urls)} 个测试URL...")
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n📡 [{i}/{len(test_urls)}] 爬取: {url}")
            
            try:
                start_time = time.time()
                result = await self.web_crawler.crawl_url(url)
                end_time = time.time()
                
                print(f"⏱️  爬取耗时: {end_time - start_time:.2f}秒")
                print(f"📊 状态: {result.get('status', 'unknown')}")
                
                if result.get('status') == 'success':
                    quality = result.get('quality_analysis', {})
                    print(f"🎯 质量评分: {quality.get('overall_score', 0):.2f}")
                    print(f"📝 质量等级: {quality.get('quality_level', 'unknown')}")
                    
                    extracted = result.get('extracted_data', {})
                    if extracted:
                        print(f"📄 提取标题: {extracted.get('title', 'N/A')}")
                        print(f"🔗 链接数量: {extracted.get('links', {}).get('total_links', 0)}")
                        
                        if extracted.get('structured_data'):
                            print(f"📊 结构化数据: {len(extracted['structured_data'])} 项")
                
                elif result.get('status') == 'failed':
                    print(f"❌ 爬取失败: {result.get('error', 'unknown error')}")
                
                elif result.get('status') == 'low_quality':
                    quality = result.get('quality_analysis', {})
                    print(f"⚠️  质量不达标: {quality.get('overall_score', 0):.2f}")
                    recommendations = quality.get('recommendations', [])
                    if recommendations:
                        print("💡 改进建议:")
                        for rec in recommendations:
                            print(f"   • {rec}")
                
            except Exception as e:
                print(f"❌ 爬取异常: {str(e)}")
        
        print("\n")
    
    async def demo_intelligent_crawler_scheduler(self):
        """演示智能爬虫调度器"""
        print("=" * 60)
        print("🧠 智能爬虫调度器演示")
        print("=" * 60)
        
        # 测试不同类型的页面
        test_cases = [
            {
                "url": "https://httpbin.org/html",
                "description": "简单HTML页面"
            },
            {
                "url": "https://httpbin.org/json",
                "description": "JSON API响应"
            },
            {
                "url": "https://example.com",
                "description": "示例网站"
            }
        ]
        
        print(f"🎯 准备使用智能调度器分析 {len(test_cases)} 个页面...")
        
        for i, test_case in enumerate(test_cases, 1):
            url = test_case["url"]
            description = test_case["description"]
            
            print(f"\n🔍 [{i}/{len(test_cases)}] 分析: {description}")
            print(f"🌐 URL: {url}")
            
            try:
                start_time = time.time()
                
                # 使用智能调度器进行分析
                result = await self.crawler_scheduler.intelligent_crawl(url)
                
                end_time = time.time()
                
                print(f"⏱️  分析耗时: {end_time - start_time:.2f}秒")
                print(f"📊 状态: {result.get('status', 'unknown')}")
                
                if result.get('crawler_used'):
                    print(f"🤖 使用的爬虫: {result['crawler_used']}")
                
                if result.get('content_analysis'):
                    analysis = result['content_analysis']
                    print(f"📝 内容长度: {analysis.get('content_length', 0)} 字符")
                    print(f"🎯 复杂度评分: {analysis.get('complexity_score', 0):.2f}")
                    
                    if analysis.get('markdown_content'):
                        markdown_preview = analysis['markdown_content'][:200] + "..."
                        print(f"📄 Markdown预览: {markdown_preview}")
                
                if result.get('quality_assessment'):
                    quality = result['quality_assessment']
                    print(f"✨ 整体质量: {quality.get('overall_score', 0):.2f}")
                    
                    recommendations = quality.get('recommendations', [])
                    if recommendations:
                        print("💡 优化建议:")
                        for rec in recommendations[:3]:  # 只显示前3个建议
                            print(f"   • {rec}")
                
            except Exception as e:
                print(f"❌ 分析异常: {str(e)}")
        
        print("\n")
    
    async def demo_batch_processing(self):
        """演示批量处理功能"""
        print("=" * 60)
        print("📦 批量内容处理演示")
        print("=" * 60)
        
        # 批量测试URL
        batch_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/xml",
            "https://httpbin.org/json",
            "https://example.com"
        ]
        
        print(f"🎯 批量处理 {len(batch_urls)} 个URL...")
        
        try:
            start_time = time.time()
            
            # 使用增强爬虫进行批量处理
            results = await self.web_crawler.crawl_urls_batch(batch_urls)
            
            end_time = time.time()
            
            print(f"⏱️  批量处理耗时: {end_time - start_time:.2f}秒")
            print(f"📊 处理结果统计:")
            
            # 统计结果
            status_counts = {}
            quality_scores = []
            
            for result in results:
                status = result.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if result.get('quality_analysis', {}).get('overall_score'):
                    quality_scores.append(result['quality_analysis']['overall_score'])
            
            print("\n📈 状态分布:")
            for status, count in status_counts.items():
                print(f"   • {status}: {count} 个")
            
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                print(f"\n🎯 平均质量评分: {avg_quality:.2f}")
                print(f"🏆 最高质量评分: {max(quality_scores):.2f}")
                print(f"⬇️  最低质量评分: {min(quality_scores):.2f}")
            
            # 显示成功处理的详细信息
            successful_results = [r for r in results if r.get('status') == 'success']
            if successful_results:
                print(f"\n✅ 成功处理的页面详情:")
                for i, result in enumerate(successful_results, 1):
                    extracted = result.get('extracted_data', {})
                    print(f"   [{i}] {result.get('url', 'N/A')}")
                    print(f"       标题: {extracted.get('title', 'N/A')}")
                    print(f"       质量: {result.get('quality_analysis', {}).get('overall_score', 0):.2f}")
        
        except Exception as e:
            print(f"❌ 批量处理失败: {str(e)}")
        
        print("\n")
    
    async def demo_content_comparison(self):
        """演示内容处理对比"""
        print("=" * 60)
        print("⚖️  内容处理方法对比演示")
        print("=" * 60)
        
        test_url = "https://httpbin.org/html"
        
        print(f"🎯 使用不同方法处理同一URL: {test_url}")
        
        # 方法1：直接使用MarkItDown
        print("\n📄 方法1: 直接MarkItDown转换")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(test_url) as response:
                    html_content = await response.text()
            
            start_time = time.time()
            markitdown_result = self.markitdown_adapter.convert_to_markdown(html_content, "html", test_url)
            end_time = time.time()
            
            print(f"⏱️  处理时间: {end_time - start_time:.2f}秒")
            print(f"✅ 转换成功: {markitdown_result['conversion_success']}")
            print(f"📝 内容长度: {len(markitdown_result.get('markdown', ''))}")
            
        except Exception as e:
            print(f"❌ MarkItDown转换失败: {str(e)}")
        
        # 方法2：增强网页爬虫
        print("\n🕷️  方法2: 增强网页爬虫")
        try:
            start_time = time.time()
            crawler_result = await self.web_crawler.crawl_url(test_url)
            end_time = time.time()
            
            print(f"⏱️  处理时间: {end_time - start_time:.2f}秒")
            print(f"📊 处理状态: {crawler_result.get('status')}")
            print(f"🎯 质量评分: {crawler_result.get('quality_analysis', {}).get('overall_score', 0):.2f}")
            
            extracted = crawler_result.get('extracted_data', {})
            if extracted:
                print(f"📄 提取信息: {len(extracted)} 项")
        
        except Exception as e:
            print(f"❌ 增强爬虫处理失败: {str(e)}")
        
        # 方法3：智能调度器
        print("\n🧠 方法3: 智能调度器")
        try:
            start_time = time.time()
            scheduler_result = await self.crawler_scheduler.intelligent_crawl(test_url)
            end_time = time.time()
            
            print(f"⏱️  处理时间: {end_time - start_time:.2f}秒")
            print(f"📊 处理状态: {scheduler_result.get('status')}")
            print(f"🤖 选择的方法: {scheduler_result.get('crawler_used', 'N/A')}")
            
            if scheduler_result.get('quality_assessment'):
                quality = scheduler_result['quality_assessment']
                print(f"✨ 整体质量: {quality.get('overall_score', 0):.2f}")
        
        except Exception as e:
            print(f"❌ 智能调度器处理失败: {str(e)}")
        
        print("\n")
    
    def print_performance_summary(self):
        """打印性能总结"""
        print("=" * 60)
        print("📊 演示总结")
        print("=" * 60)
        
        print("🎉 智能内容处理演示完成！")
        print("\n💡 主要功能亮点:")
        print("   • ✅ MarkItDown框架集成 - 支持多种格式转换")
        print("   • ✅ 增强网页爬虫 - 智能内容质量分析")
        print("   • ✅ 智能调度器 - 自动选择最佳处理方案")
        print("   • ✅ 批量处理 - 高效并发处理多个URL")
        print("   • ✅ 质量评估 - 全方位内容质量分析")
        
        print("\n🔧 技术特性:")
        print("   • 异步处理架构")
        print("   • 智能错误恢复")
        print("   • 可配置质量阈值")
        print("   • 结构化数据提取")
        print("   • 多格式内容支持")
        
        print("\n🚀 适用场景:")
        print("   • 网页内容采集与分析")
        print("   • 文档格式转换与清洗")
        print("   • 知识库内容预处理")
        print("   • 搜索结果质量评估")
        print("   • 批量内容处理任务")
        
        print("\n📞 如有问题，请参考项目文档或联系开发团队。")
    
    async def run_full_demo(self):
        """运行完整演示"""
        try:
            await self.initialize()
            
            # 运行各个演示模块
            await self.demo_markitdown_conversion()
            await self.demo_enhanced_web_crawling()
            await self.demo_intelligent_crawler_scheduler()
            await self.demo_batch_processing()
            await self.demo_content_comparison()
            
            # 打印总结
            self.print_performance_summary()
            
        except Exception as e:
            print(f"❌ 演示运行失败: {str(e)}")
            raise
        finally:
            # 清理资源
            if self.web_crawler:
                await self.web_crawler.close()
    
    async def run_interactive_demo(self):
        """运行交互式演示"""
        await self.initialize()
        
        while True:
            print("\n" + "=" * 60)
            print("🎮 智能内容处理交互式演示")
            print("=" * 60)
            print("请选择演示项目:")
            print("1. MarkItDown内容转换")
            print("2. 增强网页爬虫")
            print("3. 智能爬虫调度器")
            print("4. 批量处理")
            print("5. 方法对比")
            print("6. 运行完整演示")
            print("0. 退出")
            
            choice = input("\n请输入选项 (0-6): ").strip()
            
            try:
                if choice == "1":
                    await self.demo_markitdown_conversion()
                elif choice == "2":
                    await self.demo_enhanced_web_crawling()
                elif choice == "3":
                    await self.demo_intelligent_crawler_scheduler()
                elif choice == "4":
                    await self.demo_batch_processing()
                elif choice == "5":
                    await self.demo_content_comparison()
                elif choice == "6":
                    await self.run_full_demo()
                    break
                elif choice == "0":
                    print("👋 感谢使用智能内容处理演示！")
                    break
                else:
                    print("❌ 无效选项，请重新选择。")
                    
            except Exception as e:
                print(f"❌ 演示执行失败: {str(e)}")
                print("请检查网络连接或联系技术支持。")
        
        # 清理资源
        if self.web_crawler:
            await self.web_crawler.close()


async def main():
    """主函数"""
    print("🌟 欢迎使用智能内容处理演示系统！")
    print("本系统集成了markitdown框架、增强网页爬虫和智能调度器。")
    
    demo = ContentProcessingDemo()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "full":
            print("\n🚀 运行完整演示...")
            await demo.run_full_demo()
        elif mode == "interactive":
            print("\n🎮 启动交互式演示...")
            await demo.run_interactive_demo()
        else:
            print(f"❌ 未知模式: {mode}")
            print("支持的模式: full, interactive")
    else:
        print("\n🎮 默认启动交互式演示...")
        await demo.run_interactive_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，演示结束。")
    except Exception as e:
        print(f"\n❌ 程序异常退出: {str(e)}")
        sys.exit(1) 