"""
Milvus向量存储适配器
"""

from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
from ..core.base import VectorStorage
from ..core.exceptions import VectorStoreError, ConnectionError

try:
    from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
    import numpy as np
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    # 提供fallback类以避免NameError
    class Collection:
        pass
    class FieldSchema:
        pass
    class CollectionSchema:
        pass
    class DataType:
        INT64 = "INT64"
        FLOAT_VECTOR = "FLOAT_VECTOR"
    
    # 提供numpy fallback
    try:
        import numpy as np
    except ImportError:
        class np:
            @staticmethod
            def array(data):
                return data

logger = logging.getLogger(__name__)


class MilvusVectorStore(VectorStorage):
    """
    Milvus向量存储适配器
    实现基于Milvus的向量存储功能
    """
    
    def __init__(self, name: str = "milvus", config: Optional[Dict[str, Any]] = None):
        """
        初始化Milvus向量存储
        
        参数:
            name: 存储名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._connection_alias = f"milvus_{name}"
        self._collections = {}
    
    async def initialize(self) -> None:
        """初始化Milvus向量存储"""
        if self._initialized:
            return
        
        if not MILVUS_AVAILABLE:
            raise VectorStoreError("Milvus依赖库未安装")
        
        try:
            # 从配置获取连接参数
            host = self.get_config("vector_store_host", "localhost")
            port = self.get_config("vector_store_port", 19530)
            
            # 建立连接
            connections.connect(
                alias=self._connection_alias,
                host=host,
                port=port
            )
            
            self._initialized = True
            self._connected = True
            self.logger.info(f"Milvus连接成功: {host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Milvus初始化失败: {str(e)}")
            raise ConnectionError(f"Milvus连接失败: {str(e)}", endpoint=f"{host}:{port}")
    
    async def connect(self) -> bool:
        """建立连接"""
        if not self._initialized:
            await self.initialize()
        return self._connected
    
    async def disconnect(self) -> None:
        """断开连接"""
        try:
            if MILVUS_AVAILABLE and self._connection_alias in connections.list_connections():
                connections.disconnect(self._connection_alias)
            self._connected = False
            self.logger.info("Milvus连接已断开")
        except Exception as e:
            self.logger.error(f"断开Milvus连接失败: {str(e)}")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._connected or not MILVUS_AVAILABLE:
                return False
            
            # 尝试列出集合来验证连接
            utility.list_collections(using=self._connection_alias)
            return True
        except Exception as e:
            self.logger.warning(f"Milvus健康检查失败: {str(e)}")
            return False
    
    async def create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """创建向量集合"""
        if not MILVUS_AVAILABLE:
            raise VectorStoreError("Milvus依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 检查集合是否已存在
            if utility.has_collection(name, using=self._connection_alias):
                self.logger.info(f"集合 {name} 已存在")
                return True
            
            # 创建字段schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="chunk_id", dtype=DataType.INT64),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension)
            ]
            
            # 添加自定义字段
            if "extra_fields" in kwargs:
                for field_config in kwargs["extra_fields"]:
                    fields.append(FieldSchema(**field_config))
            
            # 创建collection schema
            schema = CollectionSchema(fields=fields, description=f"向量集合: {name}")
            collection = Collection(name=name, schema=schema, using=self._connection_alias)
            
            # 创建索引
            index_params = kwargs.get("index_params", {
                "index_type": "IVF_FLAT",
                "metric_type": "L2", 
                "params": {"nlist": 1024}
            })
            
            collection.create_index(field_name="embedding", index_params=index_params)
            
            # 缓存集合对象
            self._collections[name] = collection
            
            self.logger.info(f"成功创建集合: {name}, 维度: {dimension}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建集合失败: {str(e)}")
            raise VectorStoreError(f"创建集合失败: {str(e)}", collection=name)
    
    async def add_vectors(self, 
                         collection: str,
                         vectors: List[List[float]], 
                         ids: Optional[List[Union[int, str]]] = None,
                         metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """添加向量"""
        if not MILVUS_AVAILABLE:
            raise VectorStoreError("Milvus依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 获取集合对象
            coll = self._get_collection(collection)
            
            # 准备数据
            chunk_ids = []
            document_ids = []
            
            if metadata:
                for meta in metadata:
                    chunk_ids.append(meta.get("chunk_id", 0))
                    document_ids.append(meta.get("document_id", 0))
            else:
                chunk_ids = list(range(len(vectors)))
                document_ids = [0] * len(vectors)
            
            # 插入数据
            data = [chunk_ids, document_ids, vectors]
            coll.insert(data)
            coll.flush()
            
            self.logger.info(f"成功添加 {len(vectors)} 个向量到集合 {collection}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加向量失败: {str(e)}")
            raise VectorStoreError(f"添加向量失败: {str(e)}", collection=collection)
    
    async def search_vectors(self,
                           collection: str,
                           query_vector: List[float],
                           top_k: int = 10,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        if not MILVUS_AVAILABLE:
            raise VectorStoreError("Milvus依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 获取集合对象
            coll = self._get_collection(collection)
            coll.load()
            
            # 准备查询向量
            if not isinstance(query_vector, np.ndarray):
                query_vector = np.array([query_vector])
            
            # 执行搜索
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = coll.search(
                data=query_vector,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["chunk_id", "document_id"]
            )
            
            # 格式化结果
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "id": hit.id,
                        "chunk_id": hit.entity.get("chunk_id"),
                        "document_id": hit.entity.get("document_id"),
                        "score": hit.distance
                    })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"搜索向量失败: {str(e)}")
            raise VectorStoreError(f"搜索向量失败: {str(e)}", collection=collection)
    
    async def delete_vectors(self,
                           collection: str,
                           ids: List[Union[int, str]]) -> bool:
        """删除向量"""
        if not MILVUS_AVAILABLE:
            raise VectorStoreError("Milvus依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 获取集合对象
            coll = self._get_collection(collection)
            
            # 构建删除表达式
            id_list = [str(id_val) for id_val in ids]
            expr = f"id in [{','.join(id_list)}]"
            
            # 执行删除
            coll.delete(expr)
            coll.flush()
            
            self.logger.info(f"成功删除 {len(ids)} 个向量从集合 {collection}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除向量失败: {str(e)}")
            raise VectorStoreError(f"删除向量失败: {str(e)}", collection=collection)
    
    def _get_collection(self, name: str) -> Collection:
        """获取集合对象"""
        if not MILVUS_AVAILABLE:
            raise VectorStoreError("Milvus依赖库未安装")
            
        if name not in self._collections:
            if not utility.has_collection(name, using=self._connection_alias):
                raise VectorStoreError(f"集合 {name} 不存在", collection=name)
            
            self._collections[name] = Collection(name=name, using=self._connection_alias)
        
        return self._collections[name] 