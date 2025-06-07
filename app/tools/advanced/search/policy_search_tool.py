"""
政策检索工具模块
基于层级门户检索的政策文档搜索工具，支持地方→省级→搜索引擎的智能检索策略
现已集成智能爬取调度器，可自动解析搜索结果页面内容
"""

import logging
import asyncio
import aiohttp
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field

from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.schema import Document
from app.frameworks.fastmcp.tools import register_tool
from app.tools.base.search.search_tool import get_search_tool
from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db

# 导入智能爬取调度器
from .intelligent_crawler_scheduler import (
    get_crawler_scheduler, 
    smart_crawl_url, 
    smart_crawl_urls,
    CrawlTask,
    PageComplexity
)

logger = logging.getLogger(__name__)


class SearchLevel(Enum):
    """检索层级枚举"""
    LOCAL = "local"          # 地方门户
    PROVINCIAL = "provincial"  # 省级门户
    SEARCH_ENGINE = "search_engine"  # 搜索引擎


@dataclass
class PortalConfig:
    """门户配置类"""
    name: str
    base_url: str
    search_endpoint: str
    search_params: Dict[str, str]
    result_selector: str = ""
    encoding: str = "utf-8"
    timeout: int = 30
    max_results: int = 10


class PolicySearchConfig(BaseModel):
    """政策检索配置模型"""
    region_name: str = Field(..., description="地区名称")
    local_portal: Optional[PortalConfig] = Field(None, description="地方门户配置")
    provincial_portal: Optional[PortalConfig] = Field(None, description="省级门户配置")
    search_strategy: str = Field("auto", description="检索策略：auto|local_only|provincial_only|search_only")
    quality_threshold: float = Field(0.6, description="结果质量阈值")
    max_retries: int = Field(2, description="最大重试次数")
    # 新增智能爬取配置
    enable_intelligent_crawling: bool = Field(True, description="是否启用智能爬取")
    crawl_search_results: bool = Field(True, description="是否爬取搜索结果页面")
    crawl_detail_pages: bool = Field(False, description="是否爬取详情页面")
    max_crawl_pages: int = Field(5, description="最大爬取页面数")


class PolicySearchResult(BaseModel):
    """政策检索结果模型"""
    title: str
    url: str
    content: str
    published_date: Optional[str] = None
    source: str
    search_level: SearchLevel
    relevance_score: float = 0.0
    policy_type: Optional[str] = None
    department: Optional[str] = None
    # 新增智能解析结果
    intelligent_analysis: Optional[Dict[str, Any]] = None
    content_quality_score: float = 0.0
    extraction_method: str = "traditional"  # traditional, intelligent_crawl


class PolicySearchTool(BaseTool):
    """
    政策检索工具
    支持基于层级门户的政策文档检索，从地方门户开始，逐级向上搜索
    现已集成智能爬取调度器，可自动解析搜索结果页面内容
    """
    
    def __init__(self, name: str = "policy_search"):
        """初始化政策检索工具"""
        super().__init__(name=name)
        self.description = (
            "政策检索工具：支持智能分层检索，优先使用地方政府门户网站，"
            "然后省级门户，最后使用搜索引擎。集成智能爬取调度器，"
            "可自动解析页面内容，提供更高质量的结果。"
        )
        self.search_tool = get_search_tool()
        self.session = None
        self.crawler_scheduler = None
        self.config_manager = None
        self._init_default_portals()
    
    async def _initialize_components(self):
        """初始化组件"""
        if self.crawler_scheduler is None:
            self.crawler_scheduler = get_crawler_scheduler()
            await self.crawler_scheduler.initialize()
        
        if self.config_manager is None:
            db = next(get_db())
            self.config_manager = SystemConfigManager(db)
    
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
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
        return self.session
    
    async def _search_portal(
        self, 
        portal: PortalConfig, 
        query: str, 
        search_level: SearchLevel,
        enable_intelligent_crawling: bool = True
    ) -> List[PolicySearchResult]:
        """在指定门户进行搜索"""
        try:
            session = await self._get_session()
            
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
            
            logger.info(f"搜索URL: {search_url}")
            
            # 发送搜索请求
            async with session.get(search_url) as response:
                if response.status == 200:
                    content = await response.text(encoding=portal.encoding)
                    
                    # 传统解析
                    traditional_results = await self._parse_portal_results(
                        content, portal, search_level, query
                    )
                    
                    # 如果启用智能爬取，则进行智能解析
                    if enable_intelligent_crawling and traditional_results:
                        enhanced_results = await self._enhance_results_with_intelligent_crawling(
                            traditional_results, search_url, query
                        )
                        return enhanced_results
                    
                    return traditional_results
                else:
                    logger.warning(f"门户搜索失败，状态码: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"门户搜索出错: {str(e)}")
            return []
    
    async def _enhance_results_with_intelligent_crawling(
        self,
        traditional_results: List[PolicySearchResult],
        search_url: str,
        query: str
    ) -> List[PolicySearchResult]:
        """使用智能爬取增强搜索结果"""
        try:
            await self._initialize_components()
            
            # 首先对搜索结果页面进行智能分析
            crawl_result = await smart_crawl_url(
                url=search_url,
                task_type="content_extraction",
                extraction_rules=[
                    "提取政策文档标题、链接、摘要和发布日期",
                    "识别政策类型和发布部门",
                    "提取相关度和质量评分信息"
                ],
                analysis_goals=["政策文档列表", "元数据", "相关性分析"]
            )
            
            enhanced_results = []
            
            if crawl_result.success and crawl_result.data:
                # 将智能爬取的结果与传统结果进行融合
                intelligent_data = crawl_result.data.get("data", {})
                
                for result in traditional_results:
                    enhanced_result = result.copy()
                    enhanced_result.intelligent_analysis = intelligent_data
                    enhanced_result.content_quality_score = crawl_result.content_quality_score
                    enhanced_result.extraction_method = "intelligent_crawl"
                    
                    # 尝试从智能分析中提取更准确的信息
                    if "extracted_content" in intelligent_data:
                        extracted = intelligent_data["extracted_content"]
                        if isinstance(extracted, dict):
                            # 更新政策类型
                            if "policy_type" in extracted:
                                enhanced_result.policy_type = extracted["policy_type"]
                            
                            # 更新发布部门
                            if "department" in extracted:
                                enhanced_result.department = extracted["department"]
                            
                            # 更新发布日期
                            if "published_date" in extracted:
                                enhanced_result.published_date = extracted["published_date"]
                            
                            # 提高相关性评分
                            if enhanced_result.relevance_score < 0.8:
                                enhanced_result.relevance_score = min(
                                    enhanced_result.relevance_score + 0.2,
                                    1.0
                                )
                    
                    enhanced_results.append(enhanced_result)
                
                logger.info(f"智能爬取增强了 {len(enhanced_results)} 个搜索结果")
                return enhanced_results
            else:
                logger.warning(f"智能爬取失败: {crawl_result.error}")
                # 智能爬取失败，返回传统结果
                for result in traditional_results:
                    result.extraction_method = "traditional"
                return traditional_results
                
        except Exception as e:
            logger.error(f"智能爬取增强失败: {str(e)}")
            # 出错时返回传统结果
            for result in traditional_results:
                result.extraction_method = "traditional"
            return traditional_results
    
    async def _parse_portal_results(
        self, 
        html_content: str, 
        portal: PortalConfig, 
        search_level: SearchLevel,
        query: str
    ) -> List[PolicySearchResult]:
        """解析门户搜索结果"""
        results = []
        
        try:
            # 使用正则表达式提取搜索结果
            # 这里使用通用的HTML结构解析，实际部署时可能需要针对具体网站调整
            
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
                    extraction_method="traditional"
                )
                
                results.append(result)
            
            logger.info(f"从 {portal.name} 解析到 {len(results)} 个结果")
            
        except Exception as e:
            logger.error(f"解析门户搜索结果失败: {str(e)}")
        
        return results
    
    def _calculate_relevance(self, text: str, query: str) -> float:
        """计算文本与查询的相关性"""
        try:
            text_lower = text.lower()
            query_lower = query.lower()
            
            # 简单的关键词匹配评分
            words = query_lower.split()
            matches = 0
            total_words = len(words)
            
            for word in words:
                if word in text_lower:
                    matches += 1
            
            # 基础得分
            base_score = matches / total_words if total_words > 0 else 0
            
            # 位置权重（标题中的匹配权重更高）
            if query_lower in text_lower[:100]:  # 假设前100字符是标题
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
    
    async def _search_engine_fallback(self, query: str) -> List[PolicySearchResult]:
        """搜索引擎回退策略"""
        try:
            # 使用现有的搜索工具进行搜索
            search_query = f"{query} 政策 site:gov.cn"
            search_results = await self.search_tool.search_async(search_query, max_results=10)
            
            results = []
            for result_data in search_results:
                result = self._parse_search_engine_result(result_data, query)
                if result:
                    results.append(result)
            
            logger.info(f"搜索引擎回退获得 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索引擎回退失败: {str(e)}")
            return []
    
    def _parse_search_engine_result(self, result_data: Dict, query: str) -> Optional[PolicySearchResult]:
        """解析搜索引擎结果"""
        try:
            title = result_data.get("title", "")
            url = result_data.get("url", "")
            snippet = result_data.get("snippet", "")
            
            if not title or not url:
                return None
            
            # 计算相关性
            relevance_score = self._calculate_relevance(title + " " + snippet, query)
            
            # 识别政策类型
            policy_type = self._identify_policy_type(title)
            
            return PolicySearchResult(
                title=title,
                url=url,
                content=snippet,
                source="搜索引擎",
                search_level=SearchLevel.SEARCH_ENGINE,
                relevance_score=relevance_score,
                policy_type=policy_type,
                extraction_method="traditional"
            )
            
        except Exception as e:
            logger.error(f"解析搜索引擎结果失败: {str(e)}")
            return None
    
    def _evaluate_results_quality(self, results: List[PolicySearchResult]) -> float:
        """评估结果质量"""
        if not results:
            return 0.0
        
        # 综合评估各项指标
        total_relevance = sum(r.relevance_score for r in results)
        avg_relevance = total_relevance / len(results)
        
        # 考虑智能爬取的质量提升
        intelligent_results = [r for r in results if r.extraction_method == "intelligent_crawl"]
        intelligence_bonus = len(intelligent_results) / len(results) * 0.2
        
        return min(avg_relevance + intelligence_bonus, 1.0)
    
    async def _arun(
        self, 
        query: str, 
        region: str = "六盘水", 
        search_strategy: str = "auto",
        max_results: int = 10,
        enable_intelligent_crawling: bool = True
    ) -> str:
        """异步运行政策搜索"""
        await self._initialize_components()
        
        try:
            logger.info(f"开始政策检索: query={query}, region={region}, strategy={search_strategy}")
            
            all_results = []
            search_attempted = []
            
            # 检查是否启用智能爬取
            crawling_enabled = enable_intelligent_crawling and await self.config_manager.get_config_value(
                "crawling.enabled", True
            )
            
            # 根据策略执行搜索
            if search_strategy in ["auto", "local_only"]:
                # 尝试地方门户搜索
                if region in self.default_portals:
                    portal = self.default_portals[region]
                    results = await self._search_portal(
                        portal, query, SearchLevel.LOCAL, crawling_enabled
                    )
                    all_results.extend(results)
                    search_attempted.append("地方门户")
            
            if search_strategy in ["auto", "provincial_only"]:
                # 尝试省级门户搜索
                province = region.split("市")[0] if "市" in region else region  # 简单的省份提取
                if province in self.default_portals and province != region:
                    portal = self.default_portals[province]
                    results = await self._search_portal(
                        portal, query, SearchLevel.PROVINCIAL, crawling_enabled
                    )
                    all_results.extend(results)
                    search_attempted.append("省级门户")
            
            # 评估结果质量
            quality_score = self._evaluate_results_quality(all_results)
            
            # 如果质量不够且策略允许，使用搜索引擎
            if (search_strategy in ["auto", "search_only"] and 
                (quality_score < 0.6 or len(all_results) < 3)):
                
                search_results = await self._search_engine_fallback(query)
                all_results.extend(search_results)
                search_attempted.append("搜索引擎")
            
            # 按相关性排序并限制结果数
            all_results.sort(key=lambda x: (x.relevance_score, x.content_quality_score), reverse=True)
            final_results = all_results[:max_results]
            
            # 格式化输出
            if not final_results:
                return f"抱歉，没有找到关于 '{query}' 的相关政策信息。\n搜索渠道：{', '.join(search_attempted)}"
            
            # 构建结果字符串
            result_text = f"🔍 政策检索结果（找到 {len(final_results)} 条）\n"
            result_text += f"📊 搜索渠道：{', '.join(search_attempted)}\n"
            result_text += f"⚡ 智能爬取：{'已启用' if crawling_enabled else '未启用'}\n"
            result_text += f"📈 结果质量：{quality_score:.2f}\n\n"
            
            for i, result in enumerate(final_results, 1):
                result_text += f"{i}. **{result.title}**\n"
                result_text += f"   🔗 链接：{result.url}\n"
                result_text += f"   📅 来源：{result.source} ({result.search_level.value})\n"
                
                if result.published_date:
                    result_text += f"   📆 发布日期：{result.published_date}\n"
                
                if result.policy_type:
                    result_text += f"   📋 政策类型：{result.policy_type}\n"
                
                if result.department:
                    result_text += f"   🏛️ 发布部门：{result.department}\n"
                
                result_text += f"   ⭐ 相关度：{result.relevance_score:.2f}\n"
                result_text += f"   🤖 解析方式：{result.extraction_method}\n"
                
                if result.extraction_method == "intelligent_crawl":
                    result_text += f"   🎯 内容质量：{result.content_quality_score:.2f}\n"
                
                if result.content:
                    content_preview = result.content[:200] + "..." if len(result.content) > 200 else result.content
                    result_text += f"   📄 摘要：{content_preview}\n"
                
                # 如果有智能分析结果，添加关键洞察
                if result.intelligent_analysis and isinstance(result.intelligent_analysis, dict):
                    analysis = result.intelligent_analysis
                    if "key_insights" in analysis:
                        result_text += f"   💡 智能洞察：{analysis['key_insights']}\n"
                
                result_text += "\n"
            
            # 添加智能分析摘要
            intelligent_count = len([r for r in final_results if r.extraction_method == "intelligent_crawl"])
            if intelligent_count > 0:
                result_text += f"\n🤖 智能分析摘要：\n"
                result_text += f"• 成功解析 {intelligent_count}/{len(final_results)} 个结果\n"
                avg_quality = sum(r.content_quality_score for r in final_results if r.extraction_method == "intelligent_crawl") / intelligent_count
                result_text += f"• 平均内容质量：{avg_quality:.2f}\n"
                result_text += f"• 智能爬取提升了内容准确性和结构化程度\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"政策检索失败: {str(e)}")
            return f"政策检索过程中出现错误: {str(e)}"
        
        finally:
            # 清理资源
            if self.session and not self.session.closed:
                await self.session.close()
    
    def _run(
        self, 
        query: str, 
        region: str = "六盘水", 
        search_strategy: str = "auto",
        max_results: int = 10,
        enable_intelligent_crawling: bool = True
    ) -> str:
        """同步运行政策搜索（LlamaIndex兼容）"""
        import asyncio
        return asyncio.run(self._arun(query, region, search_strategy, max_results, enable_intelligent_crawling))


@register_tool(
    name="policy_search",
    description="政策检索工具，支持智能分层检索策略和智能爬取解析，优先使用地方政府门户，然后省级门户，最后搜索引擎",
    category="search",
    tags=["政策", "搜索", "政府", "门户", "智能爬取"]
)
async def policy_search(
    query: str,
    region: str = "六盘水",
    search_strategy: str = "auto",
    max_results: int = 10,
    enable_intelligent_crawling: bool = True
) -> str:
    """
    政策检索工具函数
    
    参数:
        query: 搜索关键词
        region: 目标地区
        search_strategy: 检索策略（auto|local_only|provincial_only|search_only）
        max_results: 最大结果数
        enable_intelligent_crawling: 是否启用智能爬取
    """
    tool = PolicySearchTool()
    return await tool._arun(query, region, search_strategy, max_results, enable_intelligent_crawling)


def create_policy_search_function_tool() -> FunctionTool:
    """创建政策检索功能工具（LlamaIndex兼容）"""
    
    def sync_policy_search(
        query: str,
        region: str = "六盘水",
        search_strategy: str = "auto",
        max_results: int = 10,
        enable_intelligent_crawling: bool = True
    ) -> str:
        """同步版本的政策检索函数"""
        import asyncio
        return asyncio.run(policy_search(query, region, search_strategy, max_results, enable_intelligent_crawling))
    
    return FunctionTool.from_defaults(
        fn=sync_policy_search,
        name="policy_search",
        description=(
            "政策检索工具：智能分层搜索政府政策文档。"
            "集成智能爬取调度器，可自动解析页面内容提供高质量结果。"
            "优先从地方政府门户网站搜索，然后省级门户，最后使用搜索引擎。"
            "支持自动质量评估、策略切换和智能内容解析。"
            "适用于查找政府政策、通知、办事指南、法规等官方文档。"
        )
    )


def get_policy_search_tool() -> PolicySearchTool:
    """获取政策检索工具实例"""
    return PolicySearchTool()


# ============ 工具导出 ============

__all__ = [
    "PolicySearchTool",
    "PolicySearchConfig", 
    "PolicySearchResult",
    "SearchLevel",
    "PortalConfig",
    "policy_search",
    "create_policy_search_function_tool",
    "get_policy_search_tool"
] 