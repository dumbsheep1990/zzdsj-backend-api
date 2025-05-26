"""
Agno知识库模块：提供与Agno知识库功能的集成，
用于文档管理、分块、索引和检索
"""

from typing import Dict, List, Any, Optional, Union, Callable
import json
import os
import logging
import asyncio
from datetime import datetime
import uuid

# 导入统一的切分工具
from app.tools.base.document_chunking import (
    get_chunking_tool, 
    ChunkingConfig, 
    DocumentChunk,
    ChunkingResult
)

# 导入向量化相关
from app.frameworks.llamaindex.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

class AgnoKnowledgeBase:
    """
    Agno知识库实现
    提供完整的文档管理、切分、向量化和检索功能
    """
    
    def __init__(self, kb_id: str, name: str = None, config: Dict[str, Any] = None):
        """
        初始化Agno知识库
        
        参数：
            kb_id: 知识库ID
            name: 知识库名称
            config: 知识库配置
        """
        self.kb_id = kb_id
        self.name = name or f"AgnoKB-{kb_id}"
        self.config = config or {}
        
        # 初始化组件
        self.chunking_tool = get_chunking_tool()
        self.embedding_model = get_embedding_model()
        
        # 知识库配置
        self.chunking_config = self._create_chunking_config()
        
        # 文档存储
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: Dict[str, DocumentChunk] = {}
        self.chunk_embeddings: Dict[str, List[float]] = {}
        
        # 索引和检索相关
        self.vector_index = None
        self._init_vector_store()
        
        logger.info(f"初始化Agno知识库: {self.name} (ID: {kb_id})")
    
    def _create_chunking_config(self) -> ChunkingConfig:
        """创建切分配置"""
        from app.frameworks.agno.config import get_agno_config
        agno_config = get_agno_config()
        
        return ChunkingConfig(
            strategy=self.config.get("chunking_strategy", "sentence"),
            chunk_size=agno_config.kb_settings.get("chunk_size", 1000),
            chunk_overlap=agno_config.kb_settings.get("chunk_overlap", 200),
            language=self.config.get("language", "zh"),
            preserve_structure=self.config.get("preserve_structure", True),
            semantic_threshold=agno_config.kb_settings.get("similarity_threshold", 0.7)
        )
    
    def _init_vector_store(self):
        """初始化向量存储"""
        try:
            # 这里可以集成不同的向量数据库
            # 目前使用简单的内存存储
            self.vector_index = {
                "vectors": {},
                "metadata": {},
                "dimension": None
            }
            logger.info("向量存储初始化完成")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {str(e)}")
    
    async def add_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        向知识库添加文档
        
        参数：
            document: 包含content、metadata等的文档数据
            
        返回：
            添加结果
        """
        try:
            content = document.get("content", "")
            metadata = document.get("metadata", {})
            doc_id = document.get("id") or str(uuid.uuid4())
            
            logger.info(f"添加文档到知识库 {self.name}: {doc_id}")
            
            # 1. 文档切分
            chunking_result = self.chunking_tool.chunk_document(content, self.chunking_config)
            
            if not chunking_result.chunks:
                raise ValueError("文档切分失败或无有效内容")
            
            # 2. 向量化
            chunk_embeddings = await self._generate_embeddings(chunking_result.chunks)
            
            # 3. 存储文档信息
            self.documents[doc_id] = {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "chunk_count": len(chunking_result.chunks),
                "created_at": datetime.now().isoformat(),
                "status": "indexed"
            }
            
            # 4. 存储切片和向量
            chunk_ids = []
            for i, chunk in enumerate(chunking_result.chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk.chunk_id = chunk_id
                chunk.metadata.update({
                    "document_id": doc_id,
                    "chunk_index": i,
                    **metadata
                })
                
                self.chunks[chunk_id] = chunk
                self.chunk_embeddings[chunk_id] = chunk_embeddings[i]
                chunk_ids.append(chunk_id)
                
                # 添加到向量索引
                self._add_to_vector_index(chunk_id, chunk_embeddings[i], chunk.metadata)
            
            result = {
                "document_id": doc_id,
                "chunks": len(chunking_result.chunks),
                "chunk_ids": chunk_ids,
                "strategy_used": chunking_result.strategy_used,
                "processing_time": chunking_result.processing_time,
                "status": "success"
            }
            
            logger.info(f"文档 {doc_id} 添加成功: {len(chunking_result.chunks)}个切片")
            return result
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return {
                "document_id": doc_id if 'doc_id' in locals() else None,
                "status": "error",
                "error": str(e)
            }
    
    async def _generate_embeddings(self, chunks: List[DocumentChunk]) -> List[List[float]]:
        """为文档切片生成向量"""
        embeddings = []
        
        # 批量处理以提高效率
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_texts = [chunk.content for chunk in batch]
            
            try:
                # 调用embedding模型
                batch_embeddings = []
                for text in batch_texts:
                    embedding = self.embedding_model.get_text_embedding(text)
                    batch_embeddings.append(embedding)
                
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"生成embedding失败: {str(e)}")
                # 生成零向量作为后备
                dummy_embedding = [0.0] * 1536  # 假设维度为1536
                embeddings.extend([dummy_embedding] * len(batch))
        
        return embeddings
    
    def _add_to_vector_index(self, chunk_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """添加向量到索引"""
        if self.vector_index["dimension"] is None:
            self.vector_index["dimension"] = len(embedding)
        
        self.vector_index["vectors"][chunk_id] = embedding
        self.vector_index["metadata"][chunk_id] = metadata
    
    async def retrieve(self, query: str, top_k: int = 5, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        从知识库检索相关文档
        
        参数：
            query: 查询字符串
            top_k: 返回的文档数量
            filter_criteria: 过滤条件
            
        返回：
            相关文档列表
        """
        try:
            if not self.chunks:
                return []
            
            # 1. 生成查询向量
            query_embedding = self.embedding_model.get_text_embedding(query)
            
            # 2. 计算相似度
            similarities = []
            for chunk_id, chunk_embedding in self.chunk_embeddings.items():
                # 应用过滤条件
                if filter_criteria and not self._match_filter(chunk_id, filter_criteria):
                    continue
                
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                similarities.append((chunk_id, similarity))
            
            # 3. 排序并取前k个
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_chunks = similarities[:top_k]
            
            # 4. 构建结果
            results = []
            for chunk_id, score in top_chunks:
                chunk = self.chunks[chunk_id]
                result = {
                    "chunk_id": chunk_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "score": float(score),
                    "document_id": chunk.metadata.get("document_id"),
                    "chunk_index": chunk.metadata.get("chunk_index")
                }
                results.append(result)
            
            logger.info(f"检索完成: 查询='{query}', 返回{len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []
    
    def _match_filter(self, chunk_id: str, filter_criteria: Dict[str, Any]) -> bool:
        """检查切片是否匹配过滤条件"""
        chunk_metadata = self.vector_index["metadata"].get(chunk_id, {})
        
        for key, value in filter_criteria.items():
            if key not in chunk_metadata:
                return False
            
            chunk_value = chunk_metadata[key]
            
            # 支持不同类型的过滤
            if isinstance(value, list):
                if chunk_value not in value:
                    return False
            elif isinstance(value, dict):
                # 支持范围过滤等
                if "$gte" in value and chunk_value < value["$gte"]:
                    return False
                if "$lte" in value and chunk_value > value["$lte"]:
                    return False
            else:
                if chunk_value != value:
                    return False
        
        return True
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def search(self, query: str, filter_criteria: Optional[Dict[str, Any]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索接口，支持复杂查询
        """
        return await self.retrieve(query, top_k, filter_criteria)
    
    async def remove_document(self, document_id: str) -> Dict[str, Any]:
        """
        从知识库中删除文档
        
        参数：
            document_id: 要删除的文档ID
            
        返回：
            删除结果
        """
        try:
            if document_id not in self.documents:
                return {"status": "error", "error": "Document not found"}
            
            # 1. 获取文档的所有切片
            chunks_to_remove = [chunk_id for chunk_id, chunk in self.chunks.items() 
                              if chunk.metadata.get("document_id") == document_id]
            
            # 2. 删除切片和向量
            for chunk_id in chunks_to_remove:
                del self.chunks[chunk_id]
                del self.chunk_embeddings[chunk_id]
                
                # 从向量索引中删除
                if chunk_id in self.vector_index["vectors"]:
                    del self.vector_index["vectors"][chunk_id]
                if chunk_id in self.vector_index["metadata"]:
                    del self.vector_index["metadata"][chunk_id]
            
            # 3. 删除文档记录
            del self.documents[document_id]
            
            logger.info(f"文档 {document_id} 删除成功，移除了 {len(chunks_to_remove)} 个切片")
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_removed": len(chunks_to_remove)
            }
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {
                "status": "error",
                "document_id": document_id,
                "error": str(e)
            }
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量添加文档
        
        参数：
            documents: 文档列表
            
        返回：
            批量添加结果
        """
        results = []
        total_chunks = 0
        
        for doc in documents:
            result = await self.add_document(doc)
            results.append(result)
            if result["status"] == "success":
                total_chunks += result["chunks"]
        
        success_count = len([r for r in results if r["status"] == "success"])
        
        return {
            "document_count": len(documents),
            "success_count": success_count,
            "error_count": len(documents) - success_count,
            "total_chunks": total_chunks,
            "status": "completed",
            "results": results
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        返回：
            统计信息
        """
        total_chars = sum(len(doc["content"]) for doc in self.documents.values())
        
        # 按文档类型统计
        doc_types = {}
        for doc in self.documents.values():
            doc_type = doc.get("metadata", {}).get("type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        return {
            "kb_id": self.kb_id,
            "name": self.name,
            "document_count": len(self.documents),
            "chunk_count": len(self.chunks),
            "total_characters": total_chars,
            "vector_dimension": self.vector_index.get("dimension"),
            "embedding_model": getattr(self.embedding_model, 'model_name', 'unknown'),
            "chunking_strategy": self.chunking_config.strategy,
            "document_types": doc_types,
            "created_at": getattr(self, 'created_at', datetime.now().isoformat()),
            "last_updated": datetime.now().isoformat()
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新知识库配置"""
        self.config.update(new_config)
        self.chunking_config = self._create_chunking_config()
        logger.info(f"知识库 {self.name} 配置已更新")

class KnowledgeBaseProcessor:
    """
    Agno知识库处理器 - 提供统一的知识库管理接口
    """
    
    def __init__(self, kb_id: str, name: str = None, config: Dict[str, Any] = None):
        """
        初始化知识库处理器
        
        参数：
            kb_id: 知识库ID
            name: 知识库名称
            config: 知识库配置
        """
        self.kb_id = kb_id
        self.agno_kb = AgnoKnowledgeBase(kb_id, name, config)
        
        logger.info(f"初始化Agno知识库处理器: {name or kb_id}")
    
    async def add_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """向知识库添加文档"""
        return await self.agno_kb.add_document(document)
    
    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """从知识库检索相关文档"""
        return await self.agno_kb.retrieve(query, top_k)
    
    async def search(self, query: str, filter_criteria: Optional[Dict[str, Any]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索文档"""
        return await self.agno_kb.search(query, filter_criteria, top_k)
    
    async def remove_document(self, document_id: str) -> Dict[str, Any]:
        """删除文档"""
        return await self.agno_kb.remove_document(document_id)
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量添加文档"""
        return await self.agno_kb.add_documents(documents)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.agno_kb.get_stats()
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.agno_kb.update_config(new_config)

# 全局知识库管理器
_knowledge_bases: Dict[str, KnowledgeBaseProcessor] = {}

def get_knowledge_base(kb_id: str, name: str = None, config: Dict[str, Any] = None) -> KnowledgeBaseProcessor:
    """获取或创建知识库实例"""
    if kb_id not in _knowledge_bases:
        _knowledge_bases[kb_id] = KnowledgeBaseProcessor(kb_id, name, config)
    return _knowledge_bases[kb_id]

def list_knowledge_bases() -> List[Dict[str, Any]]:
    """列出所有知识库"""
    return [kb.get_stats() for kb in _knowledge_bases.values()]

async def create_knowledge_base(kb_id: str, name: str, config: Dict[str, Any] = None) -> KnowledgeBaseProcessor:
    """创建新的知识库"""
    if kb_id in _knowledge_bases:
        raise ValueError(f"知识库 {kb_id} 已存在")
    
    kb_processor = KnowledgeBaseProcessor(kb_id, name, config)
    _knowledge_bases[kb_id] = kb_processor
    
    logger.info(f"创建Agno知识库: {name} (ID: {kb_id})")
    return kb_processor
