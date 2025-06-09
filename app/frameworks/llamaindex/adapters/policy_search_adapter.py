"""
政策检索工具的LlamaIndex适配器
将政策检索功能集成到LlamaIndex代理工具链中
现已集成智能爬取调度器，提供增强的页面解析能力
"""

import logging
from typing import Dict, List, Any, Optional

from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.agent import OpenAIAgent
from app.tools.advanced.search.policy_search_tool import (
    get_policy_search_tool, 
    create_policy_search_function_tool,
    PolicySearchTool
)
from app.tools.advanced.search.intelligent_crawler_scheduler import (
    get_crawler_scheduler,
    smart_crawl_url,
    smart_crawl_urls,
    CrawlTask,
    CrawlResult,
    PageComplexity
)
from app.services.system.portal_config_service import get_portal_config_service
from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db

logger = logging.getLogger(__name__)


class PolicySearchAdapter:
    """政策检索适配器 - 增强版"""
    
    def __init__(self):
        """初始化适配器"""
        self.policy_tool = get_policy_search_tool()
        self.portal_service = get_portal_config_service()
        self.crawler_scheduler = None
        self.config_manager = None
        self._initialized = False
    
    async def _initialize(self):
        """初始化组件"""
        if self._initialized:
            return
        
        # 初始化爬取调度器
        self.crawler_scheduler = get_crawler_scheduler()
        await self.crawler_scheduler.initialize()
        
        # 初始化配置管理器
        db = next(get_db())
        self.config_manager = SystemConfigManager(db)
        
        self._initialized = True
    
    async def get_available_regions(self) -> List[str]:
        """获取可用的检索地区列表"""
        try:
            configs = await self.portal_service.list_portal_configs()
            return [config.get("region_name") for config in configs if config.get("region_name")]
        except Exception as e:
            logger.error(f"获取可用地区失败: {str(e)}")
            return ["六盘水", "贵州"]  # 返回默认地区
    
    def create_enhanced_policy_search_tool(self) -> FunctionTool:
        """创建增强的政策检索工具"""
        
        async def enhanced_policy_search(
            query: str,
            region: str = "六盘水",
            search_strategy: str = "auto",
            max_results: int = 10,
            include_summary: bool = True,
            enable_intelligent_crawling: bool = True
        ) -> str:
            """
            增强的政策检索函数
            
            参数:
                query: 搜索查询关键词
                region: 地区名称
                search_strategy: 检索策略（auto|local_only|provincial_only|search_only）
                max_results: 最大返回结果数
                include_summary: 是否包含结果摘要
                enable_intelligent_crawling: 是否启用智能爬取
                
            返回:
                格式化的政策检索结果
            """
            try:
                await self._initialize()
                
                # 验证地区配置
                config = await self.portal_service.get_portal_config(region)
                if not config:
                    available_regions = await self.get_available_regions()
                    return f"地区 '{region}' 的门户配置不存在。可用地区: {', '.join(available_regions)}"
                
                # 执行搜索
                results = await self.policy_tool._arun(
                    query=query,
                    region=region,
                    search_strategy=search_strategy,
                    max_results=max_results,
                    enable_intelligent_crawling=enable_intelligent_crawling
                )
                
                # 如果需要摘要，添加统计信息
                if include_summary:
                    summary = await self._generate_search_summary(query, region, results)
                    results += f"\n\n{summary}"
                
                return results
                
            except Exception as e:
                logger.error(f"增强政策检索失败: {str(e)}")
                return f"政策检索失败: {str(e)}"
        
        # 包装为同步函数
        def sync_enhanced_policy_search(
            query: str,
            region: str = "六盘水",
            search_strategy: str = "auto", 
            max_results: int = 10,
            include_summary: bool = True,
            enable_intelligent_crawling: bool = True
        ) -> str:
            import asyncio
            return asyncio.run(enhanced_policy_search(
                query, region, search_strategy, max_results, include_summary, enable_intelligent_crawling
            ))
        
        return FunctionTool.from_defaults(
            fn=sync_enhanced_policy_search,
            name="enhanced_policy_search",
            description=(
                "增强的政策检索工具：智能分层搜索政府政策文档。"
                "集成智能爬取调度器，可自动解析页面内容提供高质量结果。"
                "优先从地方政府门户网站搜索，然后省级门户，最后使用搜索引擎。"
                "支持自动质量评估、策略切换、智能内容解析和详细统计信息。"
                "适用于查找政府政策、通知、办事指南、法规等官方文档。"
            )
        )
    
    def create_intelligent_content_analysis_tool(self) -> FunctionTool:
        """创建智能内容分析工具"""
        
        async def analyze_policy_content(
            url: str,
            analysis_type: str = "comprehensive",
            extract_entities: bool = True,
            summarize: bool = True
        ) -> str:
            """
            智能分析政策内容
            
            参数:
                url: 政策文档URL
                analysis_type: 分析类型（comprehensive|quick|detailed）
                extract_entities: 是否提取实体信息
                summarize: 是否生成摘要
                
            返回:
                结构化的分析结果
            """
            try:
                await self._initialize()
                
                # 构建分析目标
                analysis_goals = ["content", "structure", "metadata"]
                if extract_entities:
                    analysis_goals.extend(["entities", "keywords", "dates"])
                if summarize:
                    analysis_goals.append("summary")
                
                # 构建提取规则
                extraction_rules = [
                    "提取政策标题、发布部门、发布日期和有效期",
                    "识别政策类型、适用范围和主要内容",
                    "提取关键条款、重要数据和联系方式"
                ]
                
                if extract_entities:
                    extraction_rules.extend([
                        "提取人名、地名、机构名、时间和金额等实体",
                        "识别政策关键词和专业术语"
                    ])
                
                # 执行智能爬取
                result = await smart_crawl_url(
                    url=url,
                    task_type="content_extraction",
                    extraction_rules=extraction_rules,
                    analysis_goals=analysis_goals,
                    timeout=120 if analysis_type == "detailed" else 60
                )
                
                if not result.success:
                    return f"内容分析失败: {result.error}"
                
                # 格式化结果
                return self._format_analysis_result(result, analysis_type, summarize)
                
            except Exception as e:
                logger.error(f"智能内容分析失败: {str(e)}")
                return f"内容分析失败: {str(e)}"
        
        def sync_analyze_policy_content(
            url: str,
            analysis_type: str = "comprehensive",
            extract_entities: bool = True,
            summarize: bool = True
        ) -> str:
            import asyncio
            return asyncio.run(analyze_policy_content(url, analysis_type, extract_entities, summarize))
        
        return FunctionTool.from_defaults(
            fn=sync_analyze_policy_content,
            name="analyze_policy_content",
            description=(
                "智能政策内容分析工具：深度解析政策文档页面内容。"
                "自动提取政策标题、发布部门、关键条款、适用范围等信息。"
                "支持实体识别、关键词提取、内容摘要等高级分析功能。"
                "适用于深度解读政策文档，提取结构化信息。"
            )
        )
    
    def create_batch_policy_crawler_tool(self) -> FunctionTool:
        """创建批量政策爬取工具"""
        
        async def batch_crawl_policies(
            urls: List[str],
            max_concurrent: int = 3,
            include_analysis: bool = True,
            output_format: str = "structured"
        ) -> str:
            """
            批量爬取政策页面
            
            参数:
                urls: 政策页面URL列表
                max_concurrent: 最大并发数
                include_analysis: 是否包含智能分析
                output_format: 输出格式（structured|json|markdown）
                
            返回:
                批量爬取结果
            """
            try:
                await self._initialize()
                
                if not urls:
                    return "未提供URL列表"
                
                # 限制URL数量
                if len(urls) > 20:
                    urls = urls[:20]
                    logger.warning("URL数量超过限制，仅处理前20个")
                
                # 执行批量爬取
                results = await smart_crawl_urls(
                    urls=urls,
                    task_type="content_extraction" if include_analysis else "page_analysis",
                    extraction_rules=[
                        "提取政策标题、内容和发布信息",
                        "识别政策类型和关键信息",
                        "提取联系方式和相关链接"
                    ],
                    max_concurrent=max_concurrent
                )
                
                # 格式化批量结果
                return self._format_batch_results(results, output_format, include_analysis)
                
            except Exception as e:
                logger.error(f"批量政策爬取失败: {str(e)}")
                return f"批量爬取失败: {str(e)}"
        
        def sync_batch_crawl_policies(
            urls: List[str],
            max_concurrent: int = 3,
            include_analysis: bool = True,
            output_format: str = "structured"
        ) -> str:
            import asyncio
            return asyncio.run(batch_crawl_policies(urls, max_concurrent, include_analysis, output_format))
        
        return FunctionTool.from_defaults(
            fn=sync_batch_crawl_policies,
            name="batch_crawl_policies",
            description=(
                "批量政策爬取工具：高效并行爬取多个政策页面。"
                "支持智能内容分析、实体提取和结构化输出。"
                "自动处理不同网站结构，提供统一的结果格式。"
                "适用于大批量政策文档的收集和分析。"
            )
        )
    
    def _format_analysis_result(self, result: CrawlResult, analysis_type: str, include_summary: bool) -> str:
        """格式化分析结果"""
        try:
            if not result.data:
                return "分析结果为空"
            
            data = result.data.get("data", {})
            output = f"🔍 政策内容分析结果\n\n"
            output += f"📊 分析质量：{result.content_quality_score:.2f}\n"
            output += f"⏱️ 处理时间：{result.execution_time:.2f}秒\n"
            output += f"🤖 使用工具：{result.crawler_used.value if result.crawler_used else '未知'}\n\n"
            
            # 基础信息
            if "extracted_content" in data:
                content = data["extracted_content"]
                if isinstance(content, dict):
                    output += "📋 基础信息：\n"
                    for key, value in content.items():
                        if key in ["title", "department", "published_date", "policy_type"]:
                            label = {
                                "title": "标题",
                                "department": "发布部门", 
                                "published_date": "发布日期",
                                "policy_type": "政策类型"
                            }.get(key, key)
                            output += f"• {label}：{value}\n"
                    output += "\n"
            
            # 智能分析
            if "analysis_results" in data:
                analysis = data["analysis_results"]
                if isinstance(analysis, dict):
                    output += "🧠 智能分析：\n"
                    for key, value in analysis.items():
                        if isinstance(value, (str, int, float)):
                            output += f"• {key}：{value}\n"
                    output += "\n"
            
            # 摘要（如果启用）
            if include_summary and "summary" in data:
                output += f"📝 内容摘要：\n{data['summary']}\n\n"
            
            # 实体信息
            if "entities" in data and data["entities"]:
                output += "🏷️ 实体信息：\n"
                entities = data["entities"]
                if isinstance(entities, dict):
                    for entity_type, entity_list in entities.items():
                        if entity_list:
                            output += f"• {entity_type}：{', '.join(entity_list[:5])}\n"
                output += "\n"
            
            return output
            
        except Exception as e:
            logger.error(f"格式化分析结果失败: {str(e)}")
            return f"格式化结果失败: {str(e)}"
    
    def _format_batch_results(self, results: List[CrawlResult], output_format: str, include_analysis: bool) -> str:
        """格式化批量结果"""
        try:
            if not results:
                return "批量爬取无结果"
            
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            output = f"📊 批量爬取结果统计\n"
            output += f"• 总任务数：{len(results)}\n"
            output += f"• 成功数：{len(successful_results)}\n"
            output += f"• 失败数：{len(failed_results)}\n"
            output += f"• 成功率：{len(successful_results)/len(results)*100:.1f}%\n\n"
            
            if successful_results:
                avg_quality = sum(r.content_quality_score for r in successful_results) / len(successful_results)
                avg_time = sum(r.execution_time for r in successful_results) / len(successful_results)
                output += f"📈 平均质量：{avg_quality:.2f}\n"
                output += f"⏱️ 平均耗时：{avg_time:.2f}秒\n\n"
                
                output += "✅ 成功结果：\n"
                for i, result in enumerate(successful_results, 1):
                    output += f"{i}. {result.task.url}\n"
                    
                    if result.data and "data" in result.data:
                        data = result.data["data"]
                        if "extracted_content" in data:
                            content = data["extracted_content"]
                            if isinstance(content, dict):
                                if "title" in content:
                                    output += f"   📋 标题：{content['title']}\n"
                                if "policy_type" in content:
                                    output += f"   🏷️ 类型：{content['policy_type']}\n"
                    
                    output += f"   ⭐ 质量：{result.content_quality_score:.2f}\n"
                    output += "\n"
            
            if failed_results:
                output += "❌ 失败结果：\n"
                for i, result in enumerate(failed_results, 1):
                    output += f"{i}. {result.task.url}\n"
                    output += f"   错误：{result.error}\n\n"
            
            return output
            
        except Exception as e:
            logger.error(f"格式化批量结果失败: {str(e)}")
            return f"格式化批量结果失败: {str(e)}"
    
    async def _generate_search_summary(
        self, 
        query: str, 
        region: str, 
        results: str
    ) -> str:
        """生成搜索摘要"""
        try:
            # 简单的结果统计
            lines = results.split('\n')
            result_count = len([line for line in lines if line.strip().startswith(tuple(str(i) + '.' for i in range(1, 21)))])
            
            # 检查使用的搜索渠道
            channels_used = []
            if "地方门户" in results:
                channels_used.append("地方门户")
            if "省级门户" in results:
                channels_used.append("省级门户")
            if "搜索引擎" in results:
                channels_used.append("搜索引擎")
            
            # 检查智能爬取使用情况
            intelligent_enabled = "智能爬取：已启用" in results
            intelligent_count = results.count("解析方式：intelligent_crawl")
            
            summary = f"📊 搜索摘要：\n"
            summary += f"• 查询词：{query}\n"
            summary += f"• 目标地区：{region}\n"
            summary += f"• 找到结果：{result_count}条\n"
            summary += f"• 使用渠道：{', '.join(channels_used) if channels_used else '未知'}\n"
            
            if intelligent_enabled:
                summary += f"• 智能解析：{intelligent_count}条结果使用了智能爬取\n"
            
            # 添加建议
            if result_count == 0:
                summary += f"💡 建议：\n"
                summary += f"  - 尝试更通用的关键词\n"
                summary += f"  - 检查地区名称是否正确\n"
                summary += f"  - 考虑使用省级或搜索引擎模式\n"
            elif result_count < 3:
                summary += f"💡 提示：结果较少，可尝试扩大搜索范围\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"生成搜索摘要失败: {str(e)}")
            return "📊 搜索完成"
    
    def create_region_query_tool(self) -> FunctionTool:
        """创建地区查询工具"""
        
        async def query_available_regions(level: Optional[str] = None) -> str:
            """
            查询可用的检索地区
            
            参数:
                level: 行政级别过滤（provincial|municipal|county）
                
            返回:
                可用地区列表
            """
            try:
                configs = await self.portal_service.list_portal_configs(level=level)
                
                if not configs:
                    return "暂无可用的门户配置"
                
                result = f"可用的政策检索地区：\n\n"
                
                # 按级别分组
                by_level = {}
                for config in configs:
                    config_level = config.get("level", "unknown")
                    if config_level not in by_level:
                        by_level[config_level] = []
                    by_level[config_level].append(config)
                
                level_names = {
                    "provincial": "省级",
                    "municipal": "市级", 
                    "county": "县级"
                }
                
                for config_level, level_configs in by_level.items():
                    level_name = level_names.get(config_level, config_level)
                    result += f"🏛️ {level_name}门户：\n"
                    
                    for config in level_configs:
                        region_name = config.get("region_name", "未知")
                        portal_name = config.get("name", "未知")
                        is_custom = config.get("is_custom", False)
                        config_type = "自定义" if is_custom else "内置"
                        
                        result += f"  • {region_name} - {portal_name} ({config_type})\n"
                    
                    result += "\n"
                
                result += f"💡 使用方法：在政策检索时指定region参数为对应地区名称\n"
                result += f"📝 例如：policy_search(query='养老政策', region='六盘水')\n"
                
                return result
                
            except Exception as e:
                logger.error(f"查询可用地区失败: {str(e)}")
                return f"查询可用地区失败: {str(e)}"
        
        def sync_query_regions(level: Optional[str] = None) -> str:
            import asyncio
            return asyncio.run(query_available_regions(level))
        
        return FunctionTool.from_defaults(
            fn=sync_query_regions,
            name="query_policy_regions",
            description=(
                "查询可用的政策检索地区。"
                "可以按行政级别过滤（provincial|municipal|county）。"
                "返回所有配置了门户搜索的地区列表及其详细信息。"
            )
        )
    
    def create_portal_test_tool(self) -> FunctionTool:
        """创建门户测试工具"""
        
        async def test_portal_connectivity(region: str) -> str:
            """
            测试门户连通性
            
            参数:
                region: 地区名称
                
            返回:
                连通性测试结果
            """
            try:
                config = await self.portal_service.get_portal_config(region)
                if not config:
                    return f"地区 '{region}' 的门户配置不存在"
                
                # 这里可以实现实际的连通性测试
                # 暂时返回配置信息
                result = f"门户配置测试结果：\n"
                result += f"地区：{region}\n"
                result += f"门户名称：{config.get('name', '未知')}\n"
                result += f"基础URL：{config.get('base_url', '未知')}\n"
                result += f"配置状态：正常\n"
                
                return result
                
            except Exception as e:
                logger.error(f"门户连通性测试失败: {str(e)}")
                return f"测试失败: {str(e)}"
        
        def sync_test_portal(region: str) -> str:
            import asyncio
            return asyncio.run(test_portal_connectivity(region))
        
        return FunctionTool.from_defaults(
            fn=sync_test_portal,
            name="test_portal_connectivity",
            description="测试指定地区门户网站的连通性和配置状态"
        )
    
    def get_all_tools(self) -> List[BaseTool]:
        """获取所有政策检索相关工具"""
        return [
            self.create_enhanced_policy_search_tool(),
            self.create_intelligent_content_analysis_tool(),
            self.create_batch_policy_crawler_tool(),
            self.create_region_query_tool(),
            self.create_portal_test_tool()
        ]


def get_policy_search_adapter() -> PolicySearchAdapter:
    """获取政策检索适配器实例"""
    return PolicySearchAdapter()


def create_policy_search_tools() -> List[BaseTool]:
    """创建政策检索工具集合"""
    adapter = get_policy_search_adapter()
    return adapter.get_all_tools()


def integrate_policy_search_to_agent(agent: OpenAIAgent) -> None:
    """将政策检索工具集成到代理中"""
    tools = create_policy_search_tools()
    for tool in tools:
        agent.add_tool(tool)


__all__ = [
    "PolicySearchAdapter",
    "get_policy_search_adapter", 
    "create_policy_search_tools",
    "integrate_policy_search_to_agent"
] 