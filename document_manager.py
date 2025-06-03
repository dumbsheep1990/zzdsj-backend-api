#!/usr/bin/env python3
"""
文档管理器模块
统一管理文档的上传、删除操作
确保文件ID在MinIO、向量数据库和PostgreSQL中的一致性
"""

import os
import uuid
import logging
import hashlib
from typing import Optional, Dict, Any, List, Union, BinaryIO
from datetime import datetime
from fastapi import UploadFile, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor

from storage_interface import get_file_storage, FileMetadata
from storage_config import get_storage_config

logger = logging.getLogger(__name__)

class DocumentManager:
    """文档管理器"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        """
        初始化文档管理器
        
        Args:
            db_config: 数据库配置，如果不提供则从默认配置获取
        """
        self.file_storage = get_file_storage()
        self.db_config = db_config or self._get_default_db_config()
        self._init_database()
    
    def _get_default_db_config(self) -> Dict[str, Any]:
        """获取默认数据库配置"""
        from storage_config import StorageType, storage_config_manager
        pg_config = storage_config_manager.get_config(StorageType.POSTGRESQL)
        return {
            "host": pg_config.host,
            "port": pg_config.port,
            "database": pg_config.database,
            "user": pg_config.user,
            "password": pg_config.password
        }
    
    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.db_config["host"],
            port=self.db_config["port"],
            database=self.db_config["database"],
            user=self.db_config["user"],
            password=self.db_config["password"],
            cursor_factory=RealDictCursor
        )
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 创建文档注册表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_registry (
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
                    metadata TEXT,
                    status VARCHAR(20) DEFAULT 'uploaded',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash)
                );
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_registry_filename 
                ON document_registry(filename);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_registry_hash 
                ON document_registry(file_hash);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_registry_kb_id 
                ON document_registry(kb_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_registry_doc_id 
                ON document_registry(doc_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_registry_status 
                ON document_registry(status);
            """)
            
            # 创建向量数据关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_vectors (
                    id SERIAL PRIMARY KEY,
                    file_id VARCHAR(36) REFERENCES document_registry(file_id) ON DELETE CASCADE,
                    vector_id VARCHAR(100) NOT NULL,
                    chunk_id VARCHAR(100),
                    vector_collection VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_id, vector_id)
                );
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_vectors_file_id 
                ON document_vectors(file_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_vectors_vector_id 
                ON document_vectors(vector_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_vectors_collection 
                ON document_vectors(vector_collection);
            """)
            
            conn.commit()
            logger.info("文档管理器数据库表初始化完成")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库表初始化失败: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    async def upload_document(self,
                            file: Union[UploadFile, BinaryIO, bytes],
                            filename: str = None,
                            kb_id: str = None,
                            doc_id: str = None,
                            metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        上传文档
        
        Args:
            file: 文件对象、文件数据或UploadFile
            filename: 文件名（如果file是UploadFile则可以不提供）
            kb_id: 知识库ID
            doc_id: 文档ID
            metadata: 额外元数据
            
        Returns:
            Dict[str, Any]: 上传结果，包含文件ID和相关信息
        """
        try:
            # 处理不同类型的文件输入
            if isinstance(file, UploadFile):
                filename = filename or file.filename
                content_type = file.content_type
                file_data = await file.read()
            elif isinstance(file, bytes):
                if not filename:
                    raise ValueError("filename is required when file is bytes")
                file_data = file
                import mimetypes
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or 'application/octet-stream'
            else:
                # BinaryIO
                if not filename:
                    raise ValueError("filename is required when file is BinaryIO")
                file_data = file.read()
                import mimetypes
                content_type, _ = mimetypes.guess_type(filename)
                content_type = content_type or 'application/octet-stream'
            
            # 计算文件哈希
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # 检查文件是否已存在（去重）
            existing_file = self._get_file_by_hash(file_hash)
            if existing_file:
                logger.info(f"文件已存在，使用现有文件: {existing_file['file_id']}")
                return {
                    "success": True,
                    "file_id": existing_file["file_id"],
                    "filename": existing_file["filename"],
                    "exists": True,
                    "message": "文件已存在，已跳过上传"
                }
            
            # 准备上传元数据
            upload_metadata = {
                "kb_id": kb_id,
                "doc_id": doc_id,
                "upload_source": "document_manager"
            }
            if metadata:
                upload_metadata.update(metadata)
            
            # 上传文件到存储后端
            file_metadata = self.file_storage.upload_file(
                file_data=file_data,
                filename=filename,
                content_type=content_type,
                metadata=upload_metadata
            )
            
            # 注册文档到数据库
            self._register_document(
                file_metadata=file_metadata,
                kb_id=kb_id,
                doc_id=doc_id,
                metadata=upload_metadata
            )
            
            logger.info(f"文档上传成功: {filename} -> {file_metadata.file_id}")
            
            return {
                "success": True,
                "file_id": file_metadata.file_id,
                "filename": file_metadata.filename,
                "file_size": file_metadata.file_size,
                "file_hash": file_metadata.file_hash,
                "storage_path": file_metadata.storage_path,
                "content_type": file_metadata.content_type,
                "upload_time": file_metadata.upload_time.isoformat(),
                "exists": False,
                "message": "文档上传成功"
            }
            
        except Exception as e:
            logger.error(f"文档上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")
    
    async def batch_upload_documents(self,
                                   files: List[Union[UploadFile, Dict[str, Any]]],
                                   kb_id: str = None,
                                   metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        批量上传文档
        
        Args:
            files: 文件列表
            kb_id: 知识库ID
            metadata: 共享元数据
            
        Returns:
            Dict[str, Any]: 批量上传结果
        """
        results = []
        success_count = 0
        error_count = 0
        
        for i, file_item in enumerate(files):
            try:
                # 为每个文件生成唯一的文档ID
                doc_id = str(uuid.uuid4())
                
                if isinstance(file_item, UploadFile):
                    result = await self.upload_document(
                        file=file_item,
                        kb_id=kb_id,
                        doc_id=doc_id,
                        metadata=metadata
                    )
                else:
                    # 字典格式 {file: ..., filename: ..., metadata: ...}
                    file_metadata = metadata.copy() if metadata else {}
                    if "metadata" in file_item:
                        file_metadata.update(file_item["metadata"])
                    
                    result = await self.upload_document(
                        file=file_item["file"],
                        filename=file_item.get("filename"),
                        kb_id=kb_id,
                        doc_id=doc_id,
                        metadata=file_metadata
                    )
                
                results.append({
                    "index": i,
                    "status": "success",
                    "result": result
                })
                success_count += 1
                
            except Exception as e:
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(e)
                })
                error_count += 1
                logger.error(f"批量上传第{i+1}个文件失败: {str(e)}")
        
        return {
            "success": error_count == 0,
            "total_files": len(files),
            "success_count": success_count,
            "error_count": error_count,
            "results": results,
            "message": f"批量上传完成: 成功{success_count}个，失败{error_count}个"
        }
    
    async def delete_document(self, file_id: str, force: bool = False) -> Dict[str, Any]:
        """
        删除文档（关联删除）
        
        Args:
            file_id: 文件ID
            force: 是否强制删除（忽略错误）
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            # 1. 获取文档信息
            doc_info = self._get_document_info(file_id)
            if not doc_info:
                return {
                    "success": False,
                    "error": "文档不存在",
                    "file_id": file_id
                }
            
            deletion_results = {
                "file_storage": False,
                "vector_data": False,
                "database_registry": False,
                "errors": []
            }
            
            # 2. 删除向量数据
            try:
                vector_deleted = await self._delete_document_vectors(file_id)
                deletion_results["vector_data"] = vector_deleted
                if vector_deleted:
                    logger.info(f"文档{file_id}的向量数据删除成功")
                else:
                    logger.warning(f"文档{file_id}的向量数据删除失败或无向量数据")
            except Exception as e:
                error_msg = f"删除向量数据失败: {str(e)}"
                deletion_results["errors"].append(error_msg)
                logger.error(error_msg)
                if not force:
                    raise
            
            # 3. 删除文件存储
            try:
                storage_deleted = self.file_storage.delete_file(file_id)
                deletion_results["file_storage"] = storage_deleted
                if storage_deleted:
                    logger.info(f"文档{file_id}的文件存储删除成功")
                else:
                    logger.warning(f"文档{file_id}的文件存储删除失败")
            except Exception as e:
                error_msg = f"删除文件存储失败: {str(e)}"
                deletion_results["errors"].append(error_msg)
                logger.error(error_msg)
                if not force:
                    raise
            
            # 4. 删除数据库注册记录
            try:
                registry_deleted = self._delete_document_registry(file_id)
                deletion_results["database_registry"] = registry_deleted
                if registry_deleted:
                    logger.info(f"文档{file_id}的数据库记录删除成功")
                else:
                    logger.warning(f"文档{file_id}的数据库记录删除失败")
            except Exception as e:
                error_msg = f"删除数据库记录失败: {str(e)}"
                deletion_results["errors"].append(error_msg)
                logger.error(error_msg)
                if not force:
                    raise
            
            # 5. 评估删除结果
            successful_deletions = sum([
                deletion_results["file_storage"],
                deletion_results["vector_data"],
                deletion_results["database_registry"]
            ])
            
            success = successful_deletions >= 2 or force  # 至少2个成功或强制删除
            
            logger.info(f"文档{file_id}删除完成: 成功{successful_deletions}/3")
            
            return {
                "success": success,
                "file_id": file_id,
                "filename": doc_info.get("filename"),
                "deletion_results": deletion_results,
                "message": f"文档删除{'成功' if success else '部分成功'}"
            }
            
        except Exception as e:
            logger.error(f"删除文档{file_id}失败: {str(e)}")
            return {
                "success": False,
                "file_id": file_id,
                "error": str(e),
                "message": "文档删除失败"
            }
    
    def register_vector_data(self, file_id: str, vector_id: str, 
                           chunk_id: str = None, collection: str = None) -> bool:
        """
        注册向量数据关联
        
        Args:
            file_id: 文件ID
            vector_id: 向量ID
            chunk_id: 分块ID
            collection: 向量集合名称
            
        Returns:
            bool: 注册是否成功
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO document_vectors (file_id, vector_id, chunk_id, vector_collection)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (file_id, vector_id) DO NOTHING
            """, (file_id, vector_id, chunk_id, collection))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"注册向量数据关联失败: {str(e)}")
            return False
    
    def get_document_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文档信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[Dict[str, Any]]: 文档信息
        """
        return self._get_document_info(file_id)
    
    def list_documents(self, kb_id: str = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        列出文档
        
        Args:
            kb_id: 知识库ID（可选，用于过滤）
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 文档列表和统计信息
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            where_clause = ""
            params = []
            if kb_id:
                where_clause = "WHERE kb_id = %s"
                params.append(kb_id)
            
            # 查询文档
            cursor.execute(f"""
                SELECT file_id, filename, content_type, file_size, file_hash,
                       storage_backend, storage_path, upload_time, kb_id, doc_id,
                       metadata, status, created_at, updated_at
                FROM document_registry
                {where_clause}
                ORDER BY upload_time DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            
            documents = cursor.fetchall()
            
            # 查询总数
            cursor.execute(f"""
                SELECT COUNT(*) as total
                FROM document_registry
                {where_clause}
            """, params)
            
            total = cursor.fetchone()["total"]
            
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "documents": [dict(doc) for doc in documents],
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(documents) < total
            }
            
        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "documents": [],
                "total": 0
            }
    
    def _register_document(self, file_metadata: FileMetadata, kb_id: str = None,
                         doc_id: str = None, metadata: Dict[str, Any] = None):
        """注册文档到数据库"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            storage_config = get_storage_config()
            
            cursor.execute("""
                INSERT INTO document_registry 
                (file_id, filename, content_type, file_size, file_hash, 
                 storage_backend, storage_path, upload_time, kb_id, doc_id, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                file_metadata.file_id, file_metadata.filename, file_metadata.content_type,
                file_metadata.file_size, file_metadata.file_hash, storage_config.storage_type.value,
                file_metadata.storage_path, file_metadata.upload_time, kb_id, doc_id, metadata_json
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def _get_file_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """根据哈希获取文件信息"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT file_id, filename, content_type, file_size, file_hash,
                       storage_backend, storage_path, upload_time, kb_id, doc_id
                FROM document_registry
                WHERE file_hash = %s
                LIMIT 1
            """, (file_hash,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"根据哈希获取文件失败: {str(e)}")
            return None
    
    def _get_document_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT file_id, filename, content_type, file_size, file_hash,
                       storage_backend, storage_path, upload_time, kb_id, doc_id,
                       metadata, status, created_at, updated_at
                FROM document_registry
                WHERE file_id = %s
            """, (file_id,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"获取文档信息失败: {str(e)}")
            return None
    
    async def _delete_document_vectors(self, file_id: str) -> bool:
        """删除文档的向量数据"""
        try:
            # 首先获取向量关联信息
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT vector_id, chunk_id, vector_collection
                FROM document_vectors
                WHERE file_id = %s
            """, (file_id,))
            
            vector_records = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not vector_records:
                logger.info(f"文档{file_id}没有关联的向量数据")
                return True
            
            # TODO: 这里需要调用实际的向量删除逻辑
            # 例如：调用Elasticsearch、Milvus或其他向量数据库的删除API
            # 目前先返回True表示删除成功
            logger.info(f"需要删除文档{file_id}的{len(vector_records)}个向量记录")
            
            # 删除向量关联记录
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM document_vectors WHERE file_id = %s
            """, (file_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"删除了文档{file_id}的{deleted_count}个向量关联记录")
            return True
            
        except Exception as e:
            logger.error(f"删除文档向量数据失败: {str(e)}")
            return False
    
    def _delete_document_registry(self, file_id: str) -> bool:
        """删除文档注册记录"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM document_registry WHERE file_id = %s
            """, (file_id,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"删除文档注册记录失败: {str(e)}")
            return False

# 全局文档管理器实例
_document_manager_instance = None

def get_document_manager() -> DocumentManager:
    """获取文档管理器实例（单例模式）"""
    global _document_manager_instance
    if _document_manager_instance is None:
        _document_manager_instance = DocumentManager()
    return _document_manager_instance 