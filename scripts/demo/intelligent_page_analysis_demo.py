#!/usr/bin/env python3
"""
智能页面解析工具综合演示
对比Crawl4AI和Browser Use两套方案的功能和适用场景
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入两套MCP客户端
from app.frameworks.fastmcp.integrations.providers.crawl4ai_llamaindex import Crawl4AILlamaIndexClient
from app.frameworks.fastmcp.integrations.providers.browser_use_llamaindex import BrowserUseLlamaIndexClient
from app.frameworks.fastmcp.integrations.registry import ExternalMCPService

class IntelligentPageAnalysisDemo:
    """智能页面解析演示类"""
    
    def __init__(self, api_key: str):
        """
        初始化演示类
        
        参数:
            api_key: API密钥
        """
        self.api_key = api_key
        self.crawl4ai_client = None
        self.browser_use_client = None
        self._setup_clients()
    
    def _setup_clients(self):
        """设置两个客户端"""
        # Crawl4AI客户端配置
        crawl4ai_service = ExternalMCPService(
            id="crawl4ai_intelligence",
            name="Crawl4AI智能解析器",
            description="基于Crawl4AI的高性能智能页面解析工具",
            url="local://crawl4ai",
            provider="crawl4ai",
            capabilities=["tools", "resources"],
            extra_config={
                "model": {
                    "provider": "openai",
                    "name": "gpt-4o",
                    "temperature": 0.1
                }
            }
        )
        
        # Browser Use客户端配置
        browser_use_service = ExternalMCPService(
            id="browser_use_intelligence",
            name="Browser Use智能浏览器",
            description="基于Browser Use的智能浏览器自动化工具",
            url="local://browser-use",
            provider="browser_use",
            capabilities=["tools", "resources", "chat"],
            extra_config={
                "model": {
                    "provider": "openai",
                    "name": "gpt-4o",
                    "temperature": 0.3
                }
            }
        )
        
        # 创建客户端实例
        self.crawl4ai_client = Crawl4AILlamaIndexClient(crawl4ai_service, self.api_key)
        self.browser_use_client = BrowserUseLlamaIndexClient(browser_use_service, self.api_key)
    
    async def demo_performance_comparison(self):
        """演示性能对比"""
        print("\n" + "="*60)
        print("🚀 性能对比演示：Crawl4AI vs Browser Use")
        print("="*60)
        
        test_url = "https://news.ycombinator.com/"  # 示例新闻站点
        
        print(f"测试URL: {test_url}")
        print("\n正在测试Crawl4AI性能...")
        
        # 测试Crawl4AI
        start_time = time.time()
        crawl4ai_result = await self.crawl4ai_client.call_tool(
            tool_name="advanced_page_intelligence",
            parameters={
                "url": test_url,
                "intelligence_level": "standard",
                "content_types": ["text", "links"],
                "analysis_depth": "medium"
            }
        )
        crawl4ai_time = time.time() - start_time
        
        print(f"✅ Crawl4AI完成时间: {crawl4ai_time:.2f}秒")
        
        print("\n正在测试Browser Use性能...")
        
        # 测试Browser Use
        start_time = time.time()
        browser_use_result = await self.browser_use_client.call_tool(
            tool_name="intelligent_page_analysis",
            parameters={
                "url": test_url,
                "analysis_goals": ["content", "structure"],
                "depth_level": "standard"
            }
        )
        browser_use_time = time.time() - start_time
        
        print(f"✅ Browser Use完成时间: {browser_use_time:.2f}秒")
        
        # 性能分析
        print(f"\n📊 性能对比结果:")
        print(f"  Crawl4AI: {crawl4ai_time:.2f}秒")
        print(f"  Browser Use: {browser_use_time:.2f}秒")
        print(f"  速度差异: {abs(crawl4ai_time - browser_use_time):.2f}秒")
        
        if crawl4ai_time < browser_use_time:
            print(f"  🏆 Crawl4AI 快 {(browser_use_time/crawl4ai_time - 1)*100:.1f}%")
        else:
            print(f"  🏆 Browser Use 快 {(crawl4ai_time/browser_use_time - 1)*100:.1f}%")
        
        return {
            "crawl4ai": {"time": crawl4ai_time, "result": crawl4ai_result},
            "browser_use": {"time": browser_use_time, "result": browser_use_result}
        }
    
    async def demo_content_extraction_comparison(self):
        """演示内容提取对比"""
        print("\n" + "="*60)
        print("📄 内容提取对比演示")
        print("="*60)
        
        test_url = "https://www.wikipedia.org/wiki/Artificial_intelligence"
        extraction_rules = [
            "提取文章的主要定义和概念",
            "识别重要的历史时间点和事件",
            "提取相关的技术术语和专业词汇"
        ]
        
        print(f"测试URL: {test_url}")
        print(f"提取规则: {len(extraction_rules)}个")
        
        # Crawl4AI结构化挖掘
        print("\n正在使用Crawl4AI进行结构化内容挖掘...")
        crawl4ai_result = await self.crawl4ai_client.call_tool(
            tool_name="structural_content_mining",
            parameters={
                "url": test_url,
                "target_structures": ["definitions", "history", "terminology"],
                "semantic_rules": extraction_rules
            }
        )
        
        # Browser Use智能提取
        print("正在使用Browser Use进行智能内容提取...")
        browser_use_result = await self.browser_use_client.call_tool(
            tool_name="smart_content_extraction",
            parameters={
                "url": test_url,
                "extraction_rules": extraction_rules,
                "output_format": "structured"
            }
        )
        
        # 结果对比
        print("\n📋 内容提取结果对比:")
        
        if crawl4ai_result["status"] == "success":
            extracted_content = crawl4ai_result["data"].get("extracted_content", {})
            print(f"  Crawl4AI提取项目数: {len(extracted_content) if isinstance(extracted_content, list) else 'N/A'}")
            print(f"  内容长度: {crawl4ai_result['data'].get('raw_content_length', 0)} 字符")
        else:
            print(f"  Crawl4AI失败: {crawl4ai_result.get('error', 'Unknown error')}")
        
        if browser_use_result["status"] == "success":
            extracted_data = browser_use_result["data"].get("extracted_data", {})
            print(f"  Browser Use提取规则数: {len(extracted_data)}")
            total_confidence = sum(item.get("confidence", 0) for item in extracted_data.values())
            avg_confidence = total_confidence / len(extracted_data) if extracted_data else 0
            print(f"  平均置信度: {avg_confidence:.2f}")
        else:
            print(f"  Browser Use失败: {browser_use_result.get('error', 'Unknown error')}")
        
        return {
            "crawl4ai": crawl4ai_result,
            "browser_use": browser_use_result
        }
    
    async def demo_batch_processing_capability(self):
        """演示批量处理能力"""
        print("\n" + "="*60)
        print("⚡ 批量处理能力演示")
        print("="*60)
        
        test_urls = [
            "https://example.com",
            "https://httpbin.org/html",
            "https://jsonplaceholder.typicode.com"
        ]
        
        print(f"测试URL数量: {len(test_urls)}")
        
        # Crawl4AI批量处理
        print("\n正在使用Crawl4AI进行批量智能爬取...")
        start_time = time.time()
        crawl4ai_batch_result = await self.crawl4ai_client.call_tool(
            tool_name="batch_intelligent_crawling",
            parameters={
                "urls": test_urls,
                "crawl_strategy": "parallel",
                "max_concurrent": 2,
                "unified_analysis": True
            }
        )
        crawl4ai_batch_time = time.time() - start_time
        
        # Browser Use多页面分析
        print("正在使用Browser Use进行多页面分析...")
        start_time = time.time()
        browser_use_multi_result = await self.browser_use_client.call_tool(
            tool_name="multi_page_intelligence",
            parameters={
                "start_url": test_urls[0],  # 从第一个URL开始
                "navigation_strategy": "auto",
                "max_pages": len(test_urls),
                "analysis_focus": "content_similarity"
            }
        )
        browser_use_multi_time = time.time() - start_time
        
        # 批量处理结果分析
        print(f"\n⚡ 批量处理结果:")
        print(f"  Crawl4AI批量处理时间: {crawl4ai_batch_time:.2f}秒")
        print(f"  Browser Use多页面分析时间: {browser_use_multi_time:.2f}秒")
        
        if crawl4ai_batch_result["status"] == "success":
            data = crawl4ai_batch_result["data"]
            print(f"  Crawl4AI成功处理: {data.get('successful_crawls', 0)}/{data.get('total_urls', 0)} 个URL")
            print(f"  统一分析: {'✅' if data.get('unified_analysis') else '❌'}")
        
        if browser_use_multi_result["status"] == "success":
            data = browser_use_multi_result["data"]
            print(f"  Browser Use分析页面数: {data.get('pages_analyzed', 0)}")
            print(f"  跨页面分析: {'✅' if data.get('cross_page_analysis') else '❌'}")
        
        return {
            "crawl4ai": {"time": crawl4ai_batch_time, "result": crawl4ai_batch_result},
            "browser_use": {"time": browser_use_multi_time, "result": browser_use_multi_result}
        }
    
    async def demo_dynamic_content_handling(self):
        """演示动态内容处理"""
        print("\n" + "="*60)
        print("🎭 动态内容处理演示")
        print("="*60)
        
        # 选择一个有动态内容的测试站点
        dynamic_url = "https://httpbin.org/delay/2"  # 有延迟的站点模拟动态加载
        
        print(f"测试动态URL: {dynamic_url}")
        
        # Crawl4AI动态内容分析
        print("\n正在使用Crawl4AI分析动态内容...")
        crawl4ai_dynamic_result = await self.crawl4ai_client.call_tool(
            tool_name="dynamic_content_analysis",
            parameters={
                "url": dynamic_url,
                "interaction_script": "await new Promise(resolve => setTimeout(resolve, 3000));",
                "analysis_triggers": ["scroll", "wait"]
            }
        )
        
        # Browser Use表单交互（如果适用）
        print("正在使用Browser Use进行自适应交互...")
        browser_use_adaptive_result = await self.browser_use_client.call_tool(
            tool_name="adaptive_form_interaction",
            parameters={
                "url": dynamic_url,
                "form_intent": "测试动态内容响应",
                "auto_submit": False,
                "result_analysis": True
            }
        )
        
        # 动态内容处理结果
        print(f"\n🎭 动态内容处理结果:")
        
        if crawl4ai_dynamic_result["status"] == "success":
            data = crawl4ai_dynamic_result["data"]
            print(f"  Crawl4AI动态分析: ✅")
            print(f"  触发器: {data.get('interaction_triggers', [])}")
            extracted = data.get('extracted_dynamic_content', {})
            print(f"  动态内容类型: {len(extracted) if isinstance(extracted, dict) else 'N/A'}")
        else:
            print(f"  Crawl4AI动态分析: ❌ {crawl4ai_dynamic_result.get('error', '')}")
        
        if browser_use_adaptive_result["status"] == "success":
            data = browser_use_adaptive_result["data"]
            print(f"  Browser Use自适应交互: ✅")
            print(f"  表单意图: {data.get('form_intent', 'N/A')}")
            analysis = data.get('analysis_results', {})
            print(f"  结果分析: {'✅' if analysis else '❌'}")
        else:
            print(f"  Browser Use自适应交互: ❌ {browser_use_adaptive_result.get('error', '')}")
        
        return {
            "crawl4ai": crawl4ai_dynamic_result,
            "browser_use": browser_use_adaptive_result
        }
    
    async def demo_semantic_search_capability(self):
        """演示语义搜索能力"""
        print("\n" + "="*60)
        print("🔍 语义搜索能力演示")
        print("="*60)
        
        test_url = "https://en.wikipedia.org/wiki/Machine_learning"
        search_queries = [
            "机器学习的定义和核心概念",
            "主要的机器学习算法类型",
            "机器学习的实际应用场景"
        ]
        
        print(f"测试URL: {test_url}")
        print(f"搜索查询: {len(search_queries)}个")
        
        # Crawl4AI语义搜索
        print("\n正在使用Crawl4AI进行语义搜索提取...")
        crawl4ai_semantic_result = await self.crawl4ai_client.call_tool(
            tool_name="semantic_search_extraction",
            parameters={
                "url": test_url,
                "search_queries": search_queries,
                "extraction_goals": ["定义提取", "分类总结", "应用案例"],
                "similarity_threshold": 0.75
            }
        )
        
        # Browser Use智能页面分析（深度模式）
        print("正在使用Browser Use进行深度智能分析...")
        browser_use_intelligent_result = await self.browser_use_client.call_tool(
            tool_name="intelligent_page_analysis",
            parameters={
                "url": test_url,
                "analysis_goals": ["content", "structure", "metadata"],
                "depth_level": "deep"
            }
        )
        
        # 语义搜索结果对比
        print(f"\n🔍 语义搜索结果:")
        
        if crawl4ai_semantic_result["status"] == "success":
            data = crawl4ai_semantic_result["data"]
            search_results = data.get("search_results", {})
            extraction_results = data.get("extraction_results", {})
            print(f"  Crawl4AI语义搜索: ✅")
            print(f"  搜索结果数: {len(search_results)}")
            print(f"  提取目标数: {len(extraction_results)}")
            
            # 计算平均置信度
            confidences = [result.get("confidence", 0) for result in search_results.values()]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            print(f"  平均搜索置信度: {avg_confidence:.2f}")
        else:
            print(f"  Crawl4AI语义搜索: ❌ {crawl4ai_semantic_result.get('error', '')}")
        
        if browser_use_intelligent_result["status"] == "success":
            data = browser_use_intelligent_result["data"]
            analysis_results = data.get("analysis_results", {})
            print(f"  Browser Use深度分析: ✅")
            print(f"  分析维度数: {len(analysis_results)}")
            
            if "semantic_analysis" in analysis_results:
                print(f"  语义分析: ✅")
            if "entity_extraction" in analysis_results:
                print(f"  实体提取: ✅")
        else:
            print(f"  Browser Use深度分析: ❌ {browser_use_intelligent_result.get('error', '')}")
        
        return {
            "crawl4ai": crawl4ai_semantic_result,
            "browser_use": browser_use_intelligent_result
        }
    
    async def demo_tool_capabilities_overview(self):
        """演示工具能力概览"""
        print("\n" + "="*60)
        print("🛠️  工具能力概览")
        print("="*60)
        
        # 获取Crawl4AI工具列表
        crawl4ai_tools = await self.crawl4ai_client.get_tools()
        
        # 获取Browser Use工具列表
        browser_use_tools = await self.browser_use_client.get_tools()
        
        print("🔧 Crawl4AI工具集:")
        for i, tool in enumerate(crawl4ai_tools, 1):
            print(f"  {i}. {tool['name']}")
            print(f"     描述: {tool['description']}")
            required_params = tool['parameters'].get('required', [])
            print(f"     必需参数: {', '.join(required_params)}")
            print()
        
        print("🎯 Browser Use工具集:")
        for i, tool in enumerate(browser_use_tools, 1):
            print(f"  {i}. {tool['name']}")
            print(f"     描述: {tool['description']}")
            required_params = tool['parameters'].get('required', [])
            print(f"     必需参数: {', '.join(required_params)}")
            print()
        
        # 能力对比
        print("📊 能力对比总结:")
        print(f"  Crawl4AI工具数量: {len(crawl4ai_tools)}")
        print(f"  Browser Use工具数量: {len(browser_use_tools)}")
        
        crawl4ai_features = set()
        browser_use_features = set()
        
        for tool in crawl4ai_tools:
            if "batch" in tool['name']:
                crawl4ai_features.add("批量处理")
            if "dynamic" in tool['name']:
                crawl4ai_features.add("动态内容")
            if "semantic" in tool['name']:
                crawl4ai_features.add("语义搜索")
            if "structural" in tool['name']:
                crawl4ai_features.add("结构化挖掘")
        
        for tool in browser_use_tools:
            if "multi" in tool['name']:
                browser_use_features.add("多页面分析")
            if "adaptive" in tool['name']:
                browser_use_features.add("自适应交互")
            if "intelligent" in tool['name']:
                browser_use_features.add("智能分析")
        
        print(f"\n  Crawl4AI特色功能: {', '.join(crawl4ai_features)}")
        print(f"  Browser Use特色功能: {', '.join(browser_use_features)}")
        
        return {
            "crawl4ai_tools": crawl4ai_tools,
            "browser_use_tools": browser_use_tools,
            "feature_comparison": {
                "crawl4ai": list(crawl4ai_features),
                "browser_use": list(browser_use_features)
            }
        }
    
    def print_recommendations(self):
        """打印使用建议"""
        print("\n" + "="*60)
        print("💡 使用建议和最佳实践")
        print("="*60)
        
        print("🚀 Crawl4AI适用场景:")
        print("  ✅ 大规模批量网页爬取")
        print("  ✅ 高性能要求的场景")
        print("  ✅ 结构化数据提取")
        print("  ✅ 静态内容为主的网站")
        print("  ✅ API化的自动化流程")
        
        print("\n🎯 Browser Use适用场景:")
        print("  ✅ 复杂交互式网站")
        print("  ✅ 需要模拟人类行为")
        print("  ✅ 表单自动化填写")
        print("  ✅ 单页应用(SPA)处理")
        print("  ✅ 需要深度页面分析")
        
        print("\n⚖️  选择建议:")
        print("  📊 数据量大、速度优先 → 选择Crawl4AI")
        print("  🎭 交互复杂、精度优先 → 选择Browser Use")
        print("  🔄 混合场景 → 两者结合使用")
        
        print("\n🛡️  注意事项:")
        print("  ⚠️  遵守网站robots.txt规则")
        print("  ⚠️  控制爬取频率，避免过载")
        print("  ⚠️  处理反爬虫机制")
        print("  ⚠️  注意数据隐私和合规性")

async def main():
    """主函数"""
    print("🚀 智能页面解析工具综合演示")
    print("Crawl4AI vs Browser Use 全面对比")
    print("="*60)
    
    # 请替换为你的实际API密钥
    API_KEY = "your-openai-api-key-here"
    
    if API_KEY == "your-openai-api-key-here":
        print("⚠️  请先设置你的API密钥！")
        print("修改代码中的 API_KEY 变量为你的实际OpenAI API密钥")
        return
    
    # 创建演示实例
    demo = IntelligentPageAnalysisDemo(API_KEY)
    
    try:
        # 工具能力概览
        await demo.demo_tool_capabilities_overview()
        
        # 性能对比
        await demo.demo_performance_comparison()
        
        # 内容提取对比
        await demo.demo_content_extraction_comparison()
        
        # 批量处理能力
        await demo.demo_batch_processing_capability()
        
        # 动态内容处理
        await demo.demo_dynamic_content_handling()
        
        # 语义搜索能力
        await demo.demo_semantic_search_capability()
        
        # 使用建议
        demo.print_recommendations()
        
        print("\n🎉 演示完成！")
        print("两套工具各有优势，可根据具体需求选择使用。")
        
    except KeyboardInterrupt:
        print("\n👋 演示程序已停止")
    except Exception as e:
        print(f"\n❌ 演示程序出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if demo.crawl4ai_client:
            await demo.crawl4ai_client.close()
        if demo.browser_use_client:
            await demo.browser_use_client.close()

if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())