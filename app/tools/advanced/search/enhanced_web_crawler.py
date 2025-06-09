"""
增强智能网页爬虫
集成 markitdown 框架，支持自动内容清洗、格式转换和向量化处理
"""

import logging
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

import aiohttp
from bs4 import BeautifulSoup

from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db
from app.tools.advanced.content.markitdown_adapter import get_markitdown_adapter
from app.tools.advanced.search.intelligent_crawler_scheduler import IntelligentCrawlerScheduler

logger = logging.getLogger(__name__)


class EnhancedWebCrawlerConfig:
    """增强爬虫配置"""
    def __init__(self):
        # 基础爬虫配置
        self.max_concurrent_requests = 5
        self.request_timeout = 30
        self.retry_attempts = 3
        self.retry_delay = 1.0
        self.user_agent = "Enhanced-Web-Crawler/1.0"
        
        # 内容处理配置
        self.enable_markitdown = True
        self.enable_content_cleaning = True
        self.enable_smart_extraction = True
        self.extract_metadata = True
        self.generate_summaries = True
        
        # 质量控制配置
        self.min_content_length = 100
        self.max_content_length = 1000000
        self.content_quality_threshold = 0.6
        self.skip_duplicate_content = True
        
        # 存储配置
        self.save_original_html = False
        self.save_processed_markdown = True
        self.save_extracted_data = True


class ContentQualityAnalyzer:
    """内容质量分析器"""
    
    def __init__(self):
        self.quality_indicators = {
            "text_density": 0.3,      # 文本密度
            "structure_quality": 0.25, # 结构质量
            "content_relevance": 0.25, # 内容相关性
            "language_quality": 0.2    # 语言质量
        }
    
    def analyze_content_quality(self, html_content: str, markdown_content: str = "") -> Dict[str, Any]:
        """分析内容质量"""
        try:
            score = 0.0
            details = {}
            
            # 文本密度分析
            text_density_score = self._analyze_text_density(html_content)
            score += text_density_score * self.quality_indicators["text_density"]
            details["text_density"] = text_density_score
            
            # 结构质量分析
            structure_score = self._analyze_structure_quality(html_content)
            score += structure_score * self.quality_indicators["structure_quality"]
            details["structure_quality"] = structure_score
            
            # 内容相关性分析
            relevance_score = self._analyze_content_relevance(html_content, markdown_content)
            score += relevance_score * self.quality_indicators["content_relevance"]
            details["content_relevance"] = relevance_score
            
            # 语言质量分析
            language_score = self._analyze_language_quality(markdown_content or html_content)
            score += language_score * self.quality_indicators["language_quality"]
            details["language_quality"] = language_score
            
            return {
                "overall_score": min(score, 1.0),
                "details": details,
                "quality_level": self._get_quality_level(score),
                "recommendations": self._generate_recommendations(details)
            }
            
        except Exception as e:
            logger.error(f"内容质量分析失败: {str(e)}")
            return {
                "overall_score": 0.5,
                "details": {},
                "quality_level": "medium",
                "error": str(e)
            }
    
    def _analyze_text_density(self, html_content: str) -> float:
        """分析文本密度"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除script、style等非内容标签
            for tag in soup(["script", "style", "meta", "link"]):
                tag.decompose()
            
            text_content = soup.get_text()
            text_length = len(text_content.strip())
            html_length = len(html_content)
            
            if html_length == 0:
                return 0.0
            
            density = text_length / html_length
            
            # 正常的文本密度应该在0.1-0.8之间
            if 0.1 <= density <= 0.8:
                return min(density * 2, 1.0)
            else:
                return max(0.2, min(density, 0.8))
                
        except Exception as e:
            logger.error(f"文本密度分析失败: {str(e)}")
            return 0.5
    
    def _analyze_structure_quality(self, html_content: str) -> float:
        """分析HTML结构质量"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            score = 0.0
            
            # 检查标题结构
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if headings:
                score += 0.3
                
                # 检查标题层次结构
                heading_levels = [int(h.name[1]) for h in headings]
                if len(set(heading_levels)) > 1:  # 有多级标题
                    score += 0.2
            
            # 检查段落结构
            paragraphs = soup.find_all('p')
            if len(paragraphs) >= 3:
                score += 0.2
            
            # 检查列表结构
            lists = soup.find_all(['ul', 'ol'])
            if lists:
                score += 0.1
            
            # 检查表格结构
            tables = soup.find_all('table')
            if tables:
                score += 0.1
            
            # 检查语义化标签
            semantic_tags = soup.find_all(['article', 'section', 'main', 'aside', 'header', 'footer'])
            if semantic_tags:
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"结构质量分析失败: {str(e)}")
            return 0.5
    
    def _analyze_content_relevance(self, html_content: str, markdown_content: str) -> float:
        """分析内容相关性"""
        try:
            # 这里可以根据具体需求实现内容相关性分析
            # 例如：关键词密度、主题一致性等
            
            content = markdown_content or html_content
            if not content:
                return 0.0
            
            # 简单的相关性评估
            words = content.split()
            
            # 检查内容长度合理性
            if 50 <= len(words) <= 5000:
                length_score = 1.0
            elif len(words) < 50:
                length_score = len(words) / 50.0
            else:
                length_score = max(0.5, 5000 / len(words))
            
            # 检查重复内容
            unique_words = len(set(words))
            diversity_score = unique_words / max(len(words), 1)
            
            return (length_score + diversity_score) / 2
            
        except Exception as e:
            logger.error(f"内容相关性分析失败: {str(e)}")
            return 0.5
    
    def _analyze_language_quality(self, content: str) -> float:
        """分析语言质量"""
        try:
            if not content:
                return 0.0
            
            score = 0.0
            
            # 检查中文内容比例（针对中文网站）
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            total_chars = len(content)
            if total_chars > 0:
                chinese_ratio = chinese_chars / total_chars
                if chinese_ratio > 0.3:  # 主要是中文内容
                    score += 0.4
            
            # 检查句子结构
            sentences = re.split(r'[。！？.!?]', content)
            valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
            if len(valid_sentences) >= 3:
                score += 0.3
            
            # 检查段落结构
            paragraphs = content.split('\n\n')
            valid_paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 20]
            if len(valid_paragraphs) >= 2:
                score += 0.3
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"语言质量分析失败: {str(e)}")
            return 0.5
    
    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "medium"
        elif score >= 0.2:
            return "poor"
        else:
            return "very_poor"
    
    def _generate_recommendations(self, details: Dict[str, float]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if details.get("text_density", 0) < 0.3:
            recommendations.append("提高文本内容密度，减少冗余HTML标签")
        
        if details.get("structure_quality", 0) < 0.5:
            recommendations.append("改善HTML结构，使用更多语义化标签和标题层次")
        
        if details.get("content_relevance", 0) < 0.5:
            recommendations.append("提高内容相关性和多样性")
        
        if details.get("language_quality", 0) < 0.5:
            recommendations.append("改善语言表达和文本结构")
        
        return recommendations


class EnhancedWebCrawler:
    """增强智能网页爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.config = EnhancedWebCrawlerConfig()
        self.markitdown_adapter = None
        self.config_manager = None
        self.quality_analyzer = ContentQualityAnalyzer()
        self.session = None
        self._initialized = False
        
        # 缓存机制
        self.content_cache = {}
        self.url_fingerprints = set()
    
    async def initialize(self):
        """初始化爬虫组件"""
        if self._initialized:
            return
        
        try:
            # 初始化配置管理器
            try:
                db = next(get_db())
                self.config_manager = SystemConfigManager(db)
                await self._load_config()
            except Exception as e:
                logger.warning(f"配置管理器初始化失败，使用默认配置: {str(e)}")
            
            # 初始化 markitdown 适配器
            if self.config.enable_markitdown:
                self.markitdown_adapter = get_markitdown_adapter()
                await self.markitdown_adapter.initialize()
            
            # 初始化HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            connector = aiohttp.TCPConnector(limit=self.config.max_concurrent_requests)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': self.config.user_agent}
            )
            
            self._initialized = True
            logger.info("增强智能爬虫初始化完成")
            
        except Exception as e:
            logger.error(f"增强智能爬虫初始化失败: {str(e)}")
            raise
    
    async def _load_config(self):
        """从系统配置加载参数"""
        if not self.config_manager:
            return
        
        try:
            # 爬虫配置
            self.config.max_concurrent_requests = await self.config_manager.get_config_value(
                "crawler.max_concurrent_requests", 5
            )
            self.config.request_timeout = await self.config_manager.get_config_value(
                "crawler.request_timeout", 30
            )
            self.config.enable_markitdown = await self.config_manager.get_config_value(
                "crawler.enable_markitdown", True
            )
            
            logger.info("爬虫配置加载完成")
            
        except Exception as e:
            logger.error(f"爬虫配置加载失败: {str(e)}")
    
    async def crawl_url(self, url: str, **kwargs) -> Dict[str, Any]:
        """爬取单个URL"""
        try:
            await self.initialize()
            
            logger.info(f"开始爬取URL: {url}")
            
            # 检查URL是否已处理过
            url_fingerprint = hashlib.md5(url.encode()).hexdigest()
            if self.config.skip_duplicate_content and url_fingerprint in self.url_fingerprints:
                logger.info(f"URL已处理过，跳过: {url}")
                return {"url": url, "status": "skipped", "reason": "duplicate"}
            
            # 获取HTML内容
            html_result = await self._fetch_html(url)
            if not html_result["success"]:
                return {
                    "url": url,
                    "status": "failed",
                    "error": html_result["error"],
                    "timestamp": datetime.now().isoformat()
                }
            
            html_content = html_result["content"]
            
            # 质量分析
            quality_analysis = self.quality_analyzer.analyze_content_quality(html_content)
            
            # 检查质量阈值
            if quality_analysis["overall_score"] < self.config.content_quality_threshold:
                logger.warning(f"内容质量不达标: {url}, 分数: {quality_analysis['overall_score']}")
                return {
                    "url": url,
                    "status": "low_quality",
                    "quality_analysis": quality_analysis,
                    "timestamp": datetime.now().isoformat()
                }
            
            # 内容处理
            processed_content = {}
            if self.config.enable_markitdown and self.markitdown_adapter:
                processed_content = self.markitdown_adapter.convert_to_markdown(
                    html_content, "html", url
                )
            
            # 智能内容提取
            extracted_data = await self._extract_smart_content(html_content, processed_content)
            
            # 构建最终结果
            result = {
                "url": url,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "quality_analysis": quality_analysis,
                "extracted_data": extracted_data,
                "metadata": {
                    "content_length": len(html_content),
                    "processing_time": html_result.get("processing_time", 0),
                    "final_url": html_result.get("final_url", url)
                }
            }
            
            # 可选字段
            if self.config.save_original_html:
                result["original_html"] = html_content
            
            if self.config.save_processed_markdown and processed_content:
                result["markdown_content"] = processed_content.get("markdown", "")
                result["conversion_success"] = processed_content.get("conversion_success", False)
            
            # 添加到指纹集合
            self.url_fingerprints.add(url_fingerprint)
            
            logger.info(f"URL爬取完成: {url}")
            return result
            
        except Exception as e:
            logger.error(f"URL爬取失败: {url}, 错误: {str(e)}")
            return {
                "url": url,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _fetch_html(self, url: str) -> Dict[str, Any]:
        """获取HTML内容"""
        start_time = datetime.now()
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        processing_time = (datetime.now() - start_time).total_seconds()
                        
                        return {
                            "success": True,
                            "content": content,
                            "final_url": str(response.url),
                            "status_code": response.status,
                            "processing_time": processing_time
                        }
                    else:
                        logger.warning(f"HTTP错误 {response.status}: {url}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "status_code": response.status
                        }
                        
            except Exception as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}): {url}, 错误: {str(e)}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    return {
                        "success": False,
                        "error": str(e)
                    }
    
    async def _extract_smart_content(self, html_content: str, processed_content: Dict[str, Any]) -> Dict[str, Any]:
        """智能内容提取"""
        try:
            extracted = {}
            
            # 从processed_content获取基础信息
            if processed_content:
                extracted.update({
                    "title": processed_content.get("title", ""),
                    "markdown": processed_content.get("markdown", ""),
                    "metadata": processed_content.get("metadata", {}),
                    "conversion_success": processed_content.get("conversion_success", False)
                })
            
            # 使用BeautifulSoup进行额外的智能提取
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取结构化数据
            structured_data = self._extract_structured_data(soup)
            if structured_data:
                extracted["structured_data"] = structured_data
            
            # 提取关键信息
            key_info = self._extract_key_information(soup)
            if key_info:
                extracted["key_information"] = key_info
            
            # 提取链接信息
            links = self._extract_links(soup)
            if links:
                extracted["links"] = links
            
            return extracted
            
        except Exception as e:
            logger.error(f"智能内容提取失败: {str(e)}")
            return {}
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """提取结构化数据"""
        structured = {}
        
        try:
            # 提取JSON-LD数据
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            if json_ld_scripts:
                json_ld_data = []
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        json_ld_data.append(data)
                    except:
                        continue
                if json_ld_data:
                    structured["json_ld"] = json_ld_data
            
            # 提取微数据
            microdata = soup.find_all(attrs={"itemscope": True})
            if microdata:
                microdata_items = []
                for item in microdata:
                    item_data = {
                        "type": item.get("itemtype", ""),
                        "properties": {}
                    }
                    # 提取属性
                    props = item.find_all(attrs={"itemprop": True})
                    for prop in props:
                        prop_name = prop.get("itemprop")
                        prop_value = prop.get("content") or prop.get_text(strip=True)
                        item_data["properties"][prop_name] = prop_value
                    microdata_items.append(item_data)
                structured["microdata"] = microdata_items
            
            return structured
            
        except Exception as e:
            logger.error(f"结构化数据提取失败: {str(e)}")
            return {}
    
    def _extract_key_information(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """提取关键信息"""
        key_info = {}
        
        try:
            # 提取标题
            title = soup.find('title')
            if title:
                key_info["page_title"] = title.get_text(strip=True)
            
            # 提取描述
            description = soup.find('meta', attrs={'name': 'description'})
            if description:
                key_info["description"] = description.get('content', '')
            
            # 提取关键词
            keywords = soup.find('meta', attrs={'name': 'keywords'})
            if keywords:
                key_info["keywords"] = keywords.get('content', '').split(',')
            
            # 提取主要内容区域
            main_content = soup.find('main') or soup.find('article')
            if main_content:
                key_info["main_content"] = main_content.get_text(strip=True)[:1000]  # 限制长度
            
            # 提取表格数据
            tables = soup.find_all('table')
            if tables:
                table_data = []
                for table in tables[:3]:  # 最多处理3个表格
                    rows = table.find_all('tr')
                    if rows:
                        table_info = {
                            "rows": len(rows),
                            "headers": [],
                            "sample_data": []
                        }
                        
                        # 提取表头
                        header_row = rows[0]
                        headers = header_row.find_all(['th', 'td'])
                        table_info["headers"] = [h.get_text(strip=True) for h in headers]
                        
                        # 提取样例数据（前3行）
                        for row in rows[1:4]:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            table_info["sample_data"].append(row_data)
                        
                        table_data.append(table_info)
                
                key_info["tables"] = table_data
            
            return key_info
            
        except Exception as e:
            logger.error(f"关键信息提取失败: {str(e)}")
            return {}
    
    def _extract_links(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """提取链接信息"""
        try:
            links_info = {
                "internal_links": [],
                "external_links": [],
                "total_links": 0
            }
            
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href.startswith('http'):
                    links_info["external_links"].append({
                        "url": href,
                        "text": text
                    })
                elif href.startswith('/'):
                    links_info["internal_links"].append({
                        "url": href,
                        "text": text
                    })
            
            links_info["total_links"] = len(links)
            
            # 只保留前20个链接
            links_info["internal_links"] = links_info["internal_links"][:20]
            links_info["external_links"] = links_info["external_links"][:20]
            
            return links_info
            
        except Exception as e:
            logger.error(f"链接信息提取失败: {str(e)}")
            return {}
    
    async def crawl_urls_batch(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """批量爬取URL"""
        try:
            await self.initialize()
            
            logger.info(f"开始批量爬取 {len(urls)} 个URL")
            
            # 使用信号量控制并发数
            semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
            
            async def crawl_with_semaphore(url):
                async with semaphore:
                    return await self.crawl_url(url, **kwargs)
            
            # 并发执行爬取任务
            tasks = [crawl_with_semaphore(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "url": urls[i],
                        "status": "exception",
                        "error": str(result),
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    processed_results.append(result)
            
            logger.info(f"批量爬取完成，成功: {sum(1 for r in processed_results if r.get('status') == 'success')}/{len(urls)}")
            return processed_results
            
        except Exception as e:
            logger.error(f"批量爬取失败: {str(e)}")
            return []
    
    async def close(self):
        """关闭爬虫，清理资源"""
        if self.session:
            await self.session.close()
        
        self.content_cache.clear()
        self.url_fingerprints.clear()
        
        logger.info("增强智能爬虫已关闭")


# 单例模式
_enhanced_crawler_instance = None

def get_enhanced_web_crawler() -> EnhancedWebCrawler:
    """获取增强智能爬虫实例"""
    global _enhanced_crawler_instance
    if _enhanced_crawler_instance is None:
        _enhanced_crawler_instance = EnhancedWebCrawler()
    return _enhanced_crawler_instance


# 便捷函数
async def crawl_and_process_url(url: str, **kwargs) -> Dict[str, Any]:
    """爬取并处理单个URL的便捷函数"""
    crawler = get_enhanced_web_crawler()
    try:
        return await crawler.crawl_url(url, **kwargs)
    finally:
        # 注意：这里不关闭crawler，因为它是单例
        pass


async def crawl_and_process_urls(urls: List[str], **kwargs) -> List[Dict[str, Any]]:
    """批量爬取并处理URL的便捷函数"""
    crawler = get_enhanced_web_crawler()
    try:
        return await crawler.crawl_urls_batch(urls, **kwargs)
    finally:
        # 注意：这里不关闭crawler，因为它是单例
        pass 