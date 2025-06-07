"""
网页内容处理器
集成markitdown框架进行内容清洗、格式转换和向量化处理
"""

import logging
import re
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

from llama_index.core.schema import Document, TextNode
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.extractors import (
    TitleExtractor,
    KeywordExtractor, 
    SummaryExtractor
)
from llama_index.embeddings.openai import OpenAIEmbedding

from core.system_config.config_manager import SystemConfigManager
from app.models.database import get_db
from app.utils.storage.core.manager import StorageManager
from .markitdown_adapter import get_markitdown_adapter, MarkItDownAdapter

logger = logging.getLogger(__name__)


class VectorizationConfig:
    """向量化配置"""
    def __init__(self):
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.extract_keywords = True
        self.extract_summary = True
        self.extract_title = True
        self.embedding_model = "text-embedding-3-large"


class ContentProcessor:
    """网页内容处理器"""
    
    def __init__(self):
        """初始化内容处理器"""
        self.markitdown_adapter = None
        self.config_manager = None
        self.storage_manager = None
        self.embedding_model = None
        self.text_splitter = None
        self.extractors = {}
        self._initialized = False
        
        # 向量化配置
        self.vectorization_config = VectorizationConfig()
    
    async def initialize(self):
        """初始化处理器组件"""
        if self._initialized:
            return
        
        try:
            # 初始化 MarkItDown 适配器
            self.markitdown_adapter = get_markitdown_adapter()
            await self.markitdown_adapter.initialize()
            
            # 初始化配置管理器
            try:
                db = next(get_db())
                self.config_manager = SystemConfigManager(db)
                await self._load_config()
            except Exception as e:
                logger.warning(f"配置管理器初始化失败，使用默认配置: {str(e)}")
            
            # 初始化存储管理器
            try:
                self.storage_manager = StorageManager()
            except Exception as e:
                logger.warning(f"存储管理器初始化失败: {str(e)}")
            
            # 初始化嵌入模型
            await self._initialize_embedding()
            
            # 初始化文本分割器
            self._initialize_text_splitter()
            
            # 初始化内容提取器
            await self._initialize_extractors()
            
            self._initialized = True
            logger.info("内容处理器初始化完成")
            
        except Exception as e:
            logger.error(f"内容处理器初始化失败: {str(e)}")
            raise
    
    async def _load_config(self):
        """从系统配置加载参数"""
        if not self.config_manager:
            return
        
        try:
            # 向量化配置
            self.vectorization_config.chunk_size = await self.config_manager.get_config_value(
                "content.vectorization.chunk_size", 512
            )
            self.vectorization_config.chunk_overlap = await self.config_manager.get_config_value(
                "content.vectorization.chunk_overlap", 50
            )
            self.vectorization_config.embedding_model = await self.config_manager.get_config_value(
                "content.vectorization.embedding_model", "text-embedding-3-large"
            )
            
            logger.info("配置加载完成")
            
        except Exception as e:
            logger.error(f"配置加载失败: {str(e)}")
    
    async def _initialize_embedding(self):
        """初始化嵌入模型"""
        try:
            if not self.config_manager:
                logger.warning("配置管理器未初始化，跳过嵌入模型初始化")
                return
                
            api_key = await self.config_manager.get_config_value("llm.openai.api_key", "")
            if api_key:
                self.embedding_model = OpenAIEmbedding(
                    model=self.vectorization_config.embedding_model,
                    api_key=api_key
                )
                logger.info(f"嵌入模型初始化成功: {self.vectorization_config.embedding_model}")
            else:
                logger.warning("OpenAI API密钥未配置，嵌入功能将不可用")
                
        except Exception as e:
            logger.error(f"嵌入模型初始化失败: {str(e)}")
    
    def _initialize_text_splitter(self):
        """初始化文本分割器"""
        self.text_splitter = SentenceSplitter(
            chunk_size=self.vectorization_config.chunk_size,
            chunk_overlap=self.vectorization_config.chunk_overlap
        )
        logger.info("文本分割器初始化完成")
    
    async def _initialize_extractors(self):
        """初始化内容提取器"""
        try:
            if self.vectorization_config.extract_title:
                self.extractors['title'] = TitleExtractor()
            
            if self.vectorization_config.extract_keywords:
                self.extractors['keywords'] = KeywordExtractor(keywords=10)
            
            if self.vectorization_config.extract_summary:
                self.extractors['summary'] = SummaryExtractor(
                    summaries=["prev", "self", "next"]
                )
            
            logger.info(f"内容提取器初始化完成: {list(self.extractors.keys())}")
            
        except Exception as e:
            logger.error(f"内容提取器初始化失败: {str(e)}")
    
    async def convert_to_markdown(
        self, 
        content: str, 
        content_type: str = "html", 
        source_url: str = ""
    ) -> Dict[str, Any]:
        """将内容转换为Markdown格式"""
        await self.initialize()
        
        if not self.markitdown_adapter:
            logger.error("MarkItDown适配器未初始化")
            return {
                "markdown": content,
                "title": "",
                "metadata": {},
                "conversion_success": False,
                "error": "MarkItDown适配器未初始化"
            }
        
        return self.markitdown_adapter.convert_to_markdown(content, content_type, source_url)
    
    async def vectorize_content(self, markdown_content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """对Markdown内容进行向量化处理"""
        try:
            await self.initialize()
            
            if not markdown_content.strip():
                return {"error": "内容为空", "nodes": [], "embeddings": []}
            
            # 创建文档
            document = Document(
                text=markdown_content,
                metadata=metadata or {}
            )
            
            # 文本分割
            nodes = self.text_splitter.get_nodes_from_documents([document])
            
            # 内容提取
            for extractor_name, extractor in self.extractors.items():
                try:
                    nodes = extractor.extract(nodes)
                    logger.debug(f"应用提取器: {extractor_name}")
                except Exception as e:
                    logger.warning(f"提取器 {extractor_name} 执行失败: {str(e)}")
            
            # 生成嵌入向量
            embeddings = []
            if self.embedding_model:
                try:
                    for node in nodes:
                        embedding = await self._get_embedding(node.text)
                        if embedding:
                            embeddings.append(embedding)
                            node.embedding = embedding
                except Exception as e:
                    logger.error(f"嵌入向量生成失败: {str(e)}")
            
            # 构建结果
            result = {
                "nodes": [self._node_to_dict(node) for node in nodes],
                "embeddings": embeddings,
                "total_nodes": len(nodes),
                "total_embeddings": len(embeddings),
                "metadata": metadata or {}
            }
            
            logger.info(f"向量化完成: {len(nodes)} 个节点, {len(embeddings)} 个嵌入向量")
            return result
            
        except Exception as e:
            logger.error(f"内容向量化失败: {str(e)}")
            return {
                "error": str(e),
                "nodes": [],
                "embeddings": []
            }
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本嵌入向量"""
        try:
            if self.embedding_model:
                embedding = await self.embedding_model.aget_text_embedding(text)
                return embedding
            return None
        except Exception as e:
            logger.error(f"嵌入向量获取失败: {str(e)}")
            return None
    
    def _node_to_dict(self, node: TextNode) -> Dict[str, Any]:
        """将节点转换为字典"""
        return {
            "id": node.node_id,
            "text": node.text,
            "metadata": node.metadata,
            "embedding": getattr(node, 'embedding', None),
            "start_char_idx": getattr(node, 'start_char_idx', None),
            "end_char_idx": getattr(node, 'end_char_idx', None)
        }
    
    async def process_web_content(
        self, 
        html_content: str, 
        source_url: str,
        include_vectorization: bool = True,
        save_result: bool = False
    ) -> Dict[str, Any]:
        """处理网页内容的完整流程"""
        try:
            await self.initialize()
            
            logger.info(f"开始处理网页内容: {source_url}")
            
            # 1. 转换为Markdown
            markdown_result = await self.convert_to_markdown(html_content, "html", source_url)
            
            if not markdown_result["conversion_success"]:
                logger.warning("Markdown转换失败，使用原始内容")
            
            # 2. 向量化处理（可选）
            vectorization_result = {}
            if include_vectorization and markdown_result["markdown"]:
                vectorization_result = await self.vectorize_content(
                    markdown_result["markdown"], 
                    markdown_result["metadata"]
                )
            
            # 3. 整合结果
            processed_data = {
                "source_url": source_url,
                "markdown": markdown_result["markdown"],
                "title": markdown_result["title"],
                "metadata": markdown_result["metadata"],
                "vectorization_result": vectorization_result,
                "conversion_success": markdown_result["conversion_success"],
                "processing_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"网页内容处理完成: {source_url}")
            return processed_data
            
        except Exception as e:
            logger.error(f"网页内容处理失败: {str(e)}")
            return {
                "source_url": source_url,
                "error": str(e),
                "processing_timestamp": datetime.now().isoformat(),
                "conversion_success": False
            }


# 单例模式
_content_processor_instance = None

def get_content_processor() -> ContentProcessor:
    """获取内容处理器实例"""
    global _content_processor_instance
    if _content_processor_instance is None:
        _content_processor_instance = ContentProcessor()
    return _content_processor_instance


# 便捷函数
async def process_html_to_markdown(
    html_content: str, 
    source_url: str = "",
    include_vectorization: bool = True
) -> Dict[str, Any]:
    """HTML转Markdown的便捷函数"""
    processor = get_content_processor()
    return await processor.process_web_content(
        html_content, 
        source_url,
        include_vectorization=include_vectorization
    )


async def clean_and_vectorize_text(
    text_content: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """文本清洗和向量化的便捷函数"""
    processor = get_content_processor()
    await processor.initialize()
    
    return await processor.vectorize_content(text_content, metadata)
