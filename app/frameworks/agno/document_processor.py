"""
Agno文档处理器 - 使用正确的官方Agno API
基于Agno的Knowledge Base和Vector DB系统实现文档处理
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
import tempfile
import os

# 使用正确的Agno官方API导入
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.website import WebsiteKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.vectordb.pgvector import PgVector
from agno.embedder.openai import OpenAIEmbedder
from agno.chunking.text_splitter import TextSplitter

logger = logging.getLogger(__name__)

class AgnoDocumentProcessor:
    """
    Agno文档处理器 - 使用官方Agno Knowledge Base API
    支持多种文档类型和向量数据库后端
    """
    
    def __init__(
        self,
        vector_db_type: str = "lancedb",  # lancedb, pgvector
        vector_db_config: Optional[Dict[str, Any]] = None,
        embedder_model: str = "text-embedding-3-small",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        search_type: str = "hybrid",  # hybrid, vector, keyword
        **kwargs
    ):
        self.vector_db_type = vector_db_type
        self.vector_db_config = vector_db_config or {}
        self.embedder_model = embedder_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.search_type = SearchType.hybrid if search_type == "hybrid" else SearchType.vector
        
        # 创建嵌入器
        self.embedder = OpenAIEmbedder(id=embedder_model)
        
        # 创建文本分割器
        self.text_splitter = TextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        logger.info(f"Initialized Agno document processor with {vector_db_type}")
    
    def _create_vector_db(self, table_name: str, **kwargs) -> Union[LanceDb, PgVector]:
        """创建向量数据库实例"""
        if self.vector_db_type == "lancedb":
            return LanceDb(
                uri=self.vector_db_config.get("uri", "tmp/lancedb"),
                table_name=table_name,
                search_type=self.search_type,
                embedder=self.embedder,
                **kwargs
            )
        elif self.vector_db_type == "pgvector":
            return PgVector(
                db_url=self.vector_db_config.get("db_url", "postgresql://localhost/agno"),
                table_name=table_name,
                search_type=self.search_type,
                embedder=self.embedder,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported vector db type: {self.vector_db_type}")
    
    def create_pdf_knowledge_base(
        self,
        pdf_paths: Union[str, List[str]],
        kb_name: str = "pdf_kb",
        **kwargs
    ) -> PDFKnowledgeBase:
        """
        创建PDF知识库
        
        参数:
            pdf_paths: PDF文件路径或路径列表
            kb_name: 知识库名称
            **kwargs: 其他参数
            
        返回:
            PDF知识库实例
        """
        try:
            # 确保pdf_paths是列表
            if isinstance(pdf_paths, str):
                pdf_paths = [pdf_paths]
            
            # 创建向量数据库
            vector_db = self._create_vector_db(kb_name, **kwargs)
            
            # 创建PDF知识库
            knowledge_base = PDFKnowledgeBase(
                path=pdf_paths[0] if len(pdf_paths) == 1 else pdf_paths,
                vector_db=vector_db,
                chunking_strategy=self.text_splitter,
                **kwargs
            )
            
            logger.info(f"Created PDF knowledge base: {kb_name}")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Failed to create PDF knowledge base: {e}")
            raise
    
    def create_pdf_url_knowledge_base(
        self,
        pdf_urls: Union[str, List[str]],
        kb_name: str = "pdf_url_kb",
        **kwargs
    ) -> PDFUrlKnowledgeBase:
        """
        创建PDF URL知识库
        
        参数:
            pdf_urls: PDF URL或URL列表
            kb_name: 知识库名称
            **kwargs: 其他参数
            
        返回:
            PDF URL知识库实例
        """
        try:
            # 确保pdf_urls是列表
            if isinstance(pdf_urls, str):
                pdf_urls = [pdf_urls]
            
            # 创建向量数据库
            vector_db = self._create_vector_db(kb_name, **kwargs)
            
            # 创建PDF URL知识库
            knowledge_base = PDFUrlKnowledgeBase(
                urls=pdf_urls,
                vector_db=vector_db,
                chunking_strategy=self.text_splitter,
                **kwargs
            )
            
            logger.info(f"Created PDF URL knowledge base: {kb_name}")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Failed to create PDF URL knowledge base: {e}")
            raise
    
    def create_text_knowledge_base(
        self,
        texts: Union[str, List[str]],
        kb_name: str = "text_kb",
        **kwargs
    ) -> TextKnowledgeBase:
        """
        创建文本知识库
        
        参数:
            texts: 文本内容或文本列表
            kb_name: 知识库名称
            **kwargs: 其他参数
            
        返回:
            文本知识库实例
        """
        try:
            # 确保texts是列表
            if isinstance(texts, str):
                texts = [texts]
            
            # 创建向量数据库
            vector_db = self._create_vector_db(kb_name, **kwargs)
            
            # 创建文本知识库
            knowledge_base = TextKnowledgeBase(
                texts=texts,
                vector_db=vector_db,
                chunking_strategy=self.text_splitter,
                **kwargs
            )
            
            logger.info(f"Created text knowledge base: {kb_name}")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Failed to create text knowledge base: {e}")
            raise
    
    def create_website_knowledge_base(
        self,
        urls: Union[str, List[str]],
        kb_name: str = "website_kb",
        max_links: int = 10,
        **kwargs
    ) -> WebsiteKnowledgeBase:
        """
        创建网站知识库
        
        参数:
            urls: 网站URL或URL列表
            kb_name: 知识库名称
            max_links: 最大链接数
            **kwargs: 其他参数
            
        返回:
            网站知识库实例
        """
        try:
            # 确保urls是列表
            if isinstance(urls, str):
                urls = [urls]
            
            # 创建向量数据库
            vector_db = self._create_vector_db(kb_name, **kwargs)
            
            # 创建网站知识库
            knowledge_base = WebsiteKnowledgeBase(
                urls=urls,
                vector_db=vector_db,
                max_links=max_links,
                chunking_strategy=self.text_splitter,
                **kwargs
            )
            
            logger.info(f"Created website knowledge base: {kb_name}")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Failed to create website knowledge base: {e}")
            raise
    
    async def process_documents_async(
        self,
        documents: List[Dict[str, Any]],
        kb_name: str = "mixed_kb",
        **kwargs
    ) -> Any:
        """
        异步处理混合文档类型
        
        参数:
            documents: 文档列表，每个文档包含type和content/path/url
            kb_name: 知识库名称
            **kwargs: 其他参数
            
        返回:
            知识库实例
        """
        try:
            # 按类型分组文档
            pdf_paths = []
            pdf_urls = []
            texts = []
            website_urls = []
            
            for doc in documents:
                doc_type = doc.get("type", "").lower()
                if doc_type == "pdf" and "path" in doc:
                    pdf_paths.append(doc["path"])
                elif doc_type == "pdf_url" and "url" in doc:
                    pdf_urls.append(doc["url"])
                elif doc_type == "text" and "content" in doc:
                    texts.append(doc["content"])
                elif doc_type == "website" and "url" in doc:
                    website_urls.append(doc["url"])
            
            # 创建向量数据库
            vector_db = self._create_vector_db(kb_name, **kwargs)
            
            # 处理不同类型的文档
            knowledge_bases = []
            
            if pdf_paths:
                kb = await asyncio.create_task(
                    asyncio.to_thread(
                        self.create_pdf_knowledge_base,
                        pdf_paths,
                        f"{kb_name}_pdf"
                    )
                )
                knowledge_bases.append(kb)
            
            if pdf_urls:
                kb = await asyncio.create_task(
                    asyncio.to_thread(
                        self.create_pdf_url_knowledge_base,
                        pdf_urls,
                        f"{kb_name}_pdf_url"
                    )
                )
                knowledge_bases.append(kb)
            
            if texts:
                kb = await asyncio.create_task(
                    asyncio.to_thread(
                        self.create_text_knowledge_base,
                        texts,
                        f"{kb_name}_text"
                    )
                )
                knowledge_bases.append(kb)
            
            if website_urls:
                kb = await asyncio.create_task(
                    asyncio.to_thread(
                        self.create_website_knowledge_base,
                        website_urls,
                        f"{kb_name}_website"
                    )
                )
                knowledge_bases.append(kb)
            
            # 如果只有一个知识库，直接返回
            if len(knowledge_bases) == 1:
                return knowledge_bases[0]
            
            # 如果有多个知识库，返回第一个（或实现合并逻辑）
            logger.info(f"Created {len(knowledge_bases)} knowledge bases")
            return knowledge_bases[0] if knowledge_bases else None
            
        except Exception as e:
            logger.error(f"Failed to process documents async: {e}")
            raise
    
    def load_knowledge_base(self, knowledge_base: Any, upsert: bool = True) -> bool:
        """
        加载知识库到向量数据库
        
        参数:
            knowledge_base: 知识库实例
            upsert: 是否更新已存在的数据
            
        返回:
            是否成功
        """
        try:
            knowledge_base.load(upsert=upsert)
            logger.info("Knowledge base loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            return False
    
    async def aload_knowledge_base(self, knowledge_base: Any, upsert: bool = True) -> bool:
        """异步加载知识库"""
        return await asyncio.create_task(
            asyncio.to_thread(self.load_knowledge_base, knowledge_base, upsert)
        )

class AgnoFileProcessor:
    """
    Agno文件处理器 - 处理上传的文件
    支持多种文件格式的自动识别和处理
    """
    
    def __init__(self, document_processor: AgnoDocumentProcessor):
        self.document_processor = document_processor
        self.supported_extensions = {
            ".pdf": "pdf",
            ".txt": "text", 
            ".md": "text",
            ".doc": "text",
            ".docx": "text"
        }
    
    def process_uploaded_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        kb_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        处理上传的文件
        
        参数:
            file_path: 文件路径
            file_name: 文件名（可选）
            kb_name: 知识库名称（可选）
            **kwargs: 其他参数
            
        返回:
            知识库实例
        """
        try:
            path = Path(file_path)
            extension = path.suffix.lower()
            file_name = file_name or path.name
            kb_name = kb_name or f"kb_{path.stem}"
            
            if extension not in self.supported_extensions:
                raise ValueError(f"Unsupported file extension: {extension}")
            
            file_type = self.supported_extensions[extension]
            
            if file_type == "pdf":
                return self.document_processor.create_pdf_knowledge_base(
                    file_path, kb_name, **kwargs
                )
            elif file_type == "text":
                # 读取文本文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return self.document_processor.create_text_knowledge_base(
                    content, kb_name, **kwargs
                )
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
        except Exception as e:
            logger.error(f"Failed to process uploaded file: {e}")
            raise
    
    async def aprocess_uploaded_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        kb_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """异步处理上传的文件"""
        return await asyncio.create_task(
            asyncio.to_thread(
                self.process_uploaded_file,
                file_path,
                file_name,
                kb_name,
                **kwargs
            )
        )
    
    def process_multiple_files(
        self,
        file_paths: List[str],
        kb_name: str = "multi_file_kb",
        **kwargs
    ) -> Any:
        """
        处理多个文件
        
        参数:
            file_paths: 文件路径列表
            kb_name: 知识库名称
            **kwargs: 其他参数
            
        返回:
            知识库实例
        """
        try:
            documents = []
            
            for file_path in file_paths:
                path = Path(file_path)
                extension = path.suffix.lower()
                
                if extension == ".pdf":
                    documents.append({
                        "type": "pdf",
                        "path": file_path
                    })
                elif extension in [".txt", ".md"]:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    documents.append({
                        "type": "text",
                        "content": content
                    })
            
            # 使用异步处理
            return asyncio.run(
                self.document_processor.process_documents_async(
                    documents, kb_name, **kwargs
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to process multiple files: {e}")
            raise

# 便利函数 - 创建常用的处理器
def create_document_processor(
    vector_db_type: str = "lancedb",
    vector_db_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> AgnoDocumentProcessor:
    """创建文档处理器"""
    return AgnoDocumentProcessor(
        vector_db_type=vector_db_type,
        vector_db_config=vector_db_config,
        **kwargs
    )

def create_file_processor(
    document_processor: Optional[AgnoDocumentProcessor] = None,
    **kwargs
) -> AgnoFileProcessor:
    """创建文件处理器"""
    if document_processor is None:
        document_processor = create_document_processor(**kwargs)
    
    return AgnoFileProcessor(document_processor)

# LlamaIndex兼容性别名
DocumentProcessor = AgnoDocumentProcessor
FileProcessor = AgnoFileProcessor

# 导出主要组件
__all__ = [
    "AgnoDocumentProcessor",
    "AgnoFileProcessor",
    "create_document_processor",
    "create_file_processor",
    "DocumentProcessor",
    "FileProcessor"
] 