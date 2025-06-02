"""
PostgreSQL+pgvector向量存储适配器
"""

from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import json
import uuid
from datetime import datetime
from ..core.base import VectorStorage
from ..core.exceptions import VectorStoreError, ConnectionError

try:
    import asyncpg
    import psycopg2
    from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Text, DateTime, func
    from sqlalchemy.dialects.postgresql import UUID, JSONB, VARCHAR
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

logger = logging.getLogger(__name__)

Base = declarative_base()


class DocumentVectorTable(Base):
    """文档向量表模型"""
    __tablename__ = 'document_vectors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(VARCHAR(100), nullable=False, index=True)
    knowledge_base_id = Column(VARCHAR(100), nullable=False, index=True)
    chunk_id = Column(VARCHAR(100), nullable=False, index=True)
    embedding = Column(Vector(1536))  # pgvector类型
    content = Column(Text)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PgVectorStore(VectorStorage):
    """
    PostgreSQL+pgvector向量存储适配器
    实现基于pgvector扩展的向量存储功能
    """
    
    def __init__(self, name: str = "pgvector", config: Optional[Dict[str, Any]] = None):
        """
        初始化PostgreSQL+pgvector向量存储
        
        参数:
            name: 存储名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._engine = None
        self._session_factory = None
        self._tables = {}
        
    async def initialize(self) -> None:
        """初始化PostgreSQL+pgvector向量存储"""
        if self._initialized:
            return
        
        if not PGVECTOR_AVAILABLE:
            raise VectorStoreError("pgvector相关依赖库未安装")
        
        try:
            # 从配置获取连接参数
            database_url = self.get_config("database_url") or self.get_config("vector_store_database_url")
            if not database_url:
                host = self.get_config("host", "localhost")
                port = self.get_config("port", 5432)
                user = self.get_config("user", "postgres")
                password = self.get_config("password", "password")
                database = self.get_config("database", "postgres")
                database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            
            # 创建数据库引擎
            self._engine = create_engine(database_url, echo=False)
            self._session_factory = sessionmaker(bind=self._engine)
            
            # 确保pgvector扩展已安装
            await self._ensure_pgvector_extension()
            
            # 创建基础表结构
            await self._create_base_tables()
            
            self._initialized = True
            self._connected = True
            self.logger.info(f"PostgreSQL+pgvector连接成功: {database_url}")
            
        except Exception as e:
            self.logger.error(f"PostgreSQL+pgvector初始化失败: {str(e)}")
            raise ConnectionError(f"PostgreSQL连接失败: {str(e)}", endpoint=database_url)
    
    async def _ensure_pgvector_extension(self) -> None:
        """确保pgvector扩展已安装"""
        try:
            with self._engine.connect() as conn:
                # 检查并创建pgvector扩展
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                self.logger.info("pgvector扩展已确保安装")
        except Exception as e:
            self.logger.error(f"安装pgvector扩展失败: {str(e)}")
            raise
    
    async def _create_base_tables(self) -> None:
        """创建基础表结构"""
        try:
            # 创建所有表
            Base.metadata.create_all(self._engine)
            self.logger.info("基础表结构创建完成")
        except Exception as e:
            self.logger.error(f"创建表结构失败: {str(e)}")
            raise
    
    async def connect(self) -> bool:
        """建立连接"""
        if not self._initialized:
            await self.initialize()
        return self._connected
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._engine:
            self._engine.dispose()
        self._connected = False
        self.logger.info("PostgreSQL+pgvector连接已断开")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._engine:
                return False
            
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            return False
    
    async def create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """创建向量集合（表）"""
        try:
            if not self._connected:
                await self.connect()
            
            # 动态创建表结构
            table_definition = self._generate_table_definition(name, dimension, **kwargs)
            
            with self._engine.connect() as conn:
                # 创建表
                conn.execute(text(table_definition))
                
                # 创建向量索引
                await self._create_vector_index(conn, name, dimension, **kwargs)
                
                conn.commit()
            
            self.logger.info(f"成功创建pgvector表: {name}, 维度: {dimension}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建pgvector表失败: {str(e)}")
            raise VectorStoreError(f"创建表失败: {str(e)}", collection=name)
    
    def _generate_table_definition(self, table_name: str, dimension: int, **kwargs) -> str:
        """生成表定义SQL"""
        fields = kwargs.get("fields", [])
        
        # 基础字段
        columns = [
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "document_id VARCHAR(100) NOT NULL",
            "knowledge_base_id VARCHAR(100) NOT NULL", 
            "chunk_id VARCHAR(100) NOT NULL",
            f"embedding vector({dimension})",
            "content TEXT",
            "metadata JSONB",
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        # 添加自定义字段
        for field in fields:
            field_type = self._map_data_type(field.get("data_type"))
            column_def = f"{field['name']} {field_type}"
            if not field.get("nullable", True):
                column_def += " NOT NULL"
            if field.get("default_value"):
                column_def += f" DEFAULT {field['default_value']}"
            columns.append(column_def)
        
        columns_sql = ",\n    ".join(columns)
        
        return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {columns_sql}
        )
        """
    
    def _map_data_type(self, data_type: str) -> str:
        """映射数据类型到PostgreSQL类型"""
        type_mapping = {
            "VARCHAR": "VARCHAR",
            "TEXT": "TEXT", 
            "INT64": "BIGINT",
            "FLOAT": "REAL",
            "DOUBLE": "DOUBLE PRECISION",
            "BOOL": "BOOLEAN",
            "JSONB": "JSONB",
            "UUID": "UUID",
            "TIMESTAMP": "TIMESTAMP"
        }
        return type_mapping.get(data_type, "TEXT")
    
    async def _create_vector_index(self, conn, table_name: str, dimension: int, **kwargs) -> None:
        """创建向量索引"""
        index_type = kwargs.get("index_type", "ivfflat")
        metric_type = kwargs.get("metric_type", "vector_cosine_ops")
        index_params = kwargs.get("index_params", {})
        
        if index_type.lower() == "ivfflat":
            lists = index_params.get("lists", 100)
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
            ON {table_name} 
            USING ivfflat (embedding {metric_type}) 
            WITH (lists = {lists})
            """
        elif index_type.lower() == "hnsw":
            m = index_params.get("m", 16)
            ef_construction = index_params.get("ef_construction", 64)
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
            ON {table_name} 
            USING hnsw (embedding {metric_type}) 
            WITH (m = {m}, ef_construction = {ef_construction})
            """
        else:
            # 默认使用ivfflat
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
            ON {table_name} 
            USING ivfflat (embedding {metric_type}) 
            WITH (lists = 100)
            """
        
        conn.execute(text(index_sql))
        self.logger.info(f"为表 {table_name} 创建向量索引成功")
    
    async def add_vectors(self, 
                         collection: str,
                         vectors: List[List[float]], 
                         ids: Optional[List[Union[int, str]]] = None,
                         metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """添加向量"""
        try:
            if not self._connected:
                await self.connect()
            
            session = self._session_factory()
            
            try:
                for i, vector in enumerate(vectors):
                    # 准备数据
                    data = {
                        "embedding": vector,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    # 添加ID
                    if ids and i < len(ids):
                        data["id"] = ids[i]
                    
                    # 添加元数据
                    if metadata and i < len(metadata):
                        meta = metadata[i]
                        data.update({
                            "document_id": meta.get("document_id"),
                            "knowledge_base_id": meta.get("knowledge_base_id"),
                            "chunk_id": meta.get("chunk_id"),
                            "content": meta.get("content"),
                            "metadata": meta.get("metadata", {})
                        })
                    
                    # 构建插入SQL
                    placeholders = ", ".join([f":{key}" for key in data.keys()])
                    columns = ", ".join(data.keys())
                    
                    sql = f"""
                    INSERT INTO {collection} ({columns}) 
                    VALUES ({placeholders})
                    """
                    
                    session.execute(text(sql), data)
                
                session.commit()
                self.logger.info(f"成功向表 {collection} 添加 {len(vectors)} 个向量")
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"添加向量失败: {str(e)}")
            raise VectorStoreError(f"添加向量失败: {str(e)}", collection=collection)
    
    async def search_vectors(self, 
                           collection: str,
                           query_vector: List[float],
                           top_k: int = 10,
                           filter_conditions: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            if not self._connected:
                await self.connect()
            
            # 构建搜索SQL
            distance_metric = "embedding <=> %s"  # 余弦距离
            base_sql = f"""
            SELECT 
                id,
                document_id,
                knowledge_base_id,
                chunk_id,
                content,
                metadata,
                {distance_metric} as distance
            FROM {collection}
            """
            
            # 添加过滤条件
            where_conditions = []
            params = [str(query_vector)]
            
            if filter_conditions:
                for key, value in filter_conditions.items():
                    where_conditions.append(f"{key} = %s")
                    params.append(value)
            
            if where_conditions:
                base_sql += " WHERE " + " AND ".join(where_conditions)
            
            # 添加排序和限制
            sql = f"{base_sql} ORDER BY distance LIMIT %s"
            params.append(top_k)
            
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params)
                results = []
                
                for row in result:
                    results.append({
                        "id": str(row.id),
                        "document_id": row.document_id,
                        "knowledge_base_id": row.knowledge_base_id,
                        "chunk_id": row.chunk_id,
                        "content": row.content,
                        "metadata": row.metadata,
                        "score": float(1 - row.distance),  # 转换为相似度分数
                        "distance": float(row.distance)
                    })
                
                self.logger.info(f"在表 {collection} 中搜索到 {len(results)} 个结果")
                return results
                
        except Exception as e:
            self.logger.error(f"搜索向量失败: {str(e)}")
            raise VectorStoreError(f"搜索向量失败: {str(e)}", collection=collection)
    
    async def delete_vectors(self, 
                           collection: str,
                           ids: List[Union[int, str]]) -> bool:
        """删除向量"""
        try:
            if not self._connected:
                await self.connect()
            
            # 构建删除SQL
            placeholders = ", ".join(["%s"] * len(ids))
            sql = f"DELETE FROM {collection} WHERE id IN ({placeholders})"
            
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), ids)
                deleted_count = result.rowcount
                conn.commit()
            
            self.logger.info(f"从表 {collection} 删除了 {deleted_count} 个向量")
            return deleted_count > 0
            
        except Exception as e:
            self.logger.error(f"删除向量失败: {str(e)}")
            raise VectorStoreError(f"删除向量失败: {str(e)}", collection=collection)
    
    async def collection_exists(self, name: str) -> bool:
        """检查集合（表）是否存在"""
        try:
            if not self._connected:
                await self.connect()
            
            sql = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            )
            """
            
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), [name])
                return result.scalar()
                
        except Exception as e:
            self.logger.error(f"检查表存在性失败: {str(e)}")
            return False
    
    async def drop_collection(self, name: str) -> bool:
        """删除集合（表）"""
        try:
            if not self._connected:
                await self.connect()
            
            sql = f"DROP TABLE IF EXISTS {name}"
            
            with self._engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            
            self.logger.info(f"删除表 {name} 成功")
            return True
            
        except Exception as e:
            self.logger.error(f"删除表失败: {str(e)}")
            raise VectorStoreError(f"删除表失败: {str(e)}", collection=name)
    
    async def get_collection_stats(self, name: str) -> Dict[str, Any]:
        """获取集合（表）统计信息"""
        try:
            if not self._connected:
                await self.connect()
            
            sql = f"SELECT COUNT(*) as total_vectors FROM {name}"
            
            with self._engine.connect() as conn:
                result = conn.execute(text(sql))
                total_vectors = result.scalar()
            
            return {
                "name": name,
                "total_vectors": total_vectors,
                "backend": "pgvector"
            }
            
        except Exception as e:
            self.logger.error(f"获取表统计信息失败: {str(e)}")
            return {"name": name, "total_vectors": 0, "backend": "pgvector"} 