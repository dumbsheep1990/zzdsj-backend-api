"""
异步政策检索工具
支持多关键词并发检索、结果汇总和重排
集成异步执行引擎，提供高性能的政策文档搜索能力
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

from llama_index.core.tools import BaseTool, FunctionTool
from app.frameworks.fastmcp.tools import register_tool
from core.tools.async_execution_engine import (
    AsyncExecutionEngine, 
    ExecutionConfig, 
    TaskType,
    get_global_engine
)
from core.tools.search_result_aggregator import (
    SearchResult,
    SearchResultAggregator,
    create_policy_search_aggregator
)

# 导入原有的模型定义
from app.tools.advanced.search.policy_search_tool import (
    SearchLevel,
    PortalConfig,
    PolicySearchConfig,
    PolicySearchResult
)

logger = logging.getLogger(__name__)


class AsyncPolicySearchTool(BaseTool):
    """
    异步政策检索工具
    支持多关键词并发检索，集成结果汇总和重排机制
    """
    
    def __init__(self, name: str = "async_policy_search"):
        """初始化异步政策检索工具"""
        super().__init__(name=name)
        self.description = (
            "异步政策检索工具：支持多关键词并发检索，优先使用地方政府门户网站，"
            "然后省级门户，最后使用搜索引擎。集成智能结果汇总和重排机制，"
            "显著提升多关键词检索的性能和准确性。"
        )
        self.execution_engine: Optional[AsyncExecutionEngine] = None
        self.result_aggregator: Optional[SearchResultAggregator] = None
        self._init_default_portals()
        
    async def initialize(self):
        """初始化异步组件"""
        if not self.execution_engine:
            # 配置异步执行引擎
            config = ExecutionConfig(
                max_concurrent_tasks=15,        # 允许更多并发任务
                timeout_seconds=30,
                retry_attempts=2,
                enable_connection_pool=True,
                pool_size=50,
                enable_rate_limiting=True,
                rate_limit_per_second=20,       # 提高速率限制
                enable_result_dedup=True,
                enable_result_ranking=True
            )
            self.execution_engine = AsyncExecutionEngine(config)
            await self.execution_engine.initialize()
        
        if not self.result_aggregator:
            self.result_aggregator = create_policy_search_aggregator()
    
    def _init_default_portals(self):
        """初始化默认门户配置"""
        self.default_portals = {
            "六盘水": PortalConfig(
                name="六盘水市人民政府",
                base_url="https://www.gzlps.gov.cn",
                search_endpoint="/so/search.shtml",
                search_params={
                    "tenantId": "30",
                    "tenantIds": "",
                    "configTenantId": "",
                    "searchWord": "{query}"
                },
                result_selector=".search-result-item",
                max_results=10
            ),
            "贵州": PortalConfig(
                name="贵州省人民政府",
                base_url="https://www.guizhou.gov.cn",
                search_endpoint="/so/search.shtml",
                search_params={
                    "tenantId": "186",
                    "tenantIds": "",
                    "configTenantId": "",
                    "searchWord": "{query}"
                },
                result_selector=".search-result-item",
                max_results=10
            )
        }
    
    async def search_multi_keywords_concurrent(
        self,
        keywords: List[str],
        region: str = "六盘水",
        search_strategy: str = "auto",
        max_results: int = 50,
        enable_intelligent_crawling: bool = True
    ) -> List[SearchResult]:
        """
        并发搜索多个关键词
        
        Args:
            keywords: 关键词列表
            region: 目标地区
            search_strategy: 检索策略
            max_results: 最大结果数
            enable_intelligent_crawling: 是否启用智能爬取
            
        Returns:
            聚合并重排后的搜索结果
        """
        await self.initialize()
        
        try:
            logger.info(f"开始并发搜索 {len(keywords)} 个关键词: {keywords}")
            
            # 创建每个关键词的搜索任务
            search_tasks = []
            for keyword in keywords:
                task = self._create_keyword_search_task(
                    keyword=keyword,
                    region=region,
                    search_strategy=search_strategy,
                    enable_intelligent_crawling=enable_intelligent_crawling
                )
                search_tasks.append(task)
            
            # 创建结果聚合器
            aggregator = self.result_aggregator.create_keyword_specific_aggregator(keywords)
            
            # 并发执行所有搜索任务
            execution_result = await self.execution_engine.execute_concurrent_tasks(
                tasks=search_tasks,
                task_type=TaskType.IO_BOUND,
                aggregator=aggregator,
                max_results=max_results
            )
            
            # 提取聚合后的结果
            aggregated_results = execution_result.aggregated_data or []
            
            # 记录执行统计信息
            logger.info(
                f"多关键词并发搜索完成: "
                f"成功任务: {execution_result.success_count}, "
                f"失败任务: {execution_result.failure_count}, "
                f"总执行时间: {execution_result.total_execution_time:.2f}s, "
                f"最终结果数: {len(aggregated_results)}"
            )
            
            return aggregated_results[:max_results]
            
        except Exception as e:
            logger.error(f"多关键词并发搜索失败: {str(e)}")
            return []
    
    def _create_keyword_search_task(
        self,
        keyword: str,
        region: str,
        search_strategy: str,
        enable_intelligent_crawling: bool
    ) -> Callable:
        """创建单个关键词的搜索任务"""
        async def search_task() -> List[SearchResult]:
            try:
                # 执行单关键词搜索
                policy_results = await self._search_single_keyword(
                    keyword, region, search_strategy, enable_intelligent_crawling
                )
                
                # 转换为标准化搜索结果
                search_results = self._convert_to_search_results(policy_results)
                
                # 为每个结果标记关键词
                for result in search_results:
                    result.keywords_matched = [keyword]
                
                logger.info(f"关键词 '{keyword}' 搜索完成，获得 {len(search_results)} 个结果")
                return search_results
                
            except Exception as e:
                logger.error(f"关键词 '{keyword}' 搜索失败: {str(e)}")
                return []
        
        return search_task
    
    async def _search_single_keyword(
        self,
        keyword: str,
        region: str,
        search_strategy: str,
        enable_intelligent_crawling: bool
    ) -> List[PolicySearchResult]:
        """搜索单个关键词"""
        try:
            all_results = []
            
            # 根据策略执行搜索
            if search_strategy in ["auto", "local_only"]:
                # 尝试地方门户搜索
                if region in self.default_portals:
                    portal = self.default_portals[region]
                    results = await self._search_portal_async(
                        portal, keyword, SearchLevel.LOCAL, enable_intelligent_crawling
                    )
                    all_results.extend(results)
            
            if search_strategy in ["auto", "provincial_only"]:
                # 尝试省级门户搜索
                province = region.split("市")[0] if "市" in region else region
                if province in self.default_portals and province != region:
                    portal = self.default_portals[province]
                    results = await self._search_portal_async(
                        portal, keyword, SearchLevel.PROVINCIAL, enable_intelligent_crawling
                    )
                    all_results.extend(results)
            
            # 按相关性排序
            all_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return all_results
            
        except Exception as e:
            logger.error(f"单关键词搜索失败: {str(e)}")
            return []
    
    async def _search_portal_async(
        self,
        portal: PortalConfig,
        query: str,
        search_level: SearchLevel,
        enable_intelligent_crawling: bool = True
    ) -> List[PolicySearchResult]:
        """异步搜索指定门户"""
        try:
            if not self.execution_engine or not self.execution_engine.session:
                await self.initialize()
            
            session = self.execution_engine.session
            
            # 构建搜索URL
            search_params = {}
            for key, value in portal.search_params.items():
                if "{query}" in value:
                    search_params[key] = value.format(query=query)
                else:
                    search_params[key] = value
            
            search_url = urljoin(portal.base_url, portal.search_endpoint)
            if search_params:
                search_url += "?" + urlencode(search_params)
            
            logger.debug(f"搜索URL: {search_url}")
            
            # 发送异步HTTP请求
            async with session.get(search_url) as response:
                if response.status == 200:
                    content = await response.text(encoding=getattr(portal, 'encoding', 'utf-8'))
                    
                    # 解析搜索结果
                    results = await self._parse_portal_results_async(
                        content, portal, search_level, query
                    )
                    
                    return results
                else:
                    logger.warning(f"门户搜索失败，状态码: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"异步门户搜索出错: {str(e)}")
            return []
    
    async def _parse_portal_results_async(
        self,
        html_content: str,
        portal: PortalConfig,
        search_level: SearchLevel,
        query: str
    ) -> List[PolicySearchResult]:
        """异步解析门户搜索结果"""
        import re
        
        results = []
        
        try:
            # 提取标题和链接
            title_pattern = r'<h3[^>]*><a[^>]*href="([^"]*)"[^>]*>([^<]*)</a></h3>'
            matches = re.findall(title_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            # 提取摘要
            summary_pattern = r'<p[^>]*class="[^"]*summary[^"]*"[^>]*>([^<]*)</p>'
            summaries = re.findall(summary_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            # 提取日期
            date_pattern = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
            dates = re.findall(date_pattern, html_content)
            
            for i, (url, title) in enumerate(matches[:portal.max_results]):
                # 清理标题
                title = re.sub(r'<[^>]+>', '', title).strip()
                
                # 确保URL是完整的
                if not url.startswith('http'):
                    url = urljoin(portal.base_url, url)
                
                # 获取摘要
                summary = ""
                if i < len(summaries):
                    summary = re.sub(r'<[^>]+>', '', summaries[i]).strip()
                
                # 获取日期
                published_date = None
                if i < len(dates):
                    published_date = dates[i]
                
                # 计算相关性得分
                relevance_score = self._calculate_relevance(title + " " + summary, query)
                
                # 识别政策类型
                policy_type = self._identify_policy_type(title)
                
                result = PolicySearchResult(
                    title=title,
                    url=url,
                    content=summary,
                    published_date=published_date,
                    source=portal.name,
                    search_level=search_level,
                    relevance_score=relevance_score,
                    policy_type=policy_type,
                    extraction_method="async_traditional"
                )
                
                results.append(result)
            
            logger.debug(f"从 {portal.name} 异步解析到 {len(results)} 个结果")
            
        except Exception as e:
            logger.error(f"异步解析门户搜索结果失败: {str(e)}")
        
        return results
    
    def _convert_to_search_results(self, policy_results: List[PolicySearchResult]) -> List[SearchResult]:
        """将政策搜索结果转换为标准化搜索结果"""
        search_results = []
        
        for policy_result in policy_results:
            search_result = SearchResult(
                title=policy_result.title,
                url=policy_result.url,
                content=policy_result.content,
                source=policy_result.source,
                published_date=policy_result.published_date,
                relevance_score=policy_result.relevance_score,
                quality_score=getattr(policy_result, 'content_quality_score', 0.0),
                metadata={
                    "search_level": policy_result.search_level.value,
                    "policy_type": policy_result.policy_type,
                    "extraction_method": policy_result.extraction_method
                }
            )
            search_results.append(search_result)
        
        return search_results
    
    def _calculate_relevance(self, text: str, query: str) -> float:
        """计算文本与查询的相关性"""
        try:
            text_lower = text.lower()
            query_lower = query.lower()
            
            words = query_lower.split()
            matches = 0
            total_words = len(words)
            
            for word in words:
                if word in text_lower:
                    matches += 1
            
            base_score = matches / total_words if total_words > 0 else 0
            
            # 标题匹配权重更高
            if query_lower in text_lower[:100]:
                base_score += 0.2
            
            return min(base_score, 1.0)
        except:
            return 0.0
    
    def _identify_policy_type(self, title: str) -> Optional[str]:
        """根据标题识别政策类型"""
        try:
            title_lower = title.lower()
            
            policy_types = {
                "通知": ["通知", "公告", "公示"],
                "办法": ["办法", "规定", "细则"],
                "意见": ["意见", "建议", "方案"],
                "法规": ["条例", "法规", "法律"],
                "标准": ["标准", "规范", "指南"]
            }
            
            for policy_type, keywords in policy_types.items():
                for keyword in keywords:
                    if keyword in title_lower:
                        return policy_type
            
            return None
        except:
            return None
    
    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        import re
        
        # 移除标点符号并分词
        clean_query = re.sub(r'[^\w\s]', ' ', query)
        words = clean_query.split()
        
        # 过滤停用词
        stop_words = {"的", "是", "在", "有", "和", "与", "或", "但", "关于", "我"}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 如果没有提取到关键词，使用原始查询
        if not keywords:
            keywords = [query]
        
        return keywords[:5]  # 限制最多5个关键词
    
    async def _arun(
        self,
        query: str,
        region: str = "六盘水",
        search_strategy: str = "auto",
        max_results: int = 10,
        enable_intelligent_crawling: bool = True,
        enable_multi_keyword: bool = True
    ) -> str:
        """异步运行政策搜索"""
        try:
            logger.info(f"开始异步政策检索: query={query}, region={region}, strategy={search_strategy}")
            
            # 提取关键词
            keywords = self._extract_keywords_from_query(query)
            
            # 如果启用多关键词且有多个关键词，使用并发搜索
            if enable_multi_keyword and len(keywords) > 1:
                search_results = await self.search_multi_keywords_concurrent(
                    keywords=keywords,
                    region=region,
                    search_strategy=search_strategy,
                    max_results=max_results,
                    enable_intelligent_crawling=enable_intelligent_crawling
                )
            else:
                # 单关键词搜索
                main_keyword = keywords[0] if keywords else query
                policy_results = await self._search_single_keyword(
                    main_keyword, region, search_strategy, enable_intelligent_crawling
                )
                search_results = self._convert_to_search_results(policy_results)[:max_results]
            
            # 格式化输出
            if not search_results:
                return f"抱歉，没有找到关于 '{query}' 的相关政策信息。"
            
            # 构建结果字符串
            result_text = f"🔍 异步政策检索结果（找到 {len(search_results)} 条）\n"
            result_text += f"🎯 检索关键词：{', '.join(keywords)}\n"
            result_text += f"📊 搜索策略：{search_strategy}\n"
            result_text += f"⚡ 并发模式：{'已启用' if enable_multi_keyword and len(keywords) > 1 else '单关键词'}\n\n"
            
            for i, result in enumerate(search_results, 1):
                result_text += f"{i}. **{result.title}**\n"
                result_text += f"   🔗 链接：{result.url}\n"
                result_text += f"   📅 来源：{result.source}\n"
                
                if result.published_date:
                    result_text += f"   📆 发布日期：{result.published_date}\n"
                
                if result.metadata.get("policy_type"):
                    result_text += f"   📋 政策类型：{result.metadata['policy_type']}\n"
                
                result_text += f"   ⭐ 相关度：{result.relevance_score:.2f}\n"
                
                if result.keywords_matched:
                    result_text += f"   🎯 匹配关键词：{', '.join(result.keywords_matched)}\n"
                
                if result.content:
                    content_preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
                    result_text += f"   📄 摘要：{content_preview}\n"
                
                result_text += "\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"异步政策检索失败: {str(e)}")
            return f"政策检索过程中出现错误: {str(e)}"
    
    def _run(
        self,
        query: str,
        region: str = "六盘水",
        search_strategy: str = "auto",
        max_results: int = 10,
        enable_intelligent_crawling: bool = True,
        enable_multi_keyword: bool = True
    ) -> str:
        """同步运行政策搜索（LlamaIndex兼容）"""
        import asyncio
        return asyncio.run(self._arun(query, region, search_strategy, max_results, enable_intelligent_crawling, enable_multi_keyword))


@register_tool(
    name="async_policy_search",
    description="异步政策检索工具，支持多关键词并发检索和智能结果汇总重排，显著提升检索性能和准确性",
    category="search",
    tags=["政策", "搜索", "异步", "并发", "智能汇总"]
)
async def async_policy_search(
    query: str,
    region: str = "六盘水",
    search_strategy: str = "auto",
    max_results: int = 10,
    enable_intelligent_crawling: bool = True,
    enable_multi_keyword: bool = True
) -> str:
    """
    异步政策检索工具函数
    
    参数:
        query: 搜索查询
        region: 目标地区
        search_strategy: 检索策略（auto|local_only|provincial_only|search_only）
        max_results: 最大结果数
        enable_intelligent_crawling: 是否启用智能爬取
        enable_multi_keyword: 是否启用多关键词并发检索
    """
    tool = AsyncPolicySearchTool()
    return await tool._arun(query, region, search_strategy, max_results, enable_intelligent_crawling, enable_multi_keyword)


def create_async_policy_search_function_tool() -> FunctionTool:
    """创建异步政策检索功能工具（LlamaIndex兼容）"""
    
    def sync_async_policy_search(
        query: str,
        region: str = "六盘水",
        search_strategy: str = "auto",
        max_results: int = 10,
        enable_intelligent_crawling: bool = True,
        enable_multi_keyword: bool = True
    ) -> str:
        """同步版本的异步政策检索函数"""
        import asyncio
        return asyncio.run(async_policy_search(query, region, search_strategy, max_results, enable_intelligent_crawling, enable_multi_keyword))
    
    return FunctionTool.from_defaults(
        fn=sync_async_policy_search,
        name="async_policy_search",
        description=(
            "异步政策检索工具：支持多关键词并发检索和智能结果汇总重排。"
            "集成异步执行引擎，显著提升检索性能。优先从地方政府门户网站搜索，"
            "然后省级门户，最后使用搜索引擎。支持自动关键词提取、并发执行、"
            "结果去重、质量评估和智能重排。适用于复杂的政策查询和多维度检索需求。"
        )
    )


def get_async_policy_search_tool() -> AsyncPolicySearchTool:
    """获取异步政策检索工具实例"""
    return AsyncPolicySearchTool() 