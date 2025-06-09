"""
MarkItDown 适配器
专门用于各种文档格式到 Markdown 的转换，支持网页内容清洗和格式优化
"""

import logging
import re
import json
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MarkItDown = None
    MARKITDOWN_AVAILABLE = False

from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db

logger = logging.getLogger(__name__)


class ContentCleaningConfig:
    """内容清洗配置"""
    def __init__(self):
        # HTML清洗配置
        self.remove_navigation = True
        self.remove_footer = True
        self.remove_sidebar = True
        self.remove_ads = True
        self.remove_scripts = True
        self.remove_styles = True
        self.remove_comments = True
        
        # 文本处理配置
        self.remove_empty_paragraphs = True
        self.normalize_whitespace = True
        self.min_paragraph_length = 10
        self.max_line_length = 1000
        self.merge_consecutive_breaks = True
        
        # 链接处理配置
        self.preserve_links = True
        self.convert_relative_links = True
        self.clean_link_text = True


class MarkdownOptimizationConfig:
    """Markdown优化配置"""
    def __init__(self):
        # 格式化配置
        self.heading_style = "atx"  # atx (#) 或 setext (===)
        self.code_block_style = "fenced"  # fenced (```) 或 indented
        self.list_style = "dash"  # dash (-) 或 asterisk (*)
        self.emphasis_style = "asterisk"  # asterisk (*) 或 underscore (_)
        
        # 结构优化
        self.add_table_of_contents = False
        self.optimize_table_format = True
        self.preserve_code_blocks = True
        self.enhance_metadata = True
        
        # 输出控制
        self.include_source_info = True
        self.add_conversion_timestamp = True
        self.preserve_original_structure = True


class MarkItDownAdapter:
    """MarkItDown 适配器"""
    
    def __init__(self):
        """初始化适配器"""
        self.markitdown = None
        self.config_manager = None
        self._initialized = False
        
        # 配置实例
        self.cleaning_config = ContentCleaningConfig()
        self.optimization_config = MarkdownOptimizationConfig()
        
        # 统计信息
        self.conversion_stats = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "formats_processed": {}
        }
    
    async def initialize(self):
        """初始化适配器"""
        if self._initialized:
            return
        
        try:
            # 检查 markitdown 可用性
            if not MARKITDOWN_AVAILABLE:
                logger.warning("MarkItDown 模块未安装，请使用 pip install markitdown")
                raise ImportError("MarkItDown 模块不可用")
            
            # 初始化 MarkItDown
            self.markitdown = MarkItDown()
            
            # 初始化配置管理器
            try:
                db = next(get_db())
                self.config_manager = SystemConfigManager(db)
                await self._load_config()
            except Exception as e:
                logger.warning(f"配置管理器初始化失败，使用默认配置: {str(e)}")
            
            self._initialized = True
            logger.info("MarkItDown 适配器初始化成功")
            
        except Exception as e:
            logger.error(f"MarkItDown 适配器初始化失败: {str(e)}")
            raise
    
    async def _load_config(self):
        """从系统配置加载参数"""
        if not self.config_manager:
            return
        
        try:
            # 内容清洗配置
            self.cleaning_config.min_paragraph_length = await self.config_manager.get_config_value(
                "content.cleaning.min_paragraph_length", 10
            )
            self.cleaning_config.max_line_length = await self.config_manager.get_config_value(
                "content.cleaning.max_line_length", 1000
            )
            self.cleaning_config.remove_navigation = await self.config_manager.get_config_value(
                "content.cleaning.remove_navigation", True
            )
            self.cleaning_config.remove_ads = await self.config_manager.get_config_value(
                "content.cleaning.remove_ads", True
            )
            
            # Markdown 优化配置
            self.optimization_config.heading_style = await self.config_manager.get_config_value(
                "content.markdown.heading_style", "atx"
            )
            self.optimization_config.optimize_table_format = await self.config_manager.get_config_value(
                "content.markdown.optimize_table_format", True
            )
            
            logger.info("配置加载完成")
            
        except Exception as e:
            logger.error(f"配置加载失败: {str(e)}")
    
    def clean_html_content(self, html_content: str) -> str:
        """清洗HTML内容"""
        try:
            content = html_content
            
            # 移除导航相关元素
            if self.cleaning_config.remove_navigation:
                nav_patterns = [
                    r'<nav[^>]*>.*?</nav>',
                    r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',
                    r'<ul[^>]*class="[^"]*menu[^"]*"[^>]*>.*?</ul>',
                    r'<header[^>]*>.*?</header>',
                    r'<div[^>]*class="[^"]*header[^"]*"[^>]*>.*?</div>'
                ]
                for pattern in nav_patterns:
                    content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除页脚
            if self.cleaning_config.remove_footer:
                footer_patterns = [
                    r'<footer[^>]*>.*?</footer>',
                    r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>'
                ]
                for pattern in footer_patterns:
                    content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除侧边栏
            if self.cleaning_config.remove_sidebar:
                sidebar_patterns = [
                    r'<aside[^>]*>.*?</aside>',
                    r'<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>.*?</div>',
                    r'<div[^>]*class="[^"]*side[^"]*"[^>]*>.*?</div>'
                ]
                for pattern in sidebar_patterns:
                    content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除广告
            if self.cleaning_config.remove_ads:
                ad_patterns = [
                    r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',
                    r'<div[^>]*id="[^"]*ad[^"]*"[^>]*>.*?</div>',
                    r'<div[^>]*class="[^"]*advertisement[^"]*"[^>]*>.*?</div>',
                    r'<iframe[^>]*src="[^"]*ad[^"]*"[^>]*>.*?</iframe>'
                ]
                for pattern in ad_patterns:
                    content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除脚本
            if self.cleaning_config.remove_scripts:
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除样式
            if self.cleaning_config.remove_styles:
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除注释
            if self.cleaning_config.remove_comments:
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
            
            # 清理内联样式和事件属性
            content = re.sub(r'\s+style="[^"]*"', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s+on\w+="[^"]*"', '', content, flags=re.IGNORECASE)
            
            logger.debug("HTML内容清洗完成")
            return content
            
        except Exception as e:
            logger.error(f"HTML内容清洗失败: {str(e)}")
            return html_content
    
    def convert_to_markdown(self, content: str, content_type: str = "html", source_url: str = "") -> Dict[str, Any]:
        """将内容转换为Markdown格式"""
        try:
            if not self.markitdown:
                raise RuntimeError("MarkItDown 未初始化")
            
            self.conversion_stats["total_conversions"] += 1
            
            # 记录格式统计
            if content_type not in self.conversion_stats["formats_processed"]:
                self.conversion_stats["formats_processed"][content_type] = 0
            self.conversion_stats["formats_processed"][content_type] += 1
            
            # 预处理内容
            if content_type.lower() == "html":
                cleaned_content = self.clean_html_content(content)
                result = self.markitdown.convert(cleaned_content, file_extension=".html")
            elif content_type.lower() in ["pdf", "docx", "doc", "pptx", "xlsx"]:
                # 对于文档文件，直接传递内容
                result = self.markitdown.convert(content, file_extension=f".{content_type.lower()}")
            else:
                # 对于其他类型，尝试自动检测
                result = self.markitdown.convert(content)
            
            # 提取转换结果
            markdown_content = result.text_content if hasattr(result, 'text_content') else str(result)
            
            # 后处理Markdown内容
            optimized_markdown = self._optimize_markdown(markdown_content, source_url)
            
            # 提取元数据
            metadata = self._extract_metadata(optimized_markdown, content_type, source_url)
            
            # 生成质量评分
            quality_score = self._calculate_quality_score(optimized_markdown, content)
            
            self.conversion_stats["successful_conversions"] += 1
            
            result_data = {
                "markdown": optimized_markdown,
                "title": metadata.get("title", ""),
                "metadata": metadata,
                "quality_score": quality_score,
                "conversion_success": True,
                "content_type": content_type,
                "source_url": source_url,
                "processing_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"内容转换成功: {content_type} -> Markdown, 质量评分: {quality_score}")
            return result_data
            
        except Exception as e:
            self.conversion_stats["failed_conversions"] += 1
            logger.error(f"Markdown转换失败: {str(e)}")
            
            return {
                "markdown": content,  # 返回原始内容
                "title": "",
                "metadata": {"error": str(e)},
                "quality_score": 0.0,
                "conversion_success": False,
                "content_type": content_type,
                "source_url": source_url,
                "processing_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _optimize_markdown(self, markdown: str, source_url: str = "") -> str:
        """优化Markdown内容"""
        try:
            content = markdown
            
            # 移除空段落
            if self.cleaning_config.remove_empty_paragraphs:
                content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
            
            # 标准化空白字符
            if self.cleaning_config.normalize_whitespace:
                content = re.sub(r'[ \t]+', ' ', content)  # 多个空格/制表符合并
                content = re.sub(r'\n +', '\n', content)   # 移除行首空格
                content = re.sub(r' +\n', '\n', content)   # 移除行尾空格
            
            # 合并连续换行
            if self.cleaning_config.merge_consecutive_breaks:
                content = re.sub(r'\n{3,}', '\n\n', content)
            
            # 处理过长的行
            if self.cleaning_config.max_line_length > 0:
                content = self._split_long_lines(content)
            
            # 优化表格格式
            if self.optimization_config.optimize_table_format:
                content = self._optimize_tables(content)
            
            # 标准化标题格式
            if self.optimization_config.heading_style == "atx":
                content = self._standardize_headings(content)
            
            # 添加元信息
            if self.optimization_config.include_source_info and source_url:
                content = self._add_source_info(content, source_url)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Markdown优化失败: {str(e)}")
            return markdown
    
    def _split_long_lines(self, content: str) -> str:
        """分割过长的行"""
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            if len(line) <= self.cleaning_config.max_line_length:
                processed_lines.append(line)
                continue
            
            # 对于过长的行，尝试在合适的位置断行
            if line.startswith('#'):  # 标题行不分割
                processed_lines.append(line)
                continue
            
            # 尝试在句号、问号、感叹号后分割
            sentences = re.split(r'([.!?。！？])\s+', line)
            current_line = ""
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1] + " "
                
                if len(current_line + sentence) > self.cleaning_config.max_line_length:
                    if current_line:
                        processed_lines.append(current_line.strip())
                    current_line = sentence
                else:
                    current_line += sentence
            
            if current_line:
                processed_lines.append(current_line.strip())
        
        return '\n'.join(processed_lines)
    
    def _optimize_tables(self, content: str) -> str:
        """优化表格格式"""
        # 改进表格对齐
        table_pattern = r'(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)'
        
        def optimize_single_table(match):
            table = match.group(1)
            lines = table.strip().split('\n')
            
            if len(lines) < 2:
                return table
            
            # 计算每列的最大宽度
            all_rows = []
            for line in lines:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                all_rows.append(cells)
            
            if not all_rows:
                return table
            
            max_cols = max(len(row) for row in all_rows)
            col_widths = [0] * max_cols
            
            for row in all_rows:
                for i, cell in enumerate(row):
                    if i < max_cols:
                        col_widths[i] = max(col_widths[i], len(cell))
            
            # 重建表格
            formatted_lines = []
            for i, row in enumerate(all_rows):
                formatted_cells = []
                for j in range(max_cols):
                    cell = row[j] if j < len(row) else ""
                    if i == 1:  # 分隔行
                        formatted_cells.append('-' * max(3, col_widths[j]))
                    else:
                        formatted_cells.append(cell.ljust(col_widths[j]))
                
                formatted_lines.append('| ' + ' | '.join(formatted_cells) + ' |')
            
            return '\n'.join(formatted_lines)
        
        content = re.sub(table_pattern, optimize_single_table, content, flags=re.MULTILINE)
        return content
    
    def _standardize_headings(self, content: str) -> str:
        """标准化标题格式为ATX样式"""
        # 将setext样式标题转换为ATX样式
        content = re.sub(r'^([^\n]+)\n=+\s*$', r'# \1', content, flags=re.MULTILINE)
        content = re.sub(r'^([^\n]+)\n-+\s*$', r'## \1', content, flags=re.MULTILINE)
        
        # 标准化ATX标题格式（确保#后有空格）
        content = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', content, flags=re.MULTILINE)
        
        return content
    
    def _add_source_info(self, content: str, source_url: str) -> str:
        """添加来源信息"""
        if not source_url:
            return content
        
        source_info = f"\n\n---\n**来源**: [{source_url}]({source_url})\n"
        
        if self.optimization_config.add_conversion_timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            source_info += f"**转换时间**: {timestamp}\n"
        
        return content + source_info
    
    def _extract_metadata(self, markdown: str, content_type: str, source_url: str) -> Dict[str, Any]:
        """提取内容元数据"""
        try:
            metadata = {
                "content_type": content_type,
                "source_url": source_url,
                "extraction_timestamp": datetime.now().isoformat()
            }
            
            # 提取标题
            title_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()
            
            # 提取所有标题作为章节结构
            headings = re.findall(r'^(#{1,6})\s+(.+)$', markdown, re.MULTILINE)
            if headings:
                metadata["headings"] = [
                    {"level": len(h[0]), "text": h[1].strip()} 
                    for h in headings
                ]
                metadata["sections"] = [h[1].strip() for h in headings if len(h[0]) == 2]
            
            # 统计信息
            metadata["word_count"] = len(markdown.split())
            metadata["char_count"] = len(markdown)
            metadata["line_count"] = len(markdown.split('\n'))
            metadata["paragraph_count"] = len([p for p in markdown.split('\n\n') if p.strip()])
            
            # 提取链接
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown)
            if links:
                metadata["links"] = [
                    {"text": text.strip(), "url": url.strip()} 
                    for text, url in links
                ]
                metadata["external_links"] = [
                    link for link in metadata["links"] 
                    if link["url"].startswith(('http://', 'https://'))
                ]
            
            # 提取图片
            images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', markdown)
            if images:
                metadata["images"] = [
                    {"alt": alt.strip(), "url": url.strip()} 
                    for alt, url in images
                ]
            
            # 提取表格
            tables = re.findall(r'(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)', markdown)
            if tables:
                metadata["table_count"] = len(tables)
            
            # 提取代码块
            code_blocks = re.findall(r'```[^\n]*\n(.*?)\n```', markdown, re.DOTALL)
            if code_blocks:
                metadata["code_block_count"] = len(code_blocks)
            
            return metadata
            
        except Exception as e:
            logger.error(f"元数据提取失败: {str(e)}")
            return {
                "content_type": content_type,
                "source_url": source_url,
                "extraction_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _calculate_quality_score(self, markdown: str, original_content: str) -> float:
        """计算转换质量评分"""
        try:
            if not markdown or not original_content:
                return 0.0
            
            score = 0.0
            max_score = 100.0
            
            # 内容长度保持率 (30分)
            length_ratio = len(markdown) / max(len(original_content), 1)
            if 0.5 <= length_ratio <= 2.0:  # 合理的长度范围
                score += 30 * min(length_ratio, 1.0)
            
            # 结构完整性 (25分)
            has_headings = bool(re.search(r'^#+\s', markdown, re.MULTILINE))
            has_paragraphs = len(markdown.split('\n\n')) > 1
            has_lists = bool(re.search(r'^[-*+]\s', markdown, re.MULTILINE))
            
            structure_score = 0
            if has_headings: structure_score += 10
            if has_paragraphs: structure_score += 10
            if has_lists: structure_score += 5
            score += structure_score
            
            # 格式正确性 (20分)
            # 检查markdown语法正确性
            syntax_errors = 0
            
            # 检查标题格式
            invalid_headings = re.findall(r'^#{7,}', markdown, re.MULTILINE)
            syntax_errors += len(invalid_headings)
            
            # 检查链接格式
            invalid_links = re.findall(r'\[[^\]]*\]\([^)]*\)', markdown)
            malformed_links = [link for link in invalid_links if ']((' in link or '))]' in link]
            syntax_errors += len(malformed_links)
            
            format_score = max(0, 20 - syntax_errors * 2)
            score += format_score
            
            # 内容可读性 (15分)
            # 检查空行分布
            consecutive_empty_lines = len(re.findall(r'\n\n\n+', markdown))
            readability_score = max(0, 15 - consecutive_empty_lines)
            score += readability_score
            
            # 信息密度 (10分)
            # 计算有效内容密度
            effective_content = re.sub(r'\s+', ' ', markdown).strip()
            if len(effective_content) > 100:  # 有足够的内容
                score += 10
            elif len(effective_content) > 50:
                score += 5
            
            return min(score, max_score)
            
        except Exception as e:
            logger.error(f"质量评分计算失败: {str(e)}")
            return 50.0  # 返回默认中等分数
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """获取转换统计信息"""
        success_rate = 0.0
        if self.conversion_stats["total_conversions"] > 0:
            success_rate = (
                self.conversion_stats["successful_conversions"] / 
                self.conversion_stats["total_conversions"] * 100
            )
        
        return {
            **self.conversion_stats,
            "success_rate": success_rate,
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.conversion_stats = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "formats_processed": {}
        }
    
    async def batch_convert(
        self, 
        content_list: List[Dict[str, Any]], 
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """批量转换内容"""
        async def convert_single(item):
            content = item.get("content", "")
            content_type = item.get("type", "html")
            source_url = item.get("url", "")
            
            return self.convert_to_markdown(content, content_type, source_url)
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_convert(item):
            async with semaphore:
                return await convert_single(item)
        
        tasks = [bounded_convert(item) for item in content_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "markdown": "",
                    "title": "",
                    "metadata": {"error": str(result)},
                    "quality_score": 0.0,
                    "conversion_success": False,
                    "error": str(result),
                    "source_item": content_list[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results


# 单例模式
_markitdown_adapter_instance = None

def get_markitdown_adapter() -> MarkItDownAdapter:
    """获取 MarkItDown 适配器实例"""
    global _markitdown_adapter_instance
    if _markitdown_adapter_instance is None:
        _markitdown_adapter_instance = MarkItDownAdapter()
    return _markitdown_adapter_instance


# 便捷函数
async def convert_html_to_markdown(
    html_content: str, 
    source_url: str = "",
    clean_content: bool = True
) -> Dict[str, Any]:
    """HTML转Markdown的便捷函数"""
    adapter = get_markitdown_adapter()
    await adapter.initialize()
    
    return adapter.convert_to_markdown(html_content, "html", source_url)


async def convert_document_to_markdown(
    content: str,
    document_type: str,
    source_path: str = ""
) -> Dict[str, Any]:
    """文档转Markdown的便捷函数"""
    adapter = get_markitdown_adapter()
    await adapter.initialize()
    
    return adapter.convert_to_markdown(content, document_type, source_path) 