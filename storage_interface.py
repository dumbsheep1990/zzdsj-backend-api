#!/usr/bin/env python3
"""
通用文件存储接口
支持PostgreSQL、Elasticsearch、MinIO等多种存储后端
"""

import os
import uuid
import hashlib
import mimetypes
import io
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, BinaryIO, List
from dataclasses import dataclass
import psycopg2
from elasticsearch import Elasticsearch
import base64

from storage_config import StorageType, get_storage_config

# MinIO imports with fallback
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    # Fallback classes to avoid NameError
    class Minio:
        pass
    class S3Error(Exception):
        pass

@dataclass
class FileMetadata:
    """文件元数据"""
    file_id: str
    filename: str
    content_type: str
    file_size: int
    file_hash: str
    upload_time: datetime
    storage_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FileStorageInterface(ABC):
    """文件存储接口"""
    
    @abstractmethod
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None, metadata: Dict[str, Any] = None) -> FileMetadata:
        """上传文件"""
        pass
    
    @abstractmethod
    def download_file(self, file_id: str) -> Optional[bytes]:
        """下载文件"""
        pass
    
    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        pass
    
    @abstractmethod
    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileMetadata]:
        """列出文件"""
        pass

class PostgreSQLFileStorage(FileStorageInterface):
    """PostgreSQL文件存储实现"""
    
    def __init__(self, config):
        self.config = config
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password
        )
        
        cursor = conn.cursor()
        # 创建文件存储表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_storage (
                file_id VARCHAR(36) PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                content_type VARCHAR(100),
                file_size BIGINT NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                file_data BYTEA NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            );
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_storage_filename 
            ON file_storage(filename);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_storage_hash 
            ON file_storage(file_hash);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_storage_upload_time 
            ON file_storage(upload_time);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password
        )
    
    def _calculate_hash(self, data: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(data).hexdigest()
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None, metadata: Dict[str, Any] = None) -> FileMetadata:
        """上传文件到PostgreSQL"""
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        file_id = str(uuid.uuid4())
        file_hash = self._calculate_hash(file_data)
        file_size = len(file_data)
        upload_time = datetime.now()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 确保metadata是JSON兼容的
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO file_storage (file_id, filename, content_type, file_size, file_hash, file_data, upload_time, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (file_id, filename, content_type, file_size, file_hash, file_data, upload_time, metadata_json))
            
            conn.commit()
            
            return FileMetadata(
                file_id=file_id,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                file_hash=file_hash,
                upload_time=upload_time,
                metadata=metadata
            )
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """从PostgreSQL下载文件"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT file_data FROM file_storage WHERE file_id = %s", (file_id,))
            result = cursor.fetchone()
            if result:
                file_data = result[0]
                # PostgreSQL bytea类型可能返回memoryview，需要转换为bytes
                if isinstance(file_data, memoryview):
                    return file_data.tobytes()
                elif isinstance(file_data, bytes):
                    return file_data
                else:
                    # 如果是其他类型，尝试转换
                    return bytes(file_data)
            return None
            
        finally:
            cursor.close()
            conn.close()
    
    def delete_file(self, file_id: str) -> bool:
        """从PostgreSQL删除文件"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM file_storage WHERE file_id = %s", (file_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
            
        except Exception as e:
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT file_id, filename, content_type, file_size, file_hash, upload_time, metadata
                FROM file_storage WHERE file_id = %s
            """, (file_id,))
            
            result = cursor.fetchone()
            if result:
                import json
                # 安全地解析JSON元数据
                metadata = None
                if result[6]:
                    try:
                        if isinstance(result[6], str):
                            metadata = json.loads(result[6])
                        elif isinstance(result[6], dict):
                            metadata = result[6]
                    except (json.JSONDecodeError, TypeError):
                        metadata = None
                
                return FileMetadata(
                    file_id=result[0],
                    filename=result[1],
                    content_type=result[2],
                    file_size=result[3],
                    file_hash=result[4],
                    upload_time=result[5],
                    metadata=metadata
                )
            return None
            
        finally:
            cursor.close()
            conn.close()
    
    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileMetadata]:
        """列出文件"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT file_id, filename, content_type, file_size, file_hash, upload_time, metadata
                FROM file_storage ORDER BY upload_time DESC LIMIT %s OFFSET %s
            """, (limit, offset))
            
            results = cursor.fetchall()
            import json
            
            files = []
            for row in results:
                # 安全地解析JSON元数据
                metadata = None
                if row[6]:
                    try:
                        if isinstance(row[6], str):
                            metadata = json.loads(row[6])
                        elif isinstance(row[6], dict):
                            metadata = row[6]
                    except (json.JSONDecodeError, TypeError):
                        metadata = None
                
                files.append(FileMetadata(
                    file_id=row[0],
                    filename=row[1],
                    content_type=row[2],
                    file_size=row[3],
                    file_hash=row[4],
                    upload_time=row[5],
                    metadata=metadata
                ))
            
            return files
            
        finally:
            cursor.close()
            conn.close()

class ElasticsearchFileStorage(FileStorageInterface):
    """Elasticsearch文件存储实现"""
    
    def __init__(self, config):
        self.config = config
        self.client = self._get_client()
        self._init_index()
    
    def _get_client(self):
        """获取Elasticsearch客户端"""
        auth = None
        if self.config.username and self.config.password:
            auth = (self.config.username, self.config.password)
        
        return Elasticsearch(
            hosts=self.config.hosts,
            http_auth=auth,
            use_ssl=self.config.use_ssl,
            verify_certs=self.config.use_ssl
        )
    
    def _init_index(self):
        """初始化索引"""
        if not self.client.indices.exists(index=self.config.index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "filename": {"type": "text", "analyzer": "standard"},
                        "content_type": {"type": "keyword"},
                        "file_size": {"type": "long"},
                        "file_hash": {"type": "keyword"},
                        "file_data": {"type": "binary"},
                        "upload_time": {"type": "date"},
                        "metadata": {"type": "object", "enabled": False}
                    }
                }
            }
            self.client.indices.create(index=self.config.index_name, body=mapping)
    
    def _calculate_hash(self, data: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(data).hexdigest()
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None, metadata: Dict[str, Any] = None) -> FileMetadata:
        """上传文件到Elasticsearch"""
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        file_id = str(uuid.uuid4())
        file_hash = self._calculate_hash(file_data)
        file_size = len(file_data)
        upload_time = datetime.now()
        
        # 将文件数据编码为base64
        file_data_b64 = base64.b64encode(file_data).decode('utf-8')
        
        doc = {
            "filename": filename,
            "content_type": content_type,
            "file_size": file_size,
            "file_hash": file_hash,
            "file_data": file_data_b64,
            "upload_time": upload_time.isoformat(),
            "metadata": metadata or {}
        }
        
        self.client.index(index=self.config.index_name, id=file_id, body=doc)
        
        return FileMetadata(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            file_hash=file_hash,
            upload_time=upload_time,
            metadata=metadata
        )
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """从Elasticsearch下载文件"""
        try:
            response = self.client.get(index=self.config.index_name, id=file_id)
            file_data_b64 = response['_source']['file_data']
            return base64.b64decode(file_data_b64.encode('utf-8'))
        except Exception:
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """从Elasticsearch删除文件"""
        try:
            self.client.delete(index=self.config.index_name, id=file_id)
            return True
        except Exception:
            return False
    
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        try:
            response = self.client.get(index=self.config.index_name, id=file_id)
            source = response['_source']
            
            return FileMetadata(
                file_id=file_id,
                filename=source['filename'],
                content_type=source['content_type'],
                file_size=source['file_size'],
                file_hash=source['file_hash'],
                upload_time=datetime.fromisoformat(source['upload_time'].replace('Z', '+00:00')),
                metadata=source.get('metadata')
            )
        except Exception:
            return None
    
    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileMetadata]:
        """列出文件"""
        query = {
            "query": {"match_all": {}},
            "sort": [{"upload_time": {"order": "desc"}}],
            "size": limit,
            "from": offset,
            "_source": {
                "excludes": ["file_data"]  # 不返回文件数据
            }
        }
        
        try:
            response = self.client.search(index=self.config.index_name, body=query)
            results = []
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append(FileMetadata(
                    file_id=hit['_id'],
                    filename=source['filename'],
                    content_type=source['content_type'],
                    file_size=source['file_size'],
                    file_hash=source['file_hash'],
                    upload_time=datetime.fromisoformat(source['upload_time'].replace('Z', '+00:00')),
                    metadata=source.get('metadata')
                ))
            
            return results
        except Exception:
            return []

class LocalFileStorage(FileStorageInterface):
    """本地文件存储实现"""
    
    def __init__(self, config):
        self.config = config
        self.base_path = config.base_path
        os.makedirs(self.base_path, exist_ok=True)
        self._init_metadata_store()
    
    def _init_metadata_store(self):
        """初始化元数据存储"""
        # 使用SQLite存储元数据
        import sqlite3
        self.db_path = os.path.join(self.base_path, 'metadata.db')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content_type TEXT,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def _calculate_hash(self, data: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(data).hexdigest()
    
    def _get_storage_path(self, file_id: str, filename: str) -> str:
        """获取存储路径"""
        if self.config.create_date_folders:
            date_folder = datetime.now().strftime("%Y/%m/%d")
            folder_path = os.path.join(self.base_path, date_folder)
            os.makedirs(folder_path, exist_ok=True)
            return os.path.join(folder_path, f"{file_id}_{filename}")
        else:
            return os.path.join(self.base_path, f"{file_id}_{filename}")
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None, metadata: Dict[str, Any] = None) -> FileMetadata:
        """上传文件到本地存储"""
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        file_id = str(uuid.uuid4())
        file_hash = self._calculate_hash(file_data)
        file_size = len(file_data)
        upload_time = datetime.now()
        storage_path = self._get_storage_path(file_id, filename)
        
        # 写入文件
        with open(storage_path, 'wb') as f:
            f.write(file_data)
        
        # 保存元数据
        import sqlite3
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO file_metadata (file_id, filename, content_type, file_size, file_hash, storage_path, upload_time, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_id, filename, content_type, file_size, file_hash, storage_path, upload_time.isoformat(), json.dumps(metadata) if metadata else None))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return FileMetadata(
            file_id=file_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            file_hash=file_hash,
            upload_time=upload_time,
            storage_path=storage_path,
            metadata=metadata
        )
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """从本地存储下载文件"""
        metadata = self.get_file_metadata(file_id)
        if not metadata or not metadata.storage_path:
            return None
        
        try:
            with open(metadata.storage_path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """从本地存储删除文件"""
        import sqlite3
        
        metadata = self.get_file_metadata(file_id)
        if not metadata:
            return False
        
        try:
            # 删除文件
            if metadata.storage_path and os.path.exists(metadata.storage_path):
                os.remove(metadata.storage_path)
            
            # 删除元数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM file_metadata WHERE file_id = ?", (file_id,))
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        except Exception:
            return False
    
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        import sqlite3
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_id, filename, content_type, file_size, file_hash, storage_path, upload_time, metadata
            FROM file_metadata WHERE file_id = ?
        """, (file_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return FileMetadata(
                file_id=result[0],
                filename=result[1],
                content_type=result[2],
                file_size=result[3],
                file_hash=result[4],
                upload_time=datetime.fromisoformat(result[6]),
                storage_path=result[5],
                metadata=json.loads(result[7]) if result[7] else None
            )
        return None
    
    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileMetadata]:
        """列出文件"""
        import sqlite3
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_id, filename, content_type, file_size, file_hash, storage_path, upload_time, metadata
            FROM file_metadata ORDER BY upload_time DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [
            FileMetadata(
                file_id=row[0],
                filename=row[1],
                content_type=row[2],
                file_size=row[3],
                file_hash=row[4],
                upload_time=datetime.fromisoformat(row[6]),
                storage_path=row[5],
                metadata=json.loads(row[7]) if row[7] else None
            ) for row in results
        ]

class MinIOFileStorage(FileStorageInterface):
    """MinIO文件存储实现"""
    
    def __init__(self, config):
        self.config = config
        self.client = self._init_client()
        self._ensure_bucket_exists()
    
    def _init_client(self):
        """初始化MinIO客户端"""
        if not MINIO_AVAILABLE:
            raise ImportError("MinIO依赖库未安装，请运行: pip install minio")
        
        return Minio(
            self.config.endpoint,
            access_key=self.config.access_key,
            secret_key=self.config.secret_key,
            secure=self.config.secure
        )
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.config.bucket_name):
                self.client.make_bucket(self.config.bucket_name)
        except S3Error as e:
            raise Exception(f"创建存储桶失败: {str(e)}")
    
    def _calculate_hash(self, data: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(data).hexdigest()
    
    def _get_object_key(self, file_id: str, filename: str) -> str:
        """生成对象存储键"""
        # 按日期分组存储
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        return f"files/{date_prefix}/{file_id}_{filename}"
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = None, metadata: Dict[str, Any] = None) -> FileMetadata:
        """上传文件到MinIO"""
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        file_id = str(uuid.uuid4())
        file_hash = self._calculate_hash(file_data)
        file_size = len(file_data)
        upload_time = datetime.now()
        object_key = self._get_object_key(file_id, filename)
        
        try:
            # 准备元数据
            upload_metadata = {}
            if metadata:
                # MinIO元数据键必须以x-amz-meta-开头
                for key, value in metadata.items():
                    upload_metadata[f"x-amz-meta-{key}"] = str(value)
            
            # 添加文件信息到元数据
            upload_metadata.update({
                "x-amz-meta-file-id": file_id,
                "x-amz-meta-file-hash": file_hash,
                "x-amz-meta-upload-time": upload_time.isoformat(),
                "x-amz-meta-original-filename": filename
            })
            
            # 上传文件
            data_stream = io.BytesIO(file_data)
            self.client.put_object(
                bucket_name=self.config.bucket_name,
                object_name=object_key,
                data=data_stream,
                length=file_size,
                content_type=content_type,
                metadata=upload_metadata
            )
            
            return FileMetadata(
                file_id=file_id,
                filename=filename,
                content_type=content_type,
                file_size=file_size,
                file_hash=file_hash,
                upload_time=upload_time,
                storage_path=object_key,
                metadata=metadata
            )
            
        except S3Error as e:
            raise Exception(f"MinIO文件上传失败: {str(e)}")
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """从MinIO下载文件"""
        try:
            # 通过元数据查找文件
            objects = self.client.list_objects(
                self.config.bucket_name,
                prefix="files/",
                recursive=True
            )
            
            for obj in objects:
                try:
                    # 获取对象元数据
                    obj_stat = self.client.stat_object(self.config.bucket_name, obj.object_name)
                    obj_metadata = obj_stat.metadata
                    
                    # 检查文件ID
                    if obj_metadata.get("x-amz-meta-file-id") == file_id:
                        # 下载文件
                        response = self.client.get_object(self.config.bucket_name, obj.object_name)
                        data = response.read()
                        response.close()
                        response.release_conn()
                        return data
                except:
                    continue
            
            return None
            
        except S3Error:
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """从MinIO删除文件"""
        try:
            # 通过元数据查找文件
            objects = self.client.list_objects(
                self.config.bucket_name,
                prefix="files/",
                recursive=True
            )
            
            for obj in objects:
                try:
                    # 获取对象元数据
                    obj_stat = self.client.stat_object(self.config.bucket_name, obj.object_name)
                    obj_metadata = obj_stat.metadata
                    
                    # 检查文件ID
                    if obj_metadata.get("x-amz-meta-file-id") == file_id:
                        # 删除文件
                        self.client.remove_object(self.config.bucket_name, obj.object_name)
                        return True
                except:
                    continue
            
            return False
            
        except S3Error:
            return False
    
    def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        try:
            # 通过元数据查找文件
            objects = self.client.list_objects(
                self.config.bucket_name,
                prefix="files/",
                recursive=True
            )
            
            for obj in objects:
                try:
                    # 获取对象元数据
                    obj_stat = self.client.stat_object(self.config.bucket_name, obj.object_name)
                    obj_metadata = obj_stat.metadata
                    
                    # 检查文件ID
                    if obj_metadata.get("x-amz-meta-file-id") == file_id:
                        # 构建文件元数据
                        return FileMetadata(
                            file_id=file_id,
                            filename=obj_metadata.get("x-amz-meta-original-filename", "unknown"),
                            content_type=obj_stat.content_type,
                            file_size=obj_stat.size,
                            file_hash=obj_metadata.get("x-amz-meta-file-hash", ""),
                            upload_time=datetime.fromisoformat(
                                obj_metadata.get("x-amz-meta-upload-time", datetime.now().isoformat())
                            ),
                            storage_path=obj.object_name,
                            metadata={
                                key.replace("x-amz-meta-", ""): value 
                                for key, value in obj_metadata.items() 
                                if key.startswith("x-amz-meta-") and not key.startswith("x-amz-meta-file-")
                            }
                        )
                except:
                    continue
            
            return None
            
        except S3Error:
            return None
    
    def list_files(self, limit: int = 100, offset: int = 0) -> List[FileMetadata]:
        """列出文件"""
        try:
            # 获取所有文件对象
            objects = list(self.client.list_objects(
                self.config.bucket_name,
                prefix="files/",
                recursive=True
            ))
            
            # 按上传时间排序（从新到旧）
            objects.sort(key=lambda x: x.last_modified, reverse=True)
            
            # 分页处理
            paginated_objects = objects[offset:offset + limit]
            
            results = []
            for obj in paginated_objects:
                try:
                    # 获取对象元数据
                    obj_stat = self.client.stat_object(self.config.bucket_name, obj.object_name)
                    obj_metadata = obj_stat.metadata
                    
                    file_id = obj_metadata.get("x-amz-meta-file-id", "")
                    if file_id:
                        results.append(FileMetadata(
                            file_id=file_id,
                            filename=obj_metadata.get("x-amz-meta-original-filename", "unknown"),
                            content_type=obj_stat.content_type,
                            file_size=obj_stat.size,
                            file_hash=obj_metadata.get("x-amz-meta-file-hash", ""),
                            upload_time=datetime.fromisoformat(
                                obj_metadata.get("x-amz-meta-upload-time", datetime.now().isoformat())
                            ),
                            storage_path=obj.object_name,
                            metadata={
                                key.replace("x-amz-meta-", ""): value 
                                for key, value in obj_metadata.items() 
                                if key.startswith("x-amz-meta-") and not key.startswith("x-amz-meta-file-")
                            }
                        ))
                except:
                    continue
            
            return results
            
        except S3Error:
            return []

# 存储工厂类
class FileStorageFactory:
    """文件存储工厂"""
    
    @staticmethod
    def create_storage() -> FileStorageInterface:
        """根据配置创建存储实例"""
        config = get_storage_config()
        
        if config.storage_type == StorageType.POSTGRESQL:
            return PostgreSQLFileStorage(config)
        elif config.storage_type == StorageType.ELASTICSEARCH:
            return ElasticsearchFileStorage(config)
        elif config.storage_type == StorageType.LOCAL_FILE:
            return LocalFileStorage(config)
        elif config.storage_type == StorageType.MINIO:
            return MinIOFileStorage(config)
        else:
            raise ValueError(f"Unsupported storage type: {config.storage_type}")

# 全局存储实例
_storage_instance = None

def get_file_storage() -> FileStorageInterface:
    """获取文件存储实例（单例模式）"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = FileStorageFactory.create_storage()
    return _storage_instance 