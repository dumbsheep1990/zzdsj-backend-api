"""
知识库向量服务模块
整合向量存储与知识库功能，提供完整的向量管理能力
"""

import logging
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.utils.storage.core.vector_factory import VectorStorageFactory, VectorBackendType, KnowledgeBaseVectorManager
from app.utils.storage.core.base import VectorStorage
from app.repositories.knowledge import KnowledgeBaseRepository, DocumentRepository, DocumentChunkRepository
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from core.knowledge.vector_manager import VectorManager
from app.config import settings

logger = logging.getLogger(__name__)


class KnowledgeVectorService:
    """
    知识库向量服务类
    提供知识库与向量存储的完整集成服务
    """
    
    def __init__(self, db: Session, vector_backend: VectorBackendType = VectorBackendType.MILVUS):
        """
        初始化知识库向量服务
        
        参数:
            db: 数据库会话
            vector_backend: 向量存储后端类型
        """
        self.db = db
        self.vector_backend = vector_backend
        
        # 初始化知识库仓库
        self.kb_repo = KnowledgeBaseRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        
        # 初始化向量管理器
        self.vector_manager = VectorManager(db)
        
        # 延迟初始化向量存储相关组件
        self._vector_store: Optional[VectorStorage] = None
        self._kb_vector_manager: Optional[KnowledgeBaseVectorManager] = None
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @property
    def vector_store(self) -> VectorStorage:
        """获取向量存储实例（延迟初始化）"""
        if self._vector_store is None:
            # 根据配置文件或环境变量选择向量数据库配置
            config = self._get_vector_config()
            
            self._vector_store = VectorStorageFactory.create_knowledge_base_store(
                backend_type=self.vector_backend,
                config=config
            )
        
        return self._vector_store
    
    @property
    def kb_vector_manager(self) -> KnowledgeBaseVectorManager:
        """获取知识库向量管理器（延迟初始化）"""
        if self._kb_vector_manager is None:
            self._kb_vector_manager = KnowledgeBaseVectorManager(self.vector_store)
        
        return self._kb_vector_manager
    
    def _get_vector_config(self) -> Dict[str, Any]:
        """根据后端类型获取向量数据库配置"""
        base_config = {
            "default_dimension": getattr(settings, "EMBEDDING_DIMENSION", 1536),
            "batch_size": getattr(settings, "VECTOR_BATCH_SIZE", 1000),
            "timeout": getattr(settings, "VECTOR_TIMEOUT", 30),
        }
        
        if self.vector_backend == VectorBackendType.MILVUS:
            base_config.update({
                "host": getattr(settings, "MILVUS_HOST", "localhost"),
                "port": getattr(settings, "MILVUS_PORT", 19530),
                "user": getattr(settings, "MILVUS_USER", ""),
                "password": getattr(settings, "MILVUS_PASSWORD", ""),
            })
        elif self.vector_backend == VectorBackendType.PGVECTOR:
            base_config.update({
                "host": getattr(settings, "PGVECTOR_HOST", "localhost"),
                "port": getattr(settings, "PGVECTOR_PORT", 5432),
                "user": getattr(settings, "PGVECTOR_USER", "postgres"),
                "password": getattr(settings, "PGVECTOR_PASSWORD", "password"),
                "database": getattr(settings, "PGVECTOR_DATABASE", "postgres"),
            })
        elif self.vector_backend == VectorBackendType.ELASTICSEARCH:
            base_config.update({
                "es_url": getattr(settings, "ELASTICSEARCH_URL", "http://localhost:9200"),
                "username": getattr(settings, "ELASTICSEARCH_USER", ""),
                "password": getattr(settings, "ELASTICSEARCH_PASSWORD", ""),
            })
        
        return base_config
    
    # ========== 知识库管理方法 ==========
    
    async def create_knowledge_base(self, 
                                  name: str, 
                                  description: Optional[str] = None,
                                  embedding_model: Optional[str] = None,
                                  vector_dimension: int = 1536) -> Dict[str, Any]:
        """
        创建新知识库（包含向量集合）
        
        参数:
            name: 知识库名称
            description: 知识库描述
            embedding_model: 嵌入模型
            vector_dimension: 向量维度
        
        返回:
            创建结果
        """
        try:
            # 使用默认嵌入模型（如果未指定）
            if not embedding_model:
                embedding_model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-ada-002")
            
            # 创建知识库记录
            kb_data = {
                "id": str(uuid.uuid4()),
                "name": name,
                "description": description,
                "embedding_model": embedding_model,
                "vector_dimension": vector_dimension,
                "status": "creating",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            kb = self.kb_repo.create(kb_data)
            
            # 创建对应的向量集合
            collection_created = await self.kb_vector_manager.create_knowledge_base_collection(
                kb_id=kb.id,
                dimension=vector_dimension
            )
            
            if collection_created:
                # 更新知识库状态为活跃
                self.kb_repo.update(kb.id, {"status": "active"})
                
                self.logger.info(f"知识库创建成功: {name} (ID: {kb.id})")
                
                return {
                    "success": True,
                    "data": {
                        "knowledge_base": kb,
                        "collection_created": True
                    }
                }
            else:
                # 如果向量集合创建失败，删除知识库记录
                self.kb_repo.delete(kb.id)
                
                return {
                    "success": False,
                    "error": "创建向量集合失败",
                    "error_code": "VECTOR_COLLECTION_FAILED"
                }
                
        except Exception as e:
            self.logger.error(f"创建知识库时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建知识库失败: {str(e)}",
                "error_code": "CREATION_FAILED"
            }
    
    async def delete_knowledge_base(self, kb_id: str) -> Dict[str, Any]:
        """
        删除知识库（包含向量集合和所有数据）
        
        参数:
            kb_id: 知识库ID
        
        返回:
            删除结果
        """
        try:
            # 检查知识库是否存在
            kb = self.kb_repo.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 删除向量集合
            vector_deleted = await self.kb_vector_manager.delete_knowledge_base_collection(kb_id)
            
            # 删除数据库中的知识库记录（级联删除文档和分块）
            db_deleted = self.kb_repo.delete(kb_id)
            
            if vector_deleted and db_deleted:
                self.logger.info(f"知识库删除成功: {kb.name} (ID: {kb_id})")
                return {
                    "success": True,
                    "data": {
                        "kb_id": kb_id,
                        "name": kb.name
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "删除操作部分失败",
                    "error_code": "PARTIAL_DELETE_FAILED",
                    "details": {
                        "vector_deleted": vector_deleted,
                        "db_deleted": db_deleted
                    }
                }
                
        except Exception as e:
            self.logger.error(f"删除知识库时出错: {kb_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"删除知识库失败: {str(e)}",
                "error_code": "DELETION_FAILED"
            }
    
    async def get_knowledge_base_info(self, kb_id: str) -> Dict[str, Any]:
        """
        获取知识库详细信息（包含向量统计）
        
        参数:
            kb_id: 知识库ID
        
        返回:
            知识库信息
        """
        try:
            # 获取数据库中的知识库信息
            kb = self.kb_repo.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 获取向量统计信息
            vector_stats = await self.kb_vector_manager.get_knowledge_base_stats(kb_id)
            
            # 获取文档统计
            documents = self.doc_repo.get_by_knowledge_base_id(kb_id)
            
            return {
                "success": True,
                "data": {
                    "knowledge_base": kb,
                    "vector_stats": vector_stats,
                    "document_count": len(documents),
                    "documents": documents
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取知识库信息时出错: {kb_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"获取知识库信息失败: {str(e)}",
                "error_code": "GET_INFO_FAILED"
            }
    
    # ========== 文档管理方法 ==========
    
    async def add_document_with_vectors(self,
                                      kb_id: str,
                                      file_name: str,
                                      content: str,
                                      chunks: Optional[List[Dict[str, Any]]] = None,
                                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        添加文档到知识库并生成向量
        
        参数:
            kb_id: 知识库ID
            file_name: 文件名
            content: 文档内容
            chunks: 预处理的分块（可选）
            metadata: 文档元数据
        
        返回:
            添加结果
        """
        try:
            # 验证知识库是否存在
            kb = self.kb_repo.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 创建文档记录
            doc_data = {
                "id": str(uuid.uuid4()),
                "knowledge_base_id": kb_id,
                "file_name": file_name,
                "content": content,
                "status": "processing",
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            document = self.doc_repo.create(doc_data)
            
            try:
                # 如果没有提供分块，则生成分块
                if chunks is None:
                    chunks = await self._chunk_document(content, kb.embedding_model)
                
                # 为分块生成嵌入向量
                chunks_with_embeddings = await self._generate_embeddings(chunks, kb.embedding_model)
                
                # 将分块存储到数据库
                chunk_records = await self._save_document_chunks(document.id, chunks_with_embeddings)
                
                # 将向量存储到向量数据库
                vector_success = await self.kb_vector_manager.add_document_vectors(
                    kb_id=kb_id,
                    document_id=document.id,
                    chunks=chunks_with_embeddings
                )
                
                if vector_success:
                    # 更新文档状态为已完成
                    self.doc_repo.update_status(document.id, "completed")
                    
                    self.logger.info(f"文档添加成功: {file_name} (ID: {document.id})")
                    
                    return {
                        "success": True,
                        "data": {
                            "document": document,
                            "chunk_count": len(chunks_with_embeddings),
                            "vector_stored": True
                        }
                    }
                else:
                    # 向量存储失败，更新文档状态
                    self.doc_repo.update_status(document.id, "failed")
                    
                    return {
                        "success": False,
                        "error": "向量存储失败",
                        "error_code": "VECTOR_STORAGE_FAILED",
                        "data": {
                            "document": document,
                            "chunk_count": len(chunks_with_embeddings)
                        }
                    }
                    
            except Exception as e:
                # 处理失败，更新文档状态
                self.doc_repo.update_status(document.id, "failed")
                raise e
                
        except Exception as e:
            self.logger.error(f"添加文档时出错: {file_name}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"添加文档失败: {str(e)}",
                "error_code": "DOCUMENT_ADD_FAILED"
            }
    
    async def delete_document_with_vectors(self, document_id: str) -> Dict[str, Any]:
        """
        删除文档及其向量数据
        
        参数:
            document_id: 文档ID
        
        返回:
            删除结果
        """
        try:
            # 获取文档信息
            document = self.doc_repo.get_by_id(document_id)
            if not document:
                return {
                    "success": False,
                    "error": "文档不存在",
                    "error_code": "DOCUMENT_NOT_FOUND"
                }
            
            kb_id = document.knowledge_base_id
            
            # 删除向量数据
            vector_deleted = await self.kb_vector_manager.delete_document_vectors(kb_id, document_id)
            
            # 删除数据库中的文档记录（级联删除分块）
            db_deleted = self.doc_repo.delete(document_id)
            
            if vector_deleted and db_deleted:
                self.logger.info(f"文档删除成功: {document.file_name} (ID: {document_id})")
                return {
                    "success": True,
                    "data": {
                        "document_id": document_id,
                        "file_name": document.file_name
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "删除操作部分失败",
                    "error_code": "PARTIAL_DELETE_FAILED",
                    "details": {
                        "vector_deleted": vector_deleted,
                        "db_deleted": db_deleted
                    }
                }
                
        except Exception as e:
            self.logger.error(f"删除文档时出错: {document_id}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"删除文档失败: {str(e)}",
                "error_code": "DOCUMENT_DELETE_FAILED"
            }
    
    # ========== 搜索方法 ==========
    
    async def search_knowledge_base(self,
                                  kb_id: str,
                                  query: str,
                                  top_k: int = 5,
                                  similarity_threshold: float = 0.7,
                                  embedding_model: Optional[str] = None) -> Dict[str, Any]:
        """
        在知识库中搜索相关内容
        
        参数:
            kb_id: 知识库ID
            query: 查询文本
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
            embedding_model: 嵌入模型（可选）
        
        返回:
            搜索结果
        """
        try:
            # 验证知识库是否存在
            kb = self.kb_repo.get_by_id(kb_id)
            if not kb:
                return {
                    "success": False,
                    "error": "知识库不存在",
                    "error_code": "KB_NOT_FOUND"
                }
            
            # 使用知识库的嵌入模型（如果未指定）
            if not embedding_model:
                embedding_model = kb.embedding_model
            
            # 生成查询向量
            query_embedding_result = await self.vector_manager.create_embeddings(
                texts=[query],
                model=embedding_model
            )
            
            if not query_embedding_result["success"]:
                return {
                    "success": False,
                    "error": "生成查询向量失败",
                    "error_code": "QUERY_EMBEDDING_FAILED",
                    "details": query_embedding_result
                }
            
            query_vector = query_embedding_result["data"]["embeddings"][0]["embedding"]
            
            # 在向量数据库中搜索
            search_results = await self.kb_vector_manager.search_knowledge_base(
                kb_id=kb_id,
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            self.logger.info(f"知识库搜索完成: {kb_id}, 查询: {query}, 结果数: {len(search_results)}")
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": search_results,
                    "result_count": len(search_results),
                    "parameters": {
                        "kb_id": kb_id,
                        "top_k": top_k,
                        "similarity_threshold": similarity_threshold,
                        "embedding_model": embedding_model
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"知识库搜索时出错: {kb_id}, 查询: {query}, 错误: {str(e)}")
            return {
                "success": False,
                "error": f"知识库搜索失败: {str(e)}",
                "error_code": "SEARCH_FAILED"
            }
    
    # ========== 私有辅助方法 ==========
    
    async def _chunk_document(self, content: str, embedding_model: str) -> List[Dict[str, Any]]:
        """
        分割文档内容为分块
        
        参数:
            content: 文档内容
            embedding_model: 嵌入模型
        
        返回:
            分块列表
        """
        # 这里应该使用更智能的分块策略
        # 目前使用简单的固定长度分块
        chunk_size = 1000
        overlap_size = 200
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_content = content[start:end]
            
            chunks.append({
                "content": chunk_content,
                "chunk_index": chunk_index,
                "metadata": {
                    "start_pos": start,
                    "end_pos": end,
                    "length": len(chunk_content)
                }
            })
            
            start += chunk_size - overlap_size
            chunk_index += 1
        
        return chunks
    
    async def _generate_embeddings(self, chunks: List[Dict[str, Any]], embedding_model: str) -> List[Dict[str, Any]]:
        """
        为分块生成嵌入向量
        
        参数:
            chunks: 分块列表
            embedding_model: 嵌入模型
        
        返回:
            包含嵌入向量的分块列表
        """
        texts = [chunk["content"] for chunk in chunks]
        
        # 生成嵌入向量
        embedding_result = await self.vector_manager.create_embeddings(
            texts=texts,
            model=embedding_model
        )
        
        if not embedding_result["success"]:
            raise Exception(f"生成嵌入向量失败: {embedding_result['error']}")
        
        embeddings = embedding_result["data"]["embeddings"]
        
        # 将嵌入向量添加到分块中
        chunks_with_embeddings = []
        for i, chunk in enumerate(chunks):
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding["embedding"] = embeddings[i]["embedding"]
            chunks_with_embeddings.append(chunk_with_embedding)
        
        return chunks_with_embeddings
    
    async def _save_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """
        保存文档分块到数据库
        
        参数:
            document_id: 文档ID
            chunks: 分块列表
        
        返回:
            分块记录列表
        """
        chunk_data_list = []
        
        for chunk in chunks:
            chunk_data = {
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "content": chunk["content"],
                "chunk_index": chunk["chunk_index"],
                "metadata": chunk.get("metadata", {}),
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            chunk_data_list.append(chunk_data)
        
        # 批量创建分块记录
        return self.chunk_repo.bulk_create(chunk_data_list)
    
    # ========== 健康检查和维护方法 ==========
    
    async def health_check(self) -> Dict[str, Any]:
        """
        检查服务健康状态
        
        返回:
            健康状态信息
        """
        try:
            # 检查向量存储连接
            vector_health = await self.vector_store.health_check()
            
            # 检查数据库连接
            db_health = True  # 简化，实际应该检查数据库连接
            
            # 获取向量存储状态
            vector_status = self.vector_store.get_status()
            
            return {
                "success": True,
                "data": {
                    "vector_storage": {
                        "healthy": vector_health,
                        "status": vector_status,
                        "backend": self.vector_backend.value
                    },
                    "database": {
                        "healthy": db_health
                    },
                    "overall_health": vector_health and db_health
                }
            }
            
        except Exception as e:
            self.logger.error(f"健康检查时出错: {str(e)}")
            return {
                "success": False,
                "error": f"健康检查失败: {str(e)}",
                "error_code": "HEALTH_CHECK_FAILED"
            }
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self._vector_store:
                await self._vector_store.disconnect()
            self.logger.info("知识库向量服务资源清理完成")
        except Exception as e:
            self.logger.error(f"清理资源时出错: {str(e)}") 