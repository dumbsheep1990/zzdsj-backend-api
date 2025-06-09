#!/usr/bin/env python3
"""
Browser Use MCP工具使用示例
展示如何使用MCP框架集成的Browser Use进行智能化的检索结果页面爬取
"""

import asyncio
import json
from typing import Dict, Any, List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入MCP框架
from app.frameworks.fastmcp.integrations.providers.generic import GenericMCPClient
from app.frameworks.fastmcp.integrations.registry import ExternalMCPService

class BrowserUseMCPDemo:
    """Browser Use MCP工具演示类"""
    
    def __init__(self, api_key: str):
        """
        初始化演示类
        
        参数:
            api_key: OpenAI或其他LLM服务的API密钥
        """
        self.api_key = api_key
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """设置MCP客户端"""
        # 创建MCP服务配置
        service_config = ExternalMCPService(
            id="browser_use_demo",
            name="Browser Use智能浏览器",
            description="基于AI的智能浏览器自动化工具",
            url="local://browser-use",
            provider="browser_use",
            capabilities=["tools", "resources", "chat"],
            extra_config={
                "model": {
                    "provider": "openai",  # 或 "anthropic", "ollama"
                    "name": "gpt-4o",
                    "temperature": 0.3
                }
            }
        )
        
        # 创建客户端
        self.client = GenericMCPClient(service_config, self.api_key)
    
    async def demo_smart_search_with_extraction(self):
        """演示：智能搜索并深度提取内容"""
        print("\n" + "="*50)
        print("演示1: 智能搜索并深度提取内容")
        print("="*50)
        
        # 搜索查询
        search_params = {
            "query": "人工智能最新发展趋势 2024",
            "search_engine": "google",
            "max_results": 3,
            "deep_extract": True  # 深入每个链接提取内容
        }
        
        print(f"搜索查询: {search_params['query']}")
        print("正在执行智能搜索...")
        
        try:
            result = await self.client.call_tool(
                tool_name="smart_search",
                parameters=search_params
            )
            
            if result["status"] == "success":
                data = result["data"]
                print(f"✅ 搜索完成！找到 {data['total_found']} 个结果")
                
                for i, item in enumerate(data["results"], 1):
                    print(f"\n结果 {i}:")
                    print(f"  标题: {item['title']}")
                    print(f"  链接: {item['url']}")
                    print(f"  摘要: {item['snippet'][:100]}...")
                    
            else:
                print(f"❌ 搜索失败: {result['error']}")
                
        except Exception as e:
            print(f"❌ 执行出错: {str(e)}")
    
    async def demo_policy_search_automation(self):
        """演示：政策搜索自动化（基于你提到的检索场景）"""
        print("\n" + "="*50)
        print("演示2: 政策文档检索自动化")
        print("="*50)
        
        # 多页面爬取政策文档
        scraping_params = {
            "start_url": "https://www.gov.cn/zhengce/",  # 示例政策网站
            "scraping_rule": """
提取政策文档信息，包括：
1. 政策标题
2. 发布时间  
3. 发布机构
4. 政策摘要
5. 政策全文链接
6. 相关关键词

对每个政策条目：
- 点击进入详情页
- 提取完整政策内容
- 按结构化格式整理
            """,
            "max_pages": 5,
            "pagination_strategy": "auto"
        }
        
        print("正在执行政策文档自动化爬取...")
        print(f"目标网站: {scraping_params['start_url']}")
        print(f"预计爬取页面: {scraping_params['max_pages']} 页")
        
        try:
            result = await self.client.call_tool(
                tool_name="multi_page_scraping",
                parameters=scraping_params
            )
            
            if result["status"] == "success":
                data = result["data"]
                print(f"✅ 爬取完成！处理了 {data['pages_scraped']} 个页面")
                
                for i, page_data in enumerate(data["data"], 1):
                    print(f"\n页面 {i}:")
                    print(f"  URL: {page_data['url']}")
                    print(f"  内容预览: {str(page_data['content'])[:200]}...")
                    
            else:
                print(f"❌ 爬取失败: {result['error']}")
                
        except Exception as e:
            print(f"❌ 执行出错: {str(e)}")
    
    async def demo_adaptive_form_filling(self):
        """演示：自适应表单填写"""
        print("\n" + "="*50)
        print("演示3: 自适应表单填写")
        print("="*50)
        
        # 表单自动化
        form_params = {
            "url": "https://example.com/search-form",  # 示例搜索表单
            "form_data": {
                "search_query": "智能化政策检索",
                "date_range": "2024-01-01 to 2024-12-31",
                "category": "科技政策",
                "region": "全国"
            },
            "submit": True
        }
        
        print("正在执行智能表单填写...")
        print(f"目标表单: {form_params['url']}")
        
        try:
            result = await self.client.call_tool(
                tool_name="form_automation",
                parameters=form_params
            )
            
            if result["status"] == "success":
                data = result["data"]
                print("✅ 表单填写完成！")
                print(f"  填写的字段: {list(data['form_filled'].keys())}")
                print(f"  是否提交: {data['submitted']}")
                
            else:
                print(f"❌ 表单填写失败: {result['error']}")
                
        except Exception as e:
            print(f"❌ 执行出错: {str(e)}")
    
    async def demo_complex_search_workflow(self):
        """演示：复杂搜索工作流（结合多个工具）"""
        print("\n" + "="*50)
        print("演示4: 复杂检索工作流")
        print("="*50)
        
        # 步骤1: 智能搜索找到相关页面
        search_result = await self.client.call_tool(
            tool_name="smart_search",
            parameters={
                "query": "最新人工智能政策法规",
                "search_engine": "google",
                "max_results": 2,
                "deep_extract": False
            }
        )
        
        if search_result["status"] != "success":
            print(f"❌ 搜索失败: {search_result['error']}")
            return
        
        print("✅ 第1步：搜索完成")
        
        # 步骤2: 对找到的页面进行深度内容提取
        for i, result_item in enumerate(search_result["data"]["results"]):
            print(f"\n正在深度提取第{i+1}个结果...")
            
            extract_result = await self.client.call_tool(
                tool_name="browse_and_extract",
                parameters={
                    "url": result_item["url"],
                    "task": "提取页面中的政策文档信息，包括标题、发布时间、内容摘要和关键条款",
                    "extract_format": "json",
                    "max_steps": 8
                }
            )
            
            if extract_result["status"] == "success":
                print(f"✅ 第{i+2}步：内容提取完成")
                content = extract_result["data"]["content"]
                print(f"  提取内容长度: {len(content)} 字符")
            else:
                print(f"❌ 第{i+2}步：内容提取失败: {extract_result['error']}")
        
        print("\n🎉 复杂检索工作流完成！")
    
    async def demo_get_available_tools(self):
        """演示：获取可用工具列表"""
        print("\n" + "="*50)
        print("可用的Browser Use MCP工具")
        print("="*50)
        
        try:
            tools = await self.client.get_tools()
            
            for i, tool in enumerate(tools, 1):
                print(f"\n{i}. {tool['name']}")
                print(f"   描述: {tool['description']}")
                print(f"   参数: {list(tool['parameters']['properties'].keys())}")
                
        except Exception as e:
            print(f"❌ 获取工具列表失败: {str(e)}")

async def main():
    """主函数"""
    print("🚀 Browser Use MCP工具演示程序")
    print("="*60)
    
    # 请替换为你的实际API密钥
    API_KEY = "your-openai-api-key-here"
    
    if API_KEY == "your-openai-api-key-here":
        print("⚠️  请先设置你的API密钥！")
        print("修改代码中的 API_KEY 变量为你的实际OpenAI API密钥")
        return
    
    # 创建演示实例
    demo = BrowserUseMCPDemo(API_KEY)
    
    try:
        # 演示工具列表
        await demo.demo_get_available_tools()
        
        # 演示1: 智能搜索
        await demo.demo_smart_search_with_extraction()
        
        # 演示2: 政策文档爬取（适合你的使用场景）
        await demo.demo_policy_search_automation()
        
        # 演示3: 表单自动化
        await demo.demo_adaptive_form_filling()
        
        # 演示4: 复杂工作流
        await demo.demo_complex_search_workflow()
        
    except KeyboardInterrupt:
        print("\n👋 演示程序已停止")
    except Exception as e:
        print(f"\n❌ 演示程序出错: {str(e)}")
    finally:
        # 清理资源
        if demo.client:
            await demo.client.close()

if __name__ == "__main__":
    # 运行演示
    asyncio.run(main()) 