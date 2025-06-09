"""
智能内容分析工具
集成 markitdown 框架，提供自动内容清洗、格式转换、向量化和智能分析功能
"""

import logging
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path

from llama_index.core.schema import Document, TextNode
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.extractors import (
    TitleExtractor,
    KeywordExtractor,
    SummaryExtractor
)

from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db
from .markitdown_adapter import get_markitdown_adapter

logger = logging.getLogger(__name__)


class ContentAnalysisConfig:
    """内容分析配置"""
    def __init__(self):
        # 文本处理配置
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.min_chunk_size = 100
        self.max_chunks = 100
        
        # 提取器配置
        self.extract_title = True
        self.extract_keywords = True
        self.extract_summary = True
        self.keywords_count = 10
        
        # 分析配置
        self.analyze_readability = True
        self.analyze_structure = True
        self.analyze_sentiment = True
        self.analyze_topics = True
        
        # 输出配置
        self.include_metadata = True
        self.include_statistics = True
        self.include_embeddings = False
        self.output_format = "json"  # json, markdown, text


class TextStatistics:
    """文本统计分析器"""
    
    @staticmethod
    def calculate_statistics(text: str) -> Dict[str, Any]:
        """计算文本统计信息"""
        if not text:
            return {}
        
        stats = {}
        
        # 基础统计
        stats["character_count"] = len(text)
        stats["character_count_no_spaces"] = len(text.replace(" ", ""))
        
        # 单词统计
        words = text.split()
        stats["word_count"] = len(words)
        stats["unique_words"] = len(set(word.lower() for word in words))
        stats["avg_word_length"] = sum(len(word) for word in words) / len(words) if words else 0
        
        # 句子统计
        import re
        sentences = re.split(r'[.!?。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        stats["sentence_count"] = len(sentences)
        stats["avg_sentence_length"] = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # 段落统计
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        stats["paragraph_count"] = len(paragraphs)
        stats["avg_paragraph_length"] = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        # 可读性指标
        stats["readability_score"] = TextStatistics._calculate_readability(text, stats)
        
        # 语言检测
        stats["language_info"] = TextStatistics._detect_language(text)
        
        return stats
    
    @staticmethod
    def _calculate_readability(text: str, stats: Dict[str, Any]) -> Dict[str, float]:
        """计算可读性评分"""
        readability = {}
        
        try:
            words = stats.get("word_count", 0)
            sentences = stats.get("sentence_count", 0)
            
            if words > 0 and sentences > 0:
                # Flesch阅读容易度指数（简化版）
                avg_sentence_length = words / sentences
                # 简化的音节计算（用字符数估算）
                avg_syllables = stats.get("avg_word_length", 0) * 0.5
                
                flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
                readability["flesch_score"] = max(0, min(100, flesch_score))
                
                # 阅读等级
                if flesch_score >= 90:
                    readability["reading_level"] = "very_easy"
                elif flesch_score >= 80:
                    readability["reading_level"] = "easy"
                elif flesch_score >= 70:
                    readability["reading_level"] = "fairly_easy"
                elif flesch_score >= 60:
                    readability["reading_level"] = "standard"
                elif flesch_score >= 50:
                    readability["reading_level"] = "fairly_difficult"
                elif flesch_score >= 30:
                    readability["reading_level"] = "difficult"
                else:
                    readability["reading_level"] = "very_difficult"
            
        except Exception as e:
            logger.error(f"可读性计算失败: {str(e)}")
            readability["error"] = str(e)
        
        return readability
    
    @staticmethod
    def _detect_language(text: str) -> Dict[str, Any]:
        """检测文本语言"""
        language_info = {}
        
        try:
            # 简单的语言检测（基于字符集）
            import re
            
            # 中文字符
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            # 英文字符
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            # 数字
            digit_chars = len(re.findall(r'\d', text))
            # 标点符号
            punctuation_chars = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))
            
            total_chars = len(text)
            
            if total_chars > 0:
                language_info["chinese_ratio"] = chinese_chars / total_chars
                language_info["english_ratio"] = english_chars / total_chars
                language_info["digit_ratio"] = digit_chars / total_chars
                language_info["punctuation_ratio"] = punctuation_chars / total_chars
                
                # 主要语言判断
                if chinese_chars / total_chars > 0.3:
                    language_info["primary_language"] = "chinese"
                elif english_chars / total_chars > 0.5:
                    language_info["primary_language"] = "english"
                else:
                    language_info["primary_language"] = "mixed"
        
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            language_info["error"] = str(e)
        
        return language_info


class StructureAnalyzer:
    """内容结构分析器"""
    
    @staticmethod
    def analyze_structure(text: str, markdown_text: str = "") -> Dict[str, Any]:
        """分析文本结构"""
        structure = {}
        
        try:
            # 分析markdown结构
            if markdown_text:
                structure["markdown"] = StructureAnalyzer._analyze_markdown_structure(markdown_text)
            
            # 分析文本结构
            structure["text"] = StructureAnalyzer._analyze_text_structure(text)
            
            # 结构质量评分
            structure["quality_score"] = StructureAnalyzer._calculate_structure_quality(structure)
            
        except Exception as e:
            logger.error(f"结构分析失败: {str(e)}")
            structure["error"] = str(e)
        
        return structure
    
    @staticmethod
    def _analyze_markdown_structure(markdown_text: str) -> Dict[str, Any]:
        """分析Markdown结构"""
        import re
        
        markdown_structure = {}
        
        # 标题分析
        headings = re.findall(r'^(#{1,6})\s+(.+)$', markdown_text, re.MULTILINE)
        heading_levels = {}
        for level_marks, title in headings:
            level = len(level_marks)
            if level not in heading_levels:
                heading_levels[level] = []
            heading_levels[level].append(title.strip())
        
        markdown_structure["headings"] = heading_levels
        markdown_structure["heading_count"] = len(headings)
        
        # 列表分析
        ordered_lists = len(re.findall(r'^\d+\.\s+', markdown_text, re.MULTILINE))
        unordered_lists = len(re.findall(r'^[-*+]\s+', markdown_text, re.MULTILINE))
        markdown_structure["lists"] = {
            "ordered": ordered_lists,
            "unordered": unordered_lists,
            "total": ordered_lists + unordered_lists
        }
        
        # 链接分析
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown_text)
        markdown_structure["links"] = {
            "count": len(links),
            "links": links[:10]  # 只保留前10个
        }
        
        # 代码块分析
        code_blocks = len(re.findall(r'```[\s\S]*?```', markdown_text))
        inline_code = len(re.findall(r'`[^`]+`', markdown_text))
        markdown_structure["code"] = {
            "blocks": code_blocks,
            "inline": inline_code
        }
        
        # 表格分析
        tables = len(re.findall(r'\|.*\|', markdown_text))
        markdown_structure["tables"] = tables
        
        return markdown_structure
    
    @staticmethod
    def _analyze_text_structure(text: str) -> Dict[str, Any]:
        """分析文本结构"""
        text_structure = {}
        
        # 段落分析
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        text_structure["paragraphs"] = {
            "count": len(paragraphs),
            "avg_length": sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
            "lengths": [len(p) for p in paragraphs[:10]]  # 前10个段落的长度
        }
        
        # 句子长度分布
        import re
        sentences = re.split(r'[.!?。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            sentence_lengths = [len(s.split()) for s in sentences]
            text_structure["sentences"] = {
                "count": len(sentences),
                "avg_length": sum(sentence_lengths) / len(sentence_lengths),
                "max_length": max(sentence_lengths),
                "min_length": min(sentence_lengths)
            }
        
        return text_structure
    
    @staticmethod
    def _calculate_structure_quality(structure: Dict[str, Any]) -> Dict[str, float]:
        """计算结构质量评分"""
        quality = {"overall": 0.0}
        
        try:
            scores = []
            
            # Markdown结构评分
            if "markdown" in structure:
                md_struct = structure["markdown"]
                md_score = 0.0
                
                # 标题结构评分
                if md_struct.get("heading_count", 0) > 0:
                    md_score += 0.3
                    
                    # 标题层次评分
                    headings = md_struct.get("headings", {})
                    if len(headings) > 1:  # 有多级标题
                        md_score += 0.2
                
                # 列表评分
                if md_struct.get("lists", {}).get("total", 0) > 0:
                    md_score += 0.2
                
                # 链接评分
                if md_struct.get("links", {}).get("count", 0) > 0:
                    md_score += 0.1
                
                # 表格和代码评分
                if md_struct.get("tables", 0) > 0 or md_struct.get("code", {}).get("blocks", 0) > 0:
                    md_score += 0.2
                
                quality["markdown"] = min(md_score, 1.0)
                scores.append(quality["markdown"])
            
            # 文本结构评分
            if "text" in structure:
                text_struct = structure["text"]
                text_score = 0.0
                
                # 段落结构评分
                paragraphs = text_struct.get("paragraphs", {})
                para_count = paragraphs.get("count", 0)
                if 2 <= para_count <= 50:  # 合理的段落数量
                    text_score += 0.4
                
                avg_para_length = paragraphs.get("avg_length", 0)
                if 50 <= avg_para_length <= 500:  # 合理的段落长度
                    text_score += 0.3
                
                # 句子结构评分
                sentences = text_struct.get("sentences", {})
                avg_sent_length = sentences.get("avg_length", 0)
                if 5 <= avg_sent_length <= 30:  # 合理的句子长度
                    text_score += 0.3
                
                quality["text"] = min(text_score, 1.0)
                scores.append(quality["text"])
            
            # 总体评分
            if scores:
                quality["overall"] = sum(scores) / len(scores)
        
        except Exception as e:
            logger.error(f"结构质量评分失败: {str(e)}")
            quality["error"] = str(e)
        
        return quality


class IntelligentContentAnalyzer:
    """智能内容分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.config = ContentAnalysisConfig()
        self.markitdown_adapter = None
        self.config_manager = None
        self.text_splitter = None
        self.node_parser = None
        self.extractors = {}
        self._initialized = False
    
    async def initialize(self):
        """初始化分析器组件"""
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
            self.markitdown_adapter = get_markitdown_adapter()
            await self.markitdown_adapter.initialize()
            
            # 初始化文本处理器
            self.text_splitter = SentenceSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
            
            self.node_parser = SimpleNodeParser(
                text_splitter=self.text_splitter
            )
            
            # 初始化提取器
            await self._initialize_extractors()
            
            self._initialized = True
            logger.info("智能内容分析器初始化完成")
            
        except Exception as e:
            logger.error(f"智能内容分析器初始化失败: {str(e)}")
            raise
    
    async def _load_config(self):
        """从系统配置加载参数"""
        if not self.config_manager:
            return
        
        try:
            # 文本处理配置
            self.config.chunk_size = await self.config_manager.get_config_value(
                "content_analysis.chunk_size", 512
            )
            self.config.chunk_overlap = await self.config_manager.get_config_value(
                "content_analysis.chunk_overlap", 50
            )
            self.config.keywords_count = await self.config_manager.get_config_value(
                "content_analysis.keywords_count", 10
            )
            
            logger.info("内容分析配置加载完成")
            
        except Exception as e:
            logger.error(f"内容分析配置加载失败: {str(e)}")
    
    async def _initialize_extractors(self):
        """初始化内容提取器"""
        try:
            if self.config.extract_title:
                self.extractors['title'] = TitleExtractor()
            
            if self.config.extract_keywords:
                self.extractors['keywords'] = KeywordExtractor(keywords=self.config.keywords_count)
            
            if self.config.extract_summary:
                self.extractors['summary'] = SummaryExtractor(
                    summaries=["prev", "self", "next"]
                )
            
            logger.info(f"内容提取器初始化完成: {list(self.extractors.keys())}")
            
        except Exception as e:
            logger.error(f"内容提取器初始化失败: {str(e)}")
    
    async def analyze_content(
        self, 
        content: str, 
        content_type: str = "text",
        source_url: str = "",
        include_vectorization: bool = False
    ) -> Dict[str, Any]:
        """分析内容的完整流程"""
        try:
            await self.initialize()
            
            logger.info(f"开始智能内容分析，内容类型: {content_type}")
            
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "source_url": source_url,
                "content_type": content_type,
                "processing_stages": []
            }
            
            # 1. 内容预处理和转换
            if content_type in ["html", "xml", "docx", "pdf"]:
                logger.info("执行内容格式转换")
                conversion_result = self.markitdown_adapter.convert_to_markdown(
                    content, content_type, source_url
                )
                
                analysis_result["conversion"] = conversion_result
                analysis_result["processing_stages"].append("conversion")
                
                # 使用转换后的markdown内容
                processed_content = conversion_result.get("markdown", content)
                analysis_result["title"] = conversion_result.get("title", "")
            else:
                processed_content = content
                analysis_result["conversion"] = {"conversion_success": True}
            
            # 2. 基础统计分析
            logger.info("执行文本统计分析")
            statistics = TextStatistics.calculate_statistics(processed_content)
            analysis_result["statistics"] = statistics
            analysis_result["processing_stages"].append("statistics")
            
            # 3. 结构分析
            if self.config.analyze_structure:
                logger.info("执行结构分析")
                structure_analysis = StructureAnalyzer.analyze_structure(
                    processed_content, 
                    analysis_result.get("conversion", {}).get("markdown", "")
                )
                analysis_result["structure"] = structure_analysis
                analysis_result["processing_stages"].append("structure")
            
            # 4. 文本分割和节点生成
            if include_vectorization or any(self.extractors.values()):
                logger.info("执行文本分割")
                nodes_result = await self._process_text_nodes(processed_content)
                analysis_result["nodes"] = nodes_result
                analysis_result["processing_stages"].append("nodes")
            
            # 5. 内容提取
            if self.extractors:
                logger.info("执行内容提取")
                extraction_result = await self._extract_content_features(
                    processed_content, 
                    analysis_result.get("nodes", {}).get("nodes", [])
                )
                analysis_result["extraction"] = extraction_result
                analysis_result["processing_stages"].append("extraction")
            
            # 6. 质量评估
            logger.info("执行质量评估")
            quality_assessment = self._assess_content_quality(analysis_result)
            analysis_result["quality"] = quality_assessment
            analysis_result["processing_stages"].append("quality")
            
            # 7. 生成总结报告
            logger.info("生成分析报告")
            summary_report = self._generate_summary_report(analysis_result)
            analysis_result["summary"] = summary_report
            analysis_result["processing_stages"].append("summary")
            
            logger.info("智能内容分析完成")
            return analysis_result
            
        except Exception as e:
            logger.error(f"智能内容分析失败: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "source_url": source_url,
                "content_type": content_type,
                "error": str(e),
                "processing_stages": []
            }
    
    async def _process_text_nodes(self, text: str) -> Dict[str, Any]:
        """处理文本节点"""
        try:
            # 创建文档
            document = Document(text=text)
            
            # 文本分割
            nodes = self.node_parser.get_nodes_from_documents([document])
            
            # 过滤太短的节点
            filtered_nodes = [
                node for node in nodes 
                if len(node.text.strip()) >= self.config.min_chunk_size
            ]
            
            # 限制节点数量
            if len(filtered_nodes) > self.config.max_chunks:
                filtered_nodes = filtered_nodes[:self.config.max_chunks]
            
            return {
                "total_nodes": len(filtered_nodes),
                "nodes": [
                    {
                        "id": node.node_id,
                        "text": node.text,
                        "char_start": getattr(node, 'start_char_idx', None),
                        "char_end": getattr(node, 'end_char_idx', None),
                        "metadata": node.metadata
                    }
                    for node in filtered_nodes
                ],
                "avg_node_length": sum(len(node.text) for node in filtered_nodes) / len(filtered_nodes) if filtered_nodes else 0
            }
            
        except Exception as e:
            logger.error(f"文本节点处理失败: {str(e)}")
            return {"error": str(e), "total_nodes": 0, "nodes": []}
    
    async def _extract_content_features(self, text: str, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取内容特征"""
        extraction_result = {}
        
        try:
            # 将节点转换回TextNode对象
            text_nodes = []
            for node_data in nodes:
                node = TextNode(
                    text=node_data["text"],
                    id_=node_data["id"],
                    metadata=node_data.get("metadata", {})
                )
                text_nodes.append(node)
            
            # 应用提取器
            for extractor_name, extractor in self.extractors.items():
                try:
                    logger.debug(f"应用提取器: {extractor_name}")
                    extracted_nodes = extractor.extract(text_nodes)
                    
                    # 收集提取的信息
                    extracted_info = []
                    for node in extracted_nodes:
                        if hasattr(node, 'metadata') and node.metadata:
                            for key, value in node.metadata.items():
                                if key.startswith(extractor_name) or key in ['title', 'keywords', 'summary']:
                                    extracted_info.append({
                                        "key": key,
                                        "value": value,
                                        "node_id": node.node_id
                                    })
                    
                    extraction_result[extractor_name] = {
                        "success": True,
                        "extracted_info": extracted_info,
                        "count": len(extracted_info)
                    }
                    
                except Exception as e:
                    logger.error(f"提取器 {extractor_name} 执行失败: {str(e)}")
                    extraction_result[extractor_name] = {
                        "success": False,
                        "error": str(e)
                    }
            
        except Exception as e:
            logger.error(f"内容特征提取失败: {str(e)}")
            extraction_result["error"] = str(e)
        
        return extraction_result
    
    def _assess_content_quality(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估内容质量"""
        quality = {
            "overall_score": 0.0,
            "dimensions": {},
            "recommendations": []
        }
        
        try:
            scores = []
            
            # 统计质量评分
            stats = analysis_result.get("statistics", {})
            stats_score = self._assess_statistics_quality(stats)
            quality["dimensions"]["statistics"] = stats_score
            scores.append(stats_score)
            
            # 结构质量评分
            structure = analysis_result.get("structure", {})
            structure_score = structure.get("quality_score", {}).get("overall", 0.5)
            quality["dimensions"]["structure"] = structure_score
            scores.append(structure_score)
            
            # 转换质量评分
            conversion = analysis_result.get("conversion", {})
            conversion_score = 1.0 if conversion.get("conversion_success", False) else 0.3
            quality["dimensions"]["conversion"] = conversion_score
            scores.append(conversion_score)
            
            # 提取质量评分
            extraction = analysis_result.get("extraction", {})
            extraction_score = self._assess_extraction_quality(extraction)
            quality["dimensions"]["extraction"] = extraction_score
            scores.append(extraction_score)
            
            # 计算总体评分
            quality["overall_score"] = sum(scores) / len(scores) if scores else 0.0
            
            # 生成建议
            quality["recommendations"] = self._generate_quality_recommendations(quality["dimensions"])
            
        except Exception as e:
            logger.error(f"质量评估失败: {str(e)}")
            quality["error"] = str(e)
        
        return quality
    
    def _assess_statistics_quality(self, stats: Dict[str, Any]) -> float:
        """评估统计指标质量"""
        score = 0.0
        
        try:
            word_count = stats.get("word_count", 0)
            if 100 <= word_count <= 10000:  # 合理的词汇量
                score += 0.3
            
            unique_words = stats.get("unique_words", 0)
            if word_count > 0:
                diversity = unique_words / word_count
                if 0.3 <= diversity <= 0.8:  # 合理的词汇多样性
                    score += 0.3
            
            readability = stats.get("readability_score", {})
            flesch_score = readability.get("flesch_score", 0)
            if 30 <= flesch_score <= 80:  # 合理的可读性
                score += 0.4
            
        except Exception as e:
            logger.error(f"统计质量评估失败: {str(e)}")
        
        return min(score, 1.0)
    
    def _assess_extraction_quality(self, extraction: Dict[str, Any]) -> float:
        """评估提取质量"""
        score = 0.0
        
        try:
            successful_extractors = 0
            total_extractors = 0
            
            for extractor_name, result in extraction.items():
                if extractor_name != "error":
                    total_extractors += 1
                    if result.get("success", False):
                        successful_extractors += 1
                        
                        # 检查提取信息的数量
                        count = result.get("count", 0)
                        if count > 0:
                            score += 0.3
            
            if total_extractors > 0:
                success_rate = successful_extractors / total_extractors
                score += success_rate * 0.4
            
        except Exception as e:
            logger.error(f"提取质量评估失败: {str(e)}")
        
        return min(score, 1.0)
    
    def _generate_quality_recommendations(self, dimensions: Dict[str, float]) -> List[str]:
        """生成质量改进建议"""
        recommendations = []
        
        try:
            for dimension, score in dimensions.items():
                if score < 0.6:
                    if dimension == "statistics":
                        recommendations.append("建议优化文本长度和词汇多样性")
                    elif dimension == "structure":
                        recommendations.append("建议改善文档结构，添加标题和段落组织")
                    elif dimension == "conversion":
                        recommendations.append("建议检查原始内容格式，可能存在转换问题")
                    elif dimension == "extraction":
                        recommendations.append("建议丰富内容信息，添加关键词和摘要")
        
        except Exception as e:
            logger.error(f"建议生成失败: {str(e)}")
        
        return recommendations
    
    def _generate_summary_report(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成分析总结报告"""
        summary = {
            "processing_time": datetime.now().isoformat(),
            "success_stages": len(analysis_result.get("processing_stages", [])),
            "content_overview": {},
            "key_findings": [],
            "recommendations": []
        }
        
        try:
            stats = analysis_result.get("statistics", {})
            quality = analysis_result.get("quality", {})
            
            # 内容概览
            summary["content_overview"] = {
                "word_count": stats.get("word_count", 0),
                "character_count": stats.get("character_count", 0),
                "paragraph_count": stats.get("paragraph_count", 0),
                "language": stats.get("language_info", {}).get("primary_language", "unknown"),
                "quality_score": quality.get("overall_score", 0.0)
            }
            
            # 关键发现
            findings = []
            
            if stats.get("word_count", 0) > 1000:
                findings.append("内容篇幅较长，信息丰富")
            elif stats.get("word_count", 0) < 100:
                findings.append("内容篇幅较短，可能信息不足")
            
            readability = stats.get("readability_score", {})
            reading_level = readability.get("reading_level", "")
            if reading_level:
                findings.append(f"可读性等级: {reading_level}")
            
            structure = analysis_result.get("structure", {})
            if structure.get("markdown", {}).get("heading_count", 0) > 0:
                findings.append("文档具有良好的标题结构")
            
            summary["key_findings"] = findings
            
            # 综合建议
            recommendations = quality.get("recommendations", [])
            if quality.get("overall_score", 0) >= 0.8:
                recommendations.append("内容质量优秀，建议保持当前标准")
            elif quality.get("overall_score", 0) >= 0.6:
                recommendations.append("内容质量良好，可进一步优化")
            else:
                recommendations.append("内容质量需要改进，建议重新组织")
            
            summary["recommendations"] = recommendations
            
        except Exception as e:
            logger.error(f"总结报告生成失败: {str(e)}")
            summary["error"] = str(e)
        
        return summary


# 单例模式
_content_analyzer_instance = None

def get_intelligent_content_analyzer() -> IntelligentContentAnalyzer:
    """获取智能内容分析器实例"""
    global _content_analyzer_instance
    if _content_analyzer_instance is None:
        _content_analyzer_instance = IntelligentContentAnalyzer()
    return _content_analyzer_instance


# 便捷函数
async def analyze_text_content(
    content: str, 
    content_type: str = "text",
    source_url: str = "",
    include_vectorization: bool = False
) -> Dict[str, Any]:
    """分析文本内容的便捷函数"""
    analyzer = get_intelligent_content_analyzer()
    return await analyzer.analyze_content(
        content, content_type, source_url, include_vectorization
    )


async def analyze_html_content(
    html_content: str,
    source_url: str = "",
    include_vectorization: bool = False
) -> Dict[str, Any]:
    """分析HTML内容的便捷函数"""
    analyzer = get_intelligent_content_analyzer()
    return await analyzer.analyze_content(
        html_content, "html", source_url, include_vectorization
    ) 