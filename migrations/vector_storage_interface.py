"""
迁移系统的向量存储接口
提供简化的向量存储操作，避免复杂的依赖关系
"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from config import get_vector_store_config

logger = logging.getLogger(__name__)


class VectorStoreInterface(ABC):
    """向量存储接口基类"""
    
    @abstractmethod
    async def create_collection(self, collection_name: str, config: Dict[str, Any]) -> bool:
        """创建集合"""
        pass
    
    @abstractmethod
    async def drop_collection(self, collection_name: str) -> bool:
        """删除集合"""
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        pass
    
    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        pass


class MockVectorStore(VectorStoreInterface):
    """模拟向量存储，用于测试和开发"""
    
    def __init__(self):
        self.collections = set()
        logger.info("初始化模拟向量存储")
    
    async def create_collection(self, collection_name: str, config: Dict[str, Any]) -> bool:
        """创建集合"""
        try:
            self.collections.add(collection_name)
            logger.info(f"模拟创建集合: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"模拟创建集合失败: {str(e)}")
            return False
    
    async def drop_collection(self, collection_name: str) -> bool:
        """删除集合"""
        try:
            self.collections.discard(collection_name)
            logger.info(f"模拟删除集合: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"模拟删除集合失败: {str(e)}")
            return False
    
    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        return list(self.collections)
    
    async def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        return collection_name in self.collections


class MilvusVectorStore(VectorStoreInterface):
    """Milvus向量存储实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        logger.info(f"初始化Milvus向量存储: {config.get('host')}:{config.get('port')}")
    
    async def _get_client(self):
        """获取Milvus客户端"""
        if self.client is None:
            try:
                from pymilvus import connections, utility
                connections.connect(
                    alias="default",
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 19530)
                )
                self.client = utility
                logger.info("Milvus客户端连接成功")
            except ImportError:
                logger.error("pymilvus模块未安装，无法连接Milvus")
                raise
            except Exception as e:
                logger.error(f"连接Milvus失败: {str(e)}")
                raise
        return self.client
    
    async def create_collection(self, collection_name: str, config: Dict[str, Any]) -> bool:
        """创建集合"""
        try:
            from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
            
            client = await self._get_client()
            
            # 检查集合是否已存在
            if await self.collection_exists(collection_name):
                logger.info(f"集合 {collection_name} 已存在")
                return True
            
            # 创建字段模式
            fields = []
            for field_config in config.get("fields", []):
                field = FieldSchema(
                    name=field_config["name"],
                    dtype=getattr(DataType, field_config["type"]),
                    is_primary=field_config.get("is_primary", False),
                    max_length=field_config.get("max_length"),
                    dim=field_config.get("dimension")
                )
                fields.append(field)
            
            # 创建集合模式
            schema = CollectionSchema(
                fields=fields,
                description=config.get("description", "")
            )
            
            # 创建集合
            collection = Collection(
                name=collection_name,
                schema=schema
            )
            
            logger.info(f"Milvus集合创建成功: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建Milvus集合失败: {str(e)}")
            return False
    
    async def drop_collection(self, collection_name: str) -> bool:
        """删除集合"""
        try:
            from pymilvus import utility
            
            client = await self._get_client()
            
            if await self.collection_exists(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Milvus集合删除成功: {collection_name}")
            else:
                logger.info(f"集合 {collection_name} 不存在，无需删除")
            
            return True
            
        except Exception as e:
            logger.error(f"删除Milvus集合失败: {str(e)}")
            return False
    
    async def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            from pymilvus import utility
            
            client = await self._get_client()
            collections = utility.list_collections()
            return collections
            
        except Exception as e:
            logger.error(f"列出Milvus集合失败: {str(e)}")
            return []
    
    async def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            from pymilvus import utility
            
            client = await self._get_client()
            return utility.has_collection(collection_name)
            
        except Exception as e:
            logger.error(f"检查Milvus集合存在性失败: {str(e)}")
            return False


class PgVectorStore(VectorStoreInterface):
    """PgVector向量存储实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.database_url = config.get("database_url")
        logger.info("初始化PgVector向量存储")
    
    async def create_collection(self, collection_name: str, config: Dict[str, Any]) -> bool:
        """创建集合（在PgVector中即创建表）"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(self.database_url)
            try:
                # 确保vector扩展已安装
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
                # 创建向量表
                dimension = config.get("dimension", 768)
                sql = f"""
                CREATE TABLE IF NOT EXISTS {collection_name} (
                    id SERIAL PRIMARY KEY,
                    embedding vector({dimension}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                await conn.execute(sql)
                
                # 创建向量索引
                index_sql = f"""
                CREATE INDEX IF NOT EXISTS {collection_name}_embedding_idx 
                ON {collection_name} USING ivfflat (embedding vector_cosine_ops)
                """
                await conn.execute(index_sql)
                
                logger.info(f"PgVector表创建成功: {collection_name}")
                return True
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"创建PgVector表失败: {str(e)}")
            return False
    
    async def drop_collection(self, collection_name: str) -> bool:
        """删除集合（删除表）"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(self.database_url)
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {collection_name}")
                logger.info(f"PgVector表删除成功: {collection_name}")
                return True
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"删除PgVector表失败: {str(e)}")
            return False
    
    async def list_collections(self) -> List[str]:
        """列出所有集合（表）"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(self.database_url)
            try:
                result = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                """)
                return [row[0] for row in result]
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"列出PgVector表失败: {str(e)}")
            return []
    
    async def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(self.database_url)
            try:
                result = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, collection_name)
                return result
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"检查PgVector表存在性失败: {str(e)}")
            return False


def create_vector_store(vector_store_type: str) -> VectorStoreInterface:
    """创建向量存储实例"""
    config = get_vector_store_config(vector_store_type)
    
    if vector_store_type.lower() == "milvus":
        try:
            return MilvusVectorStore(config)
        except Exception as e:
            logger.warning(f"创建Milvus向量存储失败，使用模拟存储: {str(e)}")
            return MockVectorStore()
    
    elif vector_store_type.lower() == "pgvector":
        try:
            return PgVectorStore(config)
        except Exception as e:
            logger.warning(f"创建PgVector向量存储失败，使用模拟存储: {str(e)}")
            return MockVectorStore()
    
    else:
        logger.warning(f"不支持的向量存储类型: {vector_store_type}，使用模拟存储")
        return MockVectorStore() 