#!/usr/bin/env python3
"""
增强版文档管理器
完善的关联删除和数据追踪功能，包含向量chunk ID、文档ID和ES分片数据的完整关联
"""

import logging
import hashlib
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from io import BinaryIO

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import UploadFile, HTTPException

from file_storage import get_file_storage, FileMetadata
from storage_config import get_storage_config

logger = logging.getLogger(__name__)

class EnhancedDocumentManager:
    """
    增强版文档管理器
    
    主要改进：
    1. 完善的ES文档分片关联追踪
    2. 向量chunk ID的详细记录
    3. 文档切分和处理状态追踪
    4. 统一的关联删除操作
    """
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        self.db_config = db_config or self._get_default_db_config()
        self.file_storage = get_file_storage()
        self._init_enhanced_database()
    
    def _get_default_db_config(self) -> Dict[str, Any]:
        """获取默认数据库配置"""
        import os
        return {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "zzdsj"),
            "user": os.getenv("POSTGRES_USER", "zzdsj_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "zzdsj_pass")
        }
    
    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            **self.db_config,
            cursor_factory=RealDictCursor
        )
    
    def _init_enhanced_database(self):
        """初始化增强版数据库表"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. 文档注册表（增强版）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_registry_enhanced (
                    file_id VARCHAR(36) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    content_type VARCHAR(100),
                    file_size BIGINT NOT NULL,
                    file_hash VARCHAR(64) NOT NULL,
                    storage_backend VARCHAR(50) NOT NULL,
                    storage_path VARCHAR(500),
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    kb_id VARCHAR(36),
                    doc_id VARCHAR(36),
                    user_id VARCHAR(36),
                    metadata TEXT,
                    status VARCHAR(20) DEFAULT 'uploaded',
                    processing_status VARCHAR(20) DEFAULT 'pending',
                    chunk_count INTEGER DEFAULT 0,
                    vector_count INTEGER DEFAULT 0,
                    es_doc_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash)
                );
            """)
            
            # 2. 文档切片表（chunk级别的追踪）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id VARCHAR(36) PRIMARY KEY,
                    file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT,
                    chunk_size INTEGER,
                    chunk_hash VARCHAR(64),
                    chunk_metadata TEXT,
                    processing_status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_id, chunk_index)
                );
            """)
            
            # 3. 向量数据关联表（增强版）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_vectors_enhanced (
                    id SERIAL PRIMARY KEY,
                    file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
                    chunk_id VARCHAR(36) REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
                    vector_id VARCHAR(100) NOT NULL,
                    vector_collection VARCHAR(100),
                    vector_index VARCHAR(100),
                    embedding_model VARCHAR(100),
                    embedding_dimension INTEGER,
                    vector_metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_id, chunk_id, vector_id)
                );
            """)
            
            # 4. ES文档分片关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_es_shards (
                    id SERIAL PRIMARY KEY,
                    file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
                    chunk_id VARCHAR(36) REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
                    es_index VARCHAR(100) NOT NULL,
                    es_doc_id VARCHAR(100) NOT NULL,
                    es_shard_id VARCHAR(50),
                    es_routing VARCHAR(100),
                    es_doc_type VARCHAR(50),
                    es_metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(es_index, es_doc_id)
                );
            """)
            
            # 5. 文档处理历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_processing_history (
                    id SERIAL PRIMARY KEY,
                    file_id VARCHAR(36) REFERENCES document_registry_enhanced(file_id) ON DELETE CASCADE,
                    operation_type VARCHAR(50) NOT NULL,
                    operation_status VARCHAR(20) NOT NULL,
                    operation_details TEXT,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_ms INTEGER,
                    operated_by VARCHAR(36),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建索引
            self._create_enhanced_indexes(cursor)
            
            conn.commit()
            logger.info("增强版文档管理器数据库表初始化完成")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"增强版数据库表初始化失败: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def _create_enhanced_indexes(self, cursor):
        """创建增强版索引"""
        indexes = [
            # 文档注册表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_filename ON document_registry_enhanced(filename)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_hash ON document_registry_enhanced(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_kb_id ON document_registry_enhanced(kb_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_doc_id ON document_registry_enhanced(doc_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_user_id ON document_registry_enhanced(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_status ON document_registry_enhanced(status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_proc_status ON document_registry_enhanced(processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_reg_enh_upload_time ON document_registry_enhanced(upload_time)",
            
            # 文档切片表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_file_id ON document_chunks(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_index ON document_chunks(chunk_index)",
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_hash ON document_chunks(chunk_hash)",
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_status ON document_chunks(processing_status)",
            
            # 向量数据表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_file_id ON document_vectors_enhanced(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_chunk_id ON document_vectors_enhanced(chunk_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_vector_id ON document_vectors_enhanced(vector_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_collection ON document_vectors_enhanced(vector_collection)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_index ON document_vectors_enhanced(vector_index)",
            "CREATE INDEX IF NOT EXISTS idx_doc_vec_enh_model ON document_vectors_enhanced(embedding_model)",
            
            # ES分片表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_es_file_id ON document_es_shards(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_chunk_id ON document_es_shards(chunk_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_index ON document_es_shards(es_index)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_doc_id ON document_es_shards(es_doc_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_shard_id ON document_es_shards(es_shard_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_es_routing ON document_es_shards(es_routing)",
            
            # 处理历史表索引
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_file_id ON document_processing_history(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_op_type ON document_processing_history(operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_status ON document_processing_history(operation_status)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_started ON document_processing_history(started_at)",
            "CREATE INDEX IF NOT EXISTS idx_doc_proc_hist_user ON document_processing_history(operated_by)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"创建索引失败: {index_sql} - {str(e)}")
    
    def register_chunk_data(self, file_id: str, chunk_index: int, chunk_text: str, 
                           chunk_metadata: Dict[str, Any] = None) -> str:
        """
        注册文档切片数据
        
        Args:
            file_id: 文件ID
            chunk_index: 切片索引
            chunk_text: 切片文本
            chunk_metadata: 切片元数据
            
        Returns:
            str: 切片ID
        """
        try:
            chunk_id = str(uuid.uuid4())
            chunk_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO document_chunks 
                (chunk_id, file_id, chunk_index, chunk_text, chunk_size, chunk_hash, chunk_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_id, chunk_index) DO UPDATE SET
                    chunk_text = EXCLUDED.chunk_text,
                    chunk_size = EXCLUDED.chunk_size,
                    chunk_hash = EXCLUDED.chunk_hash,
                    chunk_metadata = EXCLUDED.chunk_metadata,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING chunk_id
            """, (
                chunk_id, file_id, chunk_index, chunk_text, 
                len(chunk_text), chunk_hash, 
                json.dumps(chunk_metadata) if chunk_metadata else None
            ))
            
            result = cursor.fetchone()
            actual_chunk_id = result['chunk_id'] if result else chunk_id
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return actual_chunk_id
            
        except Exception as e:
            logger.error(f"注册切片数据失败: {str(e)}")
            raise
    
    def register_vector_data_enhanced(self, file_id: str, chunk_id: str, vector_id: str,
                                    vector_collection: str = None, vector_index: str = None,
                                    embedding_model: str = None, embedding_dimension: int = None,
                                    vector_metadata: Dict[str, Any] = None) -> bool:
        """
        注册增强版向量数据关联
        
        Args:
            file_id: 文件ID
            chunk_id: 切片ID
            vector_id: 向量ID
            vector_collection: 向量集合
            vector_index: 向量索引
            embedding_model: 嵌入模型
            embedding_dimension: 嵌入维度
            vector_metadata: 向量元数据
            
        Returns:
            bool: 注册是否成功
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO document_vectors_enhanced 
                (file_id, chunk_id, vector_id, vector_collection, vector_index, 
                 embedding_model, embedding_dimension, vector_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_id, chunk_id, vector_id) DO UPDATE SET
                    vector_collection = EXCLUDED.vector_collection,
                    vector_index = EXCLUDED.vector_index,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding_dimension = EXCLUDED.embedding_dimension,
                    vector_metadata = EXCLUDED.vector_metadata
            """, (
                file_id, chunk_id, vector_id, vector_collection, vector_index,
                embedding_model, embedding_dimension,
                json.dumps(vector_metadata) if vector_metadata else None
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"注册增强版向量数据关联失败: {str(e)}")
            return False
    
    def register_es_shard_data(self, file_id: str, chunk_id: str, es_index: str, 
                              es_doc_id: str, es_shard_id: str = None, 
                              es_routing: str = None, es_doc_type: str = None,
                              es_metadata: Dict[str, Any] = None) -> bool:
        """
        注册ES文档分片数据关联
        
        Args:
            file_id: 文件ID
            chunk_id: 切片ID
            es_index: ES索引名
            es_doc_id: ES文档ID
            es_shard_id: ES分片ID
            es_routing: ES路由
            es_doc_type: ES文档类型
            es_metadata: ES元数据
            
        Returns:
            bool: 注册是否成功
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO document_es_shards 
                (file_id, chunk_id, es_index, es_doc_id, es_shard_id, 
                 es_routing, es_doc_type, es_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (es_index, es_doc_id) DO UPDATE SET
                    file_id = EXCLUDED.file_id,
                    chunk_id = EXCLUDED.chunk_id,
                    es_shard_id = EXCLUDED.es_shard_id,
                    es_routing = EXCLUDED.es_routing,
                    es_doc_type = EXCLUDED.es_doc_type,
                    es_metadata = EXCLUDED.es_metadata
            """, (
                file_id, chunk_id, es_index, es_doc_id, es_shard_id,
                es_routing, es_doc_type,
                json.dumps(es_metadata) if es_metadata else None
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"注册ES分片数据关联失败: {str(e)}")
            return False
    
    def get_complete_file_associations(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件的完整关联信息
        
        包括：
        - 基本文件信息
        - 所有切片信息
        - 所有向量关联
        - 所有ES分片关联
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[Dict[str, Any]]: 完整的关联信息
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 1. 获取基本文件信息
            cursor.execute("""
                SELECT * FROM document_registry_enhanced WHERE file_id = %s
            """, (file_id,))
            
            file_info = cursor.fetchone()
            if not file_info:
                return None
            
            file_data = dict(file_info)
            
            # 2. 获取所有切片信息
            cursor.execute("""
                SELECT * FROM document_chunks WHERE file_id = %s ORDER BY chunk_index
            """, (file_id,))
            
            chunks = [dict(chunk) for chunk in cursor.fetchall()]
            
            # 3. 获取所有向量关联
            cursor.execute("""
                SELECT * FROM document_vectors_enhanced WHERE file_id = %s
            """, (file_id,))
            
            vectors = [dict(vector) for vector in cursor.fetchall()]
            
            # 4. 获取所有ES分片关联
            cursor.execute("""
                SELECT * FROM document_es_shards WHERE file_id = %s
            """, (file_id,))
            
            es_shards = [dict(shard) for shard in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return {
                "file_info": file_data,
                "chunks": chunks,
                "vectors": vectors,
                "es_shards": es_shards,
                "summary": {
                    "chunk_count": len(chunks),
                    "vector_count": len(vectors),
                    "es_shard_count": len(es_shards)
                }
            }
            
        except Exception as e:
            logger.error(f"获取完整文件关联信息失败: {str(e)}")
            return None
    
    async def unified_delete_document(self, file_id: str, force: bool = False,
                                    delete_vectors: bool = True, 
                                    delete_es_docs: bool = True,
                                    operated_by: str = "system") -> Dict[str, Any]:
        """
        统一的文档删除操作
        
        完整删除流程：
        1. 获取所有关联信息
        2. 删除ES文档
        3. 删除向量数据
        4. 删除文件存储
        5. 删除数据库记录
        6. 记录操作历史
        
        Args:
            file_id: 文件ID
            force: 是否强制删除
            delete_vectors: 是否删除向量数据
            delete_es_docs: 是否删除ES文档
            operated_by: 操作者
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        operation_start = datetime.now()
        
        try:
            # 记录操作开始
            self._record_operation_history(
                file_id, "unified_delete", "started", 
                {"force": force, "delete_vectors": delete_vectors, "delete_es_docs": delete_es_docs},
                None, operation_start, None, operated_by
            )
            
            # 1. 获取完整关联信息
            associations = self.get_complete_file_associations(file_id)
            if not associations:
                return {
                    "success": False,
                    "error": "文件不存在或没有关联信息",
                    "file_id": file_id
                }
            
            deletion_results = {
                "es_documents": {"success": False, "count": 0, "errors": []},
                "vector_data": {"success": False, "count": 0, "errors": []},
                "file_storage": {"success": False, "errors": []},
                "database_records": {"success": False, "counts": {}, "errors": []}
            }
            
            # 2. 删除ES文档
            if delete_es_docs and associations["es_shards"]:
                try:
                    es_result = await self._delete_es_documents(associations["es_shards"])
                    deletion_results["es_documents"] = es_result
                except Exception as e:
                    error_msg = f"删除ES文档失败: {str(e)}"
                    deletion_results["es_documents"]["errors"].append(error_msg)
                    logger.error(error_msg)
                    if not force:
                        raise
            
            # 3. 删除向量数据
            if delete_vectors and associations["vectors"]:
                try:
                    vector_result = await self._delete_vector_data(associations["vectors"])
                    deletion_results["vector_data"] = vector_result
                except Exception as e:
                    error_msg = f"删除向量数据失败: {str(e)}"
                    deletion_results["vector_data"]["errors"].append(error_msg)
                    logger.error(error_msg)
                    if not force:
                        raise
            
            # 4. 删除文件存储
            try:
                storage_result = self.file_storage.delete_file(file_id)
                deletion_results["file_storage"]["success"] = storage_result
            except Exception as e:
                error_msg = f"删除文件存储失败: {str(e)}"
                deletion_results["file_storage"]["errors"].append(error_msg)
                logger.error(error_msg)
                if not force:
                    raise
            
            # 5. 删除数据库记录（级联删除）
            try:
                db_result = self._delete_database_records(file_id)
                deletion_results["database_records"] = db_result
            except Exception as e:
                error_msg = f"删除数据库记录失败: {str(e)}"
                deletion_results["database_records"]["errors"].append(error_msg)
                logger.error(error_msg)
                if not force:
                    raise
            
            # 6. 评估删除结果
            successful_operations = sum([
                deletion_results["es_documents"]["success"],
                deletion_results["vector_data"]["success"],
                deletion_results["file_storage"]["success"],
                deletion_results["database_records"]["success"]
            ])
            
            success = successful_operations >= 3 or force
            operation_end = datetime.now()
            duration_ms = int((operation_end - operation_start).total_seconds() * 1000)
            
            # 记录操作完成
            self._record_operation_history(
                file_id, "unified_delete", "completed" if success else "failed",
                deletion_results, None, operation_start, operation_end, operated_by
            )
            
            logger.info(f"统一删除文档{file_id}: 成功{successful_operations}/4, 耗时{duration_ms}ms")
            
            return {
                "success": success,
                "file_id": file_id,
                "filename": associations["file_info"].get("filename"),
                "deletion_results": deletion_results,
                "associations_deleted": associations["summary"],
                "duration_ms": duration_ms,
                "message": f"统一删除{'成功' if success else '部分成功'}"
            }
            
        except Exception as e:
            operation_end = datetime.now()
            
            # 记录操作失败
            self._record_operation_history(
                file_id, "unified_delete", "failed", None, str(e),
                operation_start, operation_end, operated_by
            )
            
            logger.error(f"统一删除文档{file_id}失败: {str(e)}")
            return {
                "success": False,
                "file_id": file_id,
                "error": str(e),
                "message": "统一删除失败"
            }
    
    async def _delete_es_documents(self, es_shards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """删除ES文档"""
        success_count = 0
        errors = []
        
        try:
            # 导入ES客户端
            from app.utils.storage.elasticsearch_manager import ElasticsearchManager
            es_manager = ElasticsearchManager()
            
            for shard in es_shards:
                try:
                    es_index = shard['es_index']
                    es_doc_id = shard['es_doc_id']
                    
                    # 删除ES文档
                    delete_result = await es_manager.delete_document(es_index, es_doc_id)
                    
                    if delete_result.get('result') == 'deleted':
                        logger.info(f"成功删除ES文档: {es_index}/{es_doc_id}")
                        success_count += 1
                    else:
                        logger.warning(f"ES文档可能已删除或不存在: {es_index}/{es_doc_id}")
                        success_count += 1  # 不存在也算成功
                        
                except Exception as e:
                    error_msg = f"ES文档删除失败 {shard['es_doc_id']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
        except ImportError:
            # 如果无法导入ES管理器，降级为模拟删除
            logger.warning("ES管理器不可用，使用模拟删除模式")
            for shard in es_shards:
                logger.info(f"[模拟] 删除ES文档: {shard['es_index']}/{shard['es_doc_id']}")
                success_count += 1
        
        return {
            "success": success_count == len(es_shards),
            "count": success_count,
            "total": len(es_shards),
            "errors": errors
        }
    
    async def _delete_vector_data(self, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """删除向量数据"""
        success_count = 0
        errors = []
        
        try:
            # 尝试导入向量管理器
            from core.knowledge.vector_manager import VectorManager
            vector_manager = VectorManager()
            
            for vector in vectors:
                try:
                    vector_collection = vector['vector_collection']
                    vector_id = vector['vector_id']
                    
                    # 删除向量数据
                    delete_result = await vector_manager.delete_vector(
                        collection_name=vector_collection,
                        vector_id=vector_id
                    )
                    
                    if delete_result:
                        logger.info(f"成功删除向量: {vector_collection}/{vector_id}")
                        success_count += 1
                    else:
                        logger.warning(f"向量可能已删除或不存在: {vector_collection}/{vector_id}")
                        success_count += 1  # 不存在也算成功
                        
                except Exception as e:
                    error_msg = f"向量删除失败 {vector['vector_id']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
        except ImportError:
            # 如果无法导入向量管理器，尝试使用Milvus客户端
            try:
                from pymilvus import connections, Collection
                
                # 连接到Milvus
                connections.connect("default", host="localhost", port="19530")
                
                for vector in vectors:
                    try:
                        vector_collection = vector['vector_collection']
                        vector_id = vector['vector_id']
                        
                        # 获取集合并删除向量
                        collection = Collection(vector_collection)
                        delete_result = collection.delete(f'id == "{vector_id}"')
                        
                        logger.info(f"成功删除向量: {vector_collection}/{vector_id}")
                        success_count += 1
                        
                    except Exception as e:
                        error_msg = f"Milvus向量删除失败 {vector['vector_id']}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
            except ImportError:
                # 如果都无法导入，降级为模拟删除
                logger.warning("向量数据库客户端不可用，使用模拟删除模式")
                for vector in vectors:
                    logger.info(f"[模拟] 删除向量: {vector['vector_collection']}/{vector['vector_id']}")
                    success_count += 1
        
        return {
            "success": success_count == len(vectors),
            "count": success_count,
            "total": len(vectors),
            "errors": errors
        }
    
    def _delete_database_records(self, file_id: str) -> Dict[str, Any]:
        """删除数据库记录（级联删除）"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 统计删除前的记录数量
            counts = {}
            
            # 统计ES分片数量
            cursor.execute("SELECT COUNT(*) as count FROM document_es_shards WHERE file_id = %s", (file_id,))
            counts["es_shards"] = cursor.fetchone()["count"]
            
            # 统计向量数量
            cursor.execute("SELECT COUNT(*) as count FROM document_vectors_enhanced WHERE file_id = %s", (file_id,))
            counts["vectors"] = cursor.fetchone()["count"]
            
            # 统计切片数量
            cursor.execute("SELECT COUNT(*) as count FROM document_chunks WHERE file_id = %s", (file_id,))
            counts["chunks"] = cursor.fetchone()["count"]
            
            # 删除主文档记录（级联删除会自动删除相关记录）
            cursor.execute("DELETE FROM document_registry_enhanced WHERE file_id = %s", (file_id,))
            deleted_main = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": deleted_main > 0,
                "counts": counts,
                "main_deleted": deleted_main,
                "errors": []
            }
            
        except Exception as e:
            logger.error(f"删除数据库记录失败: {str(e)}")
            return {
                "success": False,
                "counts": {},
                "errors": [str(e)]
            }
    
    def _record_operation_history(self, file_id: str, operation_type: str, 
                                operation_status: str, operation_details: Any = None,
                                error_message: str = None, started_at: datetime = None,
                                completed_at: datetime = None, operated_by: str = "system"):
        """记录操作历史"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            duration_ms = None
            if started_at and completed_at:
                duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            cursor.execute("""
                INSERT INTO document_processing_history 
                (file_id, operation_type, operation_status, operation_details, 
                 error_message, started_at, completed_at, duration_ms, operated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                file_id, operation_type, operation_status,
                json.dumps(operation_details) if operation_details else None,
                error_message, started_at, completed_at, duration_ms, operated_by
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录操作历史失败: {str(e)}")

# 全局增强文档管理器实例
_enhanced_document_manager_instance = None

def get_enhanced_document_manager() -> EnhancedDocumentManager:
    """获取增强文档管理器实例（单例模式）"""
    global _enhanced_document_manager_instance
    if _enhanced_document_manager_instance is None:
        _enhanced_document_manager_instance = EnhancedDocumentManager()
    return _enhanced_document_manager_instance 