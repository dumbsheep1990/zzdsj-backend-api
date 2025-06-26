"""
Agno向量存储适配器 - 动态配置版本
基于系统配置动态选择和配置向量数据库，
支持PostgreSQL(PgVector)、Milvus等向量存储引擎
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Type
from abc import ABC, abstractmethod

from app.config import settings
from app.frameworks.agno.embeddings import create_embedder, DynamicAgnoEmbedder
from app.frameworks.agno.model_config_adapter import get_model_adapter, ModelType

# 动态导入Agno向量数据库组件
try:
    from agno.vectordb.pgvector import PgVector, SearchType
    from agno.vectordb.lancedb import LanceDb
    from agno.knowledge.base import AgentKnowledge
    from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
    from agno.knowledge.url import UrlKnowledge
    AGNO_VECTORDB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Agno vectordb not available: {e}")
    AGNO_VECTORDB_AVAILABLE = False
    PgVector = None
    LanceDb = None
    AgentKnowledge = None

logger = logging.getLogger(__name__)

class VectorStoreInterface(ABC):
    """向量存储统一接口"""
    
    @abstractmethod
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """添加文档"""
        pass
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """删除文档"""
        pass

class DynamicVectorStore(VectorStoreInterface):
    """动态向量存储 - 基于系统配置选择向量数据库"""
    
    def __init__(
        self,
        table_name: Optional[str] = None,
        embedder: Optional[DynamicAgnoEmbedder] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化动态向量存储
        
        Args:
            table_name: 表名，如果为None则使用默认表名
            embedder: 嵌入器实例，如果为None则使用默认嵌入器
            user_id: 用户ID，用于多租户隔离
            **kwargs: 其他配置参数
        """
        self.table_name = table_name or self._get_default_table_name(user_id)
        self.embedder = embedder
        self.user_id = user_id
        self.kwargs = kwargs
        self._vector_db = None
        self._model_adapter = get_model_adapter()
    
    def _get_default_table_name(self, user_id: Optional[str] = None) -> str:
        """获取默认表名"""
        if user_id:
            return f"user_{user_id}_documents"
        return "agno_documents"
    
    async def _get_vector_db(self):
        """获取向量数据库实例"""
        if self._vector_db is None:
            await self._create_vector_db()
        return self._vector_db
    
    async def _create_vector_db(self):
        """创建向量数据库实例"""
        try:
            # 获取嵌入器
            if self.embedder is None:
                self.embedder = await create_embedder(user_id=self.user_id)
            
            # 根据系统配置选择向量数据库
            vector_db_type = await self._get_vector_db_type()
            
            if vector_db_type == "pgvector":
                self._vector_db = await self._create_pgvector()
            elif vector_db_type == "lancedb":
                self._vector_db = await self._create_lancedb()
            elif vector_db_type == "milvus":
                # Milvus集成（如果需要）
                self._vector_db = await self._create_milvus_adapter()
            else:
                # 默认使用LanceDB作为回退
                self._vector_db = await self._create_lancedb()
                
            logger.info(f"成功创建 {vector_db_type} 向量数据库实例")
            
        except Exception as e:
            logger.error(f"创建向量数据库失败: {str(e)}")
            # 创建本地回退向量存储
            await self._create_fallback_vector_store()
    
    async def _get_vector_db_type(self) -> str:
        """获取向量数据库类型"""
        # 根据系统配置确定使用的向量数据库
        if settings.MILVUS_ENABLED:
            return "milvus"
        elif settings.DATABASE_URL and AGNO_VECTORDB_AVAILABLE:
            return "pgvector"
        else:
            return "lancedb"
    
    async def _create_pgvector(self):
        """创建PgVector实例"""
        if not AGNO_VECTORDB_AVAILABLE or not PgVector:
            raise RuntimeError("PgVector不可用")
        
        return PgVector(
            table_name=self.table_name,
            db_url=settings.DATABASE_URL,
            embedder=self.embedder._embedder_instance,
            search_type=SearchType.hybrid,
            **self.kwargs
        )
    
    async def _create_lancedb(self):
        """创建LanceDB实例"""
        if not AGNO_VECTORDB_AVAILABLE or not LanceDb:
            raise RuntimeError("LanceDB不可用")
        
        # 使用本地存储路径
        db_path = self.kwargs.get("db_path", "tmp/lancedb")
        
        return LanceDb(
            uri=db_path,
            table_name=self.table_name,
            embedder=self.embedder._embedder_instance,
            search_type=SearchType.hybrid,
            **self.kwargs
        )
    
    async def _create_milvus_adapter(self):
        """创建Milvus适配器（如果需要）"""
        # 这里可以实现Milvus的适配器
        # 暂时使用LanceDB作为替代
        logger.warning("Milvus适配器尚未实现，使用LanceDB作为替代")
        return await self._create_lancedb()
    
    async def _create_fallback_vector_store(self):
        """创建回退向量存储"""
        # 最简单的内存向量存储实现
        self._vector_db = LocalVectorStore(self.embedder)
        logger.warning("使用本地内存向量存储作为回退")
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """添加文档"""
        try:
            vector_db = await self._get_vector_db()
            
            # 转换文档格式
            texts = []
            metadatas = []
            
            for doc in documents:
                if isinstance(doc, dict):
                    texts.append(doc.get("content", str(doc)))
                    metadatas.append(doc.get("metadata", {}))
                else:
                    texts.append(str(doc))
                    metadatas.append({})
            
            # 添加到向量数据库
            if hasattr(vector_db, 'add_texts'):
                await vector_db.add_texts(texts, metadatas)
            elif hasattr(vector_db, 'load_text'):
                for text in texts:
                    await vector_db.load_text(text)
            
            return True
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            vector_db = await self._get_vector_db()
            
            # 执行搜索
            if hasattr(vector_db, 'search'):
                results = await vector_db.search(query, limit=top_k)
            elif hasattr(vector_db, 'query'):
                results = await vector_db.query(query, top_k=top_k)
            else:
                # 回退搜索方法
                results = await self._fallback_search(query, top_k)
            
            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": getattr(result, 'content', str(result)),
                    "metadata": getattr(result, 'metadata', {}),
                    "score": getattr(result, 'score', 1.0),
                    "id": getattr(result, 'id', None)
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索文档失败: {str(e)}")
            return []
    
    async def _fallback_search(self, query: str, top_k: int) -> List[Any]:
        """回退搜索方法"""
        # 简单的回退搜索实现
        return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """删除文档"""
        try:
            vector_db = await self._get_vector_db()
            
            if hasattr(vector_db, 'delete'):
                for doc_id in document_ids:
                    await vector_db.delete(doc_id)
                return True
            else:
                logger.warning("向量数据库不支持删除操作")
                return False
                
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False

class LocalVectorStore(VectorStoreInterface):
    """本地内存向量存储 - 回退实现"""
    
    def __init__(self, embedder: DynamicAgnoEmbedder):
        self.embedder = embedder
        self.documents = []
        self.embeddings = []
        logger.warning("使用本地内存向量存储，仅适用于开发和测试")
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """添加文档"""
        try:
            for doc in documents:
                content = doc.get("content", str(doc)) if isinstance(doc, dict) else str(doc)
                embedding = await self.embedder.embed_text(content)
                
                self.documents.append(doc)
                self.embeddings.append(embedding)
            
            return True
        except Exception as e:
            logger.error(f"本地向量存储添加文档失败: {str(e)}")
            return False
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            if not self.documents:
                return []
            
            # 获取查询向量
            query_embedding = await self.embedder.embed_text(query)
            
            # 计算相似度
            import numpy as np
            scores = []
            
            for embedding in self.embeddings:
                # 计算余弦相似度
                query_norm = np.linalg.norm(query_embedding)
                doc_norm = np.linalg.norm(embedding)
                
                if query_norm > 0 and doc_norm > 0:
                    score = np.dot(query_embedding, embedding) / (query_norm * doc_norm)
                else:
                    score = 0.0
                
                scores.append(score)
            
            # 排序并返回top_k结果
            indexed_scores = list(enumerate(scores))
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for i, score in indexed_scores[:top_k]:
                doc = self.documents[i]
                result = {
                    "content": doc.get("content", str(doc)) if isinstance(doc, dict) else str(doc),
                    "metadata": doc.get("metadata", {}) if isinstance(doc, dict) else {},
                    "score": float(score),
                    "id": str(i)
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"本地向量存储搜索失败: {str(e)}")
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """删除文档"""
        try:
            # 转换ID为索引
            indices_to_remove = []
            for doc_id in document_ids:
                try:
                    index = int(doc_id)
                    if 0 <= index < len(self.documents):
                        indices_to_remove.append(index)
                except ValueError:
                    pass
            
            # 从后往前删除，避免索引错乱
            for index in sorted(indices_to_remove, reverse=True):
                del self.documents[index]
                del self.embeddings[index]
            
            return True
            
        except Exception as e:
            logger.error(f"本地向量存储删除文档失败: {str(e)}")
            return False

# 知识库管理

class DynamicKnowledgeBase:
    """动态知识库 - 基于配置创建不同类型的知识库"""
    
    def __init__(
        self,
        kb_type: str = "agent",  # agent, pdf_url, url
        sources: Optional[List[str]] = None,
        vector_store: Optional[DynamicVectorStore] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化动态知识库
        
        Args:
            kb_type: 知识库类型
            sources: 数据源列表
            vector_store: 向量存储实例
            user_id: 用户ID
            **kwargs: 其他配置参数
        """
        self.kb_type = kb_type
        self.sources = sources or []
        self.vector_store = vector_store
        self.user_id = user_id
        self.kwargs = kwargs
        self._knowledge_base = None
    
    async def get_knowledge_base(self):
        """获取知识库实例"""
        if self._knowledge_base is None:
            await self._create_knowledge_base()
        return self._knowledge_base
    
    async def _create_knowledge_base(self):
        """创建知识库实例"""
        try:
            if not AGNO_VECTORDB_AVAILABLE:
                raise RuntimeError("Agno知识库组件不可用")
            
            # 创建向量存储
            if self.vector_store is None:
                self.vector_store = DynamicVectorStore(user_id=self.user_id)
            
            vector_db = await self.vector_store._get_vector_db()
            
            if self.kb_type == "pdf_url" and PDFUrlKnowledgeBase:
                self._knowledge_base = PDFUrlKnowledgeBase(
                    urls=self.sources,
                    vector_db=vector_db,
                    **self.kwargs
                )
            elif self.kb_type == "url" and UrlKnowledge:
                self._knowledge_base = UrlKnowledge(
                    urls=self.sources,
                    vector_db=vector_db,
                    **self.kwargs
                )
            elif self.kb_type == "agent" and AgentKnowledge:
                self._knowledge_base = AgentKnowledge(
                    vector_db=vector_db,
                    **self.kwargs
                )
            else:
                # 创建基础Agent知识库
                self._knowledge_base = AgentKnowledge(
                    vector_db=vector_db,
                    **self.kwargs
                )
                
            logger.info(f"成功创建 {self.kb_type} 类型知识库")
            
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            # 创建简单的回退知识库
            self._knowledge_base = SimpleKnowledgeBase(self.vector_store)
    
    async def load_data(self, recreate: bool = False):
        """加载数据"""
        try:
            knowledge_base = await self.get_knowledge_base()
            
            if hasattr(knowledge_base, 'load'):
                await knowledge_base.load(recreate=recreate)
            elif hasattr(knowledge_base, 'load_data'):
                await knowledge_base.load_data()
            
            logger.info("知识库数据加载完成")
            
        except Exception as e:
            logger.error(f"加载知识库数据失败: {str(e)}")

class SimpleKnowledgeBase:
    """简单知识库实现 - 回退方案"""
    
    def __init__(self, vector_store: DynamicVectorStore):
        self.vector_store = vector_store
        logger.warning("使用简单知识库实现")
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """搜索知识库"""
        return await self.vector_store.search(query, **kwargs)
    
    async def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """添加文本"""
        doc = {"content": text, "metadata": metadata or {}}
        await self.vector_store.add_documents([doc])

# 工厂函数

async def create_vector_store(
    vector_db_type: Optional[str] = None,
    table_name: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> DynamicVectorStore:
    """
    创建向量存储实例
    
    Args:
        vector_db_type: 向量数据库类型
        table_name: 表名
        user_id: 用户ID
        **kwargs: 其他配置参数
        
    Returns:
        DynamicVectorStore: 向量存储实例
    """
    return DynamicVectorStore(
        table_name=table_name,
        user_id=user_id,
        **kwargs
    )

async def create_knowledge_base(
    kb_type: str = "agent",
    sources: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> DynamicKnowledgeBase:
    """
    创建知识库实例
    
    Args:
        kb_type: 知识库类型
        sources: 数据源
        user_id: 用户ID
        **kwargs: 其他配置参数
        
    Returns:
        DynamicKnowledgeBase: 知识库实例
    """
    return DynamicKnowledgeBase(
        kb_type=kb_type,
        sources=sources,
        user_id=user_id,
        **kwargs
    )

# 兼容性函数

def get_vector_store_config() -> Dict[str, Any]:
    """获取向量存储配置"""
    return {
        "database_url": settings.DATABASE_URL,
        "milvus_enabled": settings.MILVUS_ENABLED,
        "milvus_host": getattr(settings, 'MILVUS_HOST', 'localhost'),
        "milvus_port": getattr(settings, 'MILVUS_PORT', 19530),
        "deployment_mode": settings.DEPLOYMENT_MODE
    } 