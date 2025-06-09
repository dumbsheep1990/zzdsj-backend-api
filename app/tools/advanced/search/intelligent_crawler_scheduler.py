"""
智能爬取工具调度器
自动选择合适的爬取工具（Crawl4AI或Browser Use）进行页面内容解析
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
from urllib.parse import urlparse
import re

from app.frameworks.fastmcp.integrations.providers.crawl4ai_llamaindex import Crawl4AILlamaIndexClient
from app.frameworks.fastmcp.integrations.providers.browser_use_llamaindex import BrowserUseLlamaIndexClient
from app.frameworks.fastmcp.integrations.registry import ExternalMCPService
from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db

logger = logging.getLogger(__name__)


class CrawlerType(Enum):
    """爬取工具类型"""
    CRAWL4AI = "crawl4ai"
    BROWSER_USE = "browser_use"
    AUTO = "auto"


class PageComplexity(Enum):
    """页面复杂度级别"""
    SIMPLE = "simple"          # 静态页面，内容简单
    MODERATE = "moderate"      # 有一些动态内容
    COMPLEX = "complex"        # 复杂交互，大量JS
    INTERACTIVE = "interactive" # 需要表单交互


@dataclass
class CrawlTask:
    """爬取任务配置"""
    url: str
    task_type: str = "page_analysis"  # page_analysis, content_extraction, form_interaction
    complexity: PageComplexity = PageComplexity.AUTO
    priority: int = 5  # 1-10, 数字越大优先级越高
    timeout: int = 60  # 超时时间（秒）
    max_retries: int = 2
    extraction_rules: List[str] = None
    analysis_goals: List[str] = None
    output_format: str = "structured"


@dataclass
class CrawlResult:
    """爬取结果"""
    task: CrawlTask
    success: bool
    data: Dict[str, Any] = None
    error: str = None
    crawler_used: CrawlerType = None
    execution_time: float = 0.0
    content_quality_score: float = 0.0


class IntelligentCrawlerScheduler:
    """智能爬取工具调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.crawl4ai_client = None
        self.browser_use_client = None
        self.config_manager = None
        self._initialized = False
        self._model_config_cache = {}
        
    async def initialize(self):
        """初始化调度器和客户端"""
        if self._initialized:
            return
            
        try:
            # 获取系统配置管理器
            db = next(get_db())
            self.config_manager = SystemConfigManager(db)
            
            # 获取模型配置
            model_config = await self._get_model_config()
            
            # 创建Crawl4AI客户端
            crawl4ai_service = ExternalMCPService(
                id="crawl4ai_intelligence",
                name="Crawl4AI智能解析器",
                description="基于Crawl4AI的高性能智能页面解析工具",
                url="local://crawl4ai",
                provider="crawl4ai",
                capabilities=["tools", "resources"],
                extra_config=model_config
            )
            
            # 创建Browser Use客户端
            browser_use_service = ExternalMCPService(
                id="browser_use_intelligence", 
                name="Browser Use智能浏览器",
                description="基于Browser Use的智能浏览器自动化工具",
                url="local://browser-use",
                provider="browser_use",
                capabilities=["tools", "resources", "chat"],
                extra_config=model_config
            )
            
            # 获取API密钥
            api_key = await self._get_api_key(model_config.get("model", {}).get("provider", "openai"))
            
            # 初始化客户端
            self.crawl4ai_client = Crawl4AILlamaIndexClient(crawl4ai_service, api_key)
            self.browser_use_client = BrowserUseLlamaIndexClient(browser_use_service, api_key)
            
            self._initialized = True
            logger.info("智能爬取调度器初始化完成")
            
        except Exception as e:
            logger.error(f"调度器初始化失败: {str(e)}")
            raise
    
    async def _get_model_config(self) -> Dict[str, Any]:
        """从系统配置获取模型配置"""
        try:
            # 先检查缓存
            if self._model_config_cache:
                return self._model_config_cache
            
            # 获取爬取工具的模型配置
            provider = await self.config_manager.get_config_value("crawling.model.provider", "openai")
            model_name = await self.config_manager.get_config_value("crawling.model.name", "gpt-4o")
            temperature = await self.config_manager.get_config_value("crawling.model.temperature", 0.1)
            
            # 如果没有专门的爬取配置，回退到默认LLM配置
            if provider == "openai" and await self.config_manager.get_config_value("crawling.model.provider") is None:
                provider = await self.config_manager.get_config_value("llm.default_provider", "openai")
                model_name = await self.config_manager.get_config_value("llm.default_model", "gpt-4o")
                temperature = await self.config_manager.get_config_value("llm.temperature", 0.1)
            
            config = {
                "model": {
                    "provider": provider,
                    "name": model_name,
                    "temperature": float(temperature)
                }
            }
            
            # 缓存配置
            self._model_config_cache = config
            
            logger.info(f"获取到模型配置: {config}")
            return config
            
        except Exception as e:
            logger.error(f"获取模型配置失败: {str(e)}")
            # 返回默认配置
            return {
                "model": {
                    "provider": "openai",
                    "name": "gpt-4o", 
                    "temperature": 0.1
                }
            }
    
    async def _get_api_key(self, provider: str) -> str:
        """获取API密钥"""
        try:
            if provider == "openai":
                return await self.config_manager.get_config_value("llm.openai.api_key", "")
            elif provider == "anthropic":
                return await self.config_manager.get_config_value("llm.anthropic.api_key", "")
            elif provider == "ollama":
                return ""  # Ollama通常不需要API密钥
            else:
                logger.warning(f"未知的模型提供商: {provider}")
                return ""
        except Exception as e:
            logger.error(f"获取API密钥失败: {str(e)}")
            return ""
    
    async def analyze_page_complexity(self, url: str) -> PageComplexity:
        """分析页面复杂度"""
        try:
            domain = urlparse(url).netloc.lower()
            path = urlparse(url).path.lower()
            
            # 基于URL模式判断复杂度
            interactive_patterns = [
                r"login", r"register", r"form", r"submit", r"checkout",
                r"search\?", r"query="
            ]
            
            complex_patterns = [
                r"spa", r"app", r"dashboard", r"admin", r"console",
                r"\.js$", r"angular", r"react", r"vue"
            ]
            
            moderate_patterns = [
                r"news", r"blog", r"article", r"page", r"detail",
                r"list", r"category", r"tag"
            ]
            
            # 检查交互性模式
            for pattern in interactive_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return PageComplexity.INTERACTIVE
            
            # 检查复杂性模式
            for pattern in complex_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return PageComplexity.COMPLEX
            
            # 检查中等复杂度模式
            for pattern in moderate_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return PageComplexity.MODERATE
            
            # 政府网站通常结构相对简单
            gov_patterns = [r"\.gov\.", r"政府", r"政务", r"门户"]
            for pattern in gov_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return PageComplexity.SIMPLE
            
            # 默认为中等复杂度
            return PageComplexity.MODERATE
            
        except Exception as e:
            logger.error(f"分析页面复杂度失败: {str(e)}")
            return PageComplexity.MODERATE
    
    def select_crawler(self, task: CrawlTask) -> CrawlerType:
        """选择合适的爬取工具"""
        try:
            # 如果明确指定了工具类型
            if hasattr(task, 'preferred_crawler'):
                return task.preferred_crawler
            
            # 基于任务类型选择
            if task.task_type == "form_interaction":
                return CrawlerType.BROWSER_USE
            
            # 基于页面复杂度选择
            if task.complexity == PageComplexity.INTERACTIVE:
                return CrawlerType.BROWSER_USE
            elif task.complexity == PageComplexity.COMPLEX:
                return CrawlerType.BROWSER_USE
            elif task.complexity == PageComplexity.SIMPLE:
                return CrawlerType.CRAWL4AI
            else:  # MODERATE
                # 中等复杂度优先使用Crawl4AI（性能更好）
                return CrawlerType.CRAWL4AI
                
        except Exception as e:
            logger.error(f"选择爬取工具失败: {str(e)}")
            return CrawlerType.CRAWL4AI  # 默认选择
    
    async def execute_crawl_task(self, task: CrawlTask) -> CrawlResult:
        """执行爬取任务"""
        await self.initialize()
        
        start_time = asyncio.get_event_loop().time()
        crawler_type = self.select_crawler(task)
        
        try:
            # 根据工具类型执行不同的爬取策略
            if crawler_type == CrawlerType.CRAWL4AI:
                result_data = await self._execute_crawl4ai_task(task)
            else:  # BROWSER_USE
                result_data = await self._execute_browser_use_task(task)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # 评估内容质量
            quality_score = self._evaluate_content_quality(result_data)
            
            return CrawlResult(
                task=task,
                success=True,
                data=result_data,
                crawler_used=crawler_type,
                execution_time=execution_time,
                content_quality_score=quality_score
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"爬取任务执行失败: {str(e)}")
            
            return CrawlResult(
                task=task,
                success=False,
                error=str(e),
                crawler_used=crawler_type,
                execution_time=execution_time
            )
    
    async def _execute_crawl4ai_task(self, task: CrawlTask) -> Dict[str, Any]:
        """使用Crawl4AI执行爬取任务"""
        if task.task_type == "content_extraction":
            # 结构化内容挖掘
            return await self.crawl4ai_client.call_tool(
                "structural_content_mining",
                {
                    "url": task.url,
                    "target_structures": ["articles", "policies", "documents"],
                    "semantic_rules": task.extraction_rules or []
                }
            )
        elif task.task_type == "batch_analysis":
            # 批量智能爬取（如果URL是列表）
            urls = [task.url] if isinstance(task.url, str) else task.url
            return await self.crawl4ai_client.call_tool(
                "batch_intelligent_crawling",
                {
                    "urls": urls,
                    "crawl_strategy": "parallel",
                    "max_concurrent": 3,
                    "unified_analysis": True
                }
            )
        else:  # page_analysis
            # 高级页面智能分析
            return await self.crawl4ai_client.call_tool(
                "advanced_page_intelligence",
                {
                    "url": task.url,
                    "intelligence_level": "comprehensive",
                    "content_types": ["text", "links", "tables"],
                    "analysis_depth": "deep"
                }
            )
    
    async def _execute_browser_use_task(self, task: CrawlTask) -> Dict[str, Any]:
        """使用Browser Use执行爬取任务"""
        if task.task_type == "form_interaction":
            # 自适应表单交互
            return await self.browser_use_client.call_tool(
                "adaptive_form_interaction",
                {
                    "url": task.url,
                    "form_intent": "提取政策信息和相关数据",
                    "auto_submit": False,
                    "result_analysis": True
                }
            )
        elif task.task_type == "content_extraction":
            # 智能内容提取
            return await self.browser_use_client.call_tool(
                "smart_content_extraction",
                {
                    "url": task.url,
                    "extraction_rules": task.extraction_rules or ["提取政策标题、内容和相关信息"],
                    "output_format": task.output_format
                }
            )
        elif task.task_type == "multi_page":
            # 多页面智能分析
            return await self.browser_use_client.call_tool(
                "multi_page_intelligence",
                {
                    "start_url": task.url,
                    "navigation_strategy": "auto",
                    "max_pages": 5,
                    "analysis_focus": "content_similarity"
                }
            )
        else:  # page_analysis
            # 智能页面分析
            return await self.browser_use_client.call_tool(
                "intelligent_page_analysis",
                {
                    "url": task.url,
                    "analysis_goals": task.analysis_goals or ["content", "structure", "metadata"],
                    "depth_level": "deep"
                }
            )
    
    def _evaluate_content_quality(self, result_data: Dict[str, Any]) -> float:
        """评估爬取内容质量"""
        try:
            if not result_data or result_data.get("status") != "success":
                return 0.0
            
            data = result_data.get("data", {})
            
            # 基础质量指标
            quality_factors = []
            
            # 内容长度质量
            content_length = 0
            if "extracted_content" in data:
                content_length = len(str(data["extracted_content"]))
            elif "analysis_results" in data:
                content_length = len(str(data["analysis_results"]))
            elif "intelligence_analysis" in data:
                content_length = len(str(data["intelligence_analysis"]))
            
            if content_length > 1000:
                quality_factors.append(0.9)
            elif content_length > 500:
                quality_factors.append(0.7)
            elif content_length > 100:
                quality_factors.append(0.5)
            else:
                quality_factors.append(0.2)
            
            # 结构化程度
            if isinstance(data.get("extracted_content"), dict) or isinstance(data.get("analysis_results"), dict):
                quality_factors.append(0.8)
            else:
                quality_factors.append(0.5)
            
            # 错误率
            if "error" not in result_data:
                quality_factors.append(1.0)
            else:
                quality_factors.append(0.0)
            
            # 计算平均质量分数
            return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
            
        except Exception as e:
            logger.error(f"评估内容质量失败: {str(e)}")
            return 0.5
    
    async def batch_crawl(self, tasks: List[CrawlTask]) -> List[CrawlResult]:
        """批量执行爬取任务"""
        await self.initialize()
        
        # 按优先级排序任务
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        
        # 并发执行任务
        semaphore = asyncio.Semaphore(3)  # 限制并发数
        
        async def execute_with_semaphore(task):
            async with semaphore:
                return await self.execute_crawl_task(task)
        
        # 创建任务协程
        task_coroutines = [execute_with_semaphore(task) for task in sorted_tasks]
        
        # 执行并等待所有任务完成
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(CrawlResult(
                    task=sorted_tasks[i],
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def smart_retry(self, task: CrawlTask, failed_result: CrawlResult) -> CrawlResult:
        """智能重试机制"""
        try:
            # 分析失败原因并调整策略
            if "timeout" in failed_result.error.lower():
                # 超时错误，增加超时时间
                task.timeout = min(task.timeout * 2, 300)  # 最大5分钟
            
            if failed_result.crawler_used == CrawlerType.CRAWL4AI:
                # 如果Crawl4AI失败，尝试Browser Use
                task.complexity = PageComplexity.COMPLEX  # 强制使用Browser Use
            elif failed_result.crawler_used == CrawlerType.BROWSER_USE:
                # 如果Browser Use失败，尝试Crawl4AI
                task.complexity = PageComplexity.SIMPLE   # 强制使用Crawl4AI
            
            logger.info(f"重试爬取任务: {task.url}, 新策略: {self.select_crawler(task)}")
            
            # 执行重试
            return await self.execute_crawl_task(task)
            
        except Exception as e:
            logger.error(f"智能重试失败: {str(e)}")
            return CrawlResult(
                task=task,
                success=False,
                error=f"重试失败: {str(e)}"
            )


# 单例模式
_crawler_scheduler_instance = None

def get_crawler_scheduler() -> IntelligentCrawlerScheduler:
    """获取爬取调度器实例"""
    global _crawler_scheduler_instance
    if _crawler_scheduler_instance is None:
        _crawler_scheduler_instance = IntelligentCrawlerScheduler()
    return _crawler_scheduler_instance


# 便捷函数
async def smart_crawl_url(
    url: str,
    task_type: str = "page_analysis",
    extraction_rules: List[str] = None,
    analysis_goals: List[str] = None,
    timeout: int = 60
) -> CrawlResult:
    """智能爬取单个URL的便捷函数"""
    scheduler = get_crawler_scheduler()
    
    # 分析页面复杂度
    complexity = await scheduler.analyze_page_complexity(url)
    
    # 创建爬取任务
    task = CrawlTask(
        url=url,
        task_type=task_type,
        complexity=complexity,
        extraction_rules=extraction_rules,
        analysis_goals=analysis_goals,
        timeout=timeout
    )
    
    # 执行爬取
    result = await scheduler.execute_crawl_task(task)
    
    # 如果失败且有重试次数，进行智能重试
    if not result.success and task.max_retries > 0:
        task.max_retries -= 1
        result = await scheduler.smart_retry(task, result)
    
    return result


async def smart_crawl_urls(
    urls: List[str],
    task_type: str = "page_analysis",
    extraction_rules: List[str] = None,
    max_concurrent: int = 3
) -> List[CrawlResult]:
    """智能爬取多个URL的便捷函数"""
    scheduler = get_crawler_scheduler()
    
    # 创建任务列表
    tasks = []
    for url in urls:
        complexity = await scheduler.analyze_page_complexity(url)
        task = CrawlTask(
            url=url,
            task_type=task_type,
            complexity=complexity,
            extraction_rules=extraction_rules
        )
        tasks.append(task)
    
    # 批量执行
    return await scheduler.batch_crawl(tasks)