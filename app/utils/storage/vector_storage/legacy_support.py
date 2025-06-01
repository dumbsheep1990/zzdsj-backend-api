"""
向量存储向后兼容支持
保持原有接口不变，内部使用新架构实现
"""

from typing import List, Dict, Any, Optional
import logging
from .store import get_vector_store
from ..core.config import create_config_from_settings

logger = logging.getLogger(__name__)

# 全局变量，保持与原接口兼容
_initialized = False
_global_collection = None


def init_milvus():
    """
    初始化Milvus向量数据库连接
    保持与原接口兼容
    """
    global _initialized
    
    if _initialized:
        return
    
    try:
        # 尝试导入settings
        from app.config import settings
        
        # 创建配置
        config = create_config_from_settings(settings).to_dict()
        
        # 获取向量存储实例
        vector_store = get_vector_store(config)
        
        # 异步初始化（在同步函数中处理）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已在运行，创建任务
                asyncio.create_task(vector_store.initialize())
            else:
                # 如果没有运行事件循环，直接运行
                loop.run_until_complete(vector_store.initialize())
        except RuntimeError:
            # 如果没有事件循环，创建新的
            asyncio.run(vector_store.initialize())
        
        _initialized = True
        logger.info("Milvus初始化完成 (兼容模式)")
        
    except Exception as e:
        logger.error(f"Milvus初始化失败: {str(e)}")
        raise


def create_collection(dim: int = 1536):
    """
    创建用于文档嵌入的Milvus集合
    保持与原接口兼容
    """
    try:
        # 尝试导入settings
        from app.config import settings
        collection_name = getattr(settings, 'MILVUS_COLLECTION', 'default_collection')
        
        # 获取向量存储实例
        vector_store = get_vector_store()
        
        # 异步创建集合
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(vector_store.create_collection(collection_name, dim))
            else:
                loop.run_until_complete(vector_store.create_collection(collection_name, dim))
        except RuntimeError:
            asyncio.run(vector_store.create_collection(collection_name, dim))
        
        # 模拟返回Collection对象
        return MockCollection(collection_name, vector_store)
        
    except Exception as e:
        logger.error(f"创建集合失败: {str(e)}")
        raise


def get_collection():
    """
    获取Milvus集合，如有必要则创建
    保持与原接口兼容
    """
    global _global_collection
    
    if _global_collection is None:
        _global_collection = create_collection()
    
    return _global_collection


def add_vectors(chunk_ids: List[int], document_ids: List[int], vectors: List[List[float]]):
    """
    向Milvus集合添加向量
    保持与原接口兼容
    """
    try:
        # 准备元数据
        metadata = []
        for i, (chunk_id, doc_id) in enumerate(zip(chunk_ids, document_ids)):
            metadata.append({
                "chunk_id": chunk_id,
                "document_id": doc_id
            })
        
        # 获取集合
        collection = get_collection()
        
        # 添加向量
        collection.add_vectors(vectors, metadata=metadata)
        
    except Exception as e:
        logger.error(f"添加向量失败: {str(e)}")
        raise


def search_similar_vectors(query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    在Milvus中搜索相似向量
    保持与原接口兼容
    """
    try:
        # 获取集合
        collection = get_collection()
        
        # 搜索向量
        results = collection.search_vectors(query_vector, top_k)
        
        # 转换结果格式以保持兼容性
        formatted_results = []
        for result in results:
            formatted_results.append({
                "chunk_id": result.get("chunk_id"),
                "document_id": result.get("document_id"),
                "score": result.get("score")
            })
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"搜索向量失败: {str(e)}")
        raise


class MockCollection:
    """
    模拟Collection对象，保持向后兼容性
    """
    
    def __init__(self, name: str, vector_store):
        self.name = name
        self._vector_store = vector_store
    
    def add_vectors(self, vectors: List[List[float]], metadata: Optional[List[Dict[str, Any]]] = None):
        """添加向量"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._vector_store.add_vectors(self.name, vectors, metadata=metadata)
                )
            else:
                loop.run_until_complete(
                    self._vector_store.add_vectors(self.name, vectors, metadata=metadata)
                )
        except RuntimeError:
            asyncio.run(
                self._vector_store.add_vectors(self.name, vectors, metadata=metadata)
            )
    
    def search_vectors(self, query_vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索向量"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 创建任务但不能直接获取结果，返回空列表作为fallback
                asyncio.create_task(
                    self._vector_store.search_vectors(self.name, query_vector, top_k)
                )
                return []
            else:
                return loop.run_until_complete(
                    self._vector_store.search_vectors(self.name, query_vector, top_k)
                )
        except RuntimeError:
            return asyncio.run(
                self._vector_store.search_vectors(self.name, query_vector, top_k)
            )
    
    def insert(self, data):
        """插入数据 - 模拟原始接口"""
        # 解析数据格式 [chunk_ids, document_ids, vectors]
        if isinstance(data, list) and len(data) >= 3:
            chunk_ids, document_ids, vectors = data[0], data[1], data[2]
            
            # 准备元数据
            metadata = []
            for chunk_id, doc_id in zip(chunk_ids, document_ids):
                metadata.append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id
                })
            
            self.add_vectors(vectors, metadata)
    
    def flush(self):
        """刷新 - 模拟原始接口"""
        # 在新架构中，刷新操作已在add_vectors中处理
        pass
    
    def load(self):
        """加载 - 模拟原始接口"""
        # 在新架构中，加载操作已在search_vectors中处理
        pass
    
    def search(self, data, anns_field, param, limit, output_fields=None):
        """搜索 - 模拟原始接口"""
        # 转换为新接口调用
        if isinstance(data, list) and len(data) > 0:
            query_vector = data[0]
            results = self.search_vectors(query_vector, limit)
            
            # 模拟原始返回格式
            class MockHits:
                def __init__(self, results):
                    self.hits = []
                    for result in results:
                        hit = MockHit(result)
                        self.hits.append(hit)
                
                def __iter__(self):
                    return iter(self.hits)
            
            return [MockHits(results)]
        
        return []


class MockHit:
    """模拟Hit对象"""
    
    def __init__(self, result: Dict[str, Any]):
        self.id = result.get("id")
        self.distance = result.get("score", 0.0)
        self.entity = MockEntity(result)


class MockEntity:
    """模拟Entity对象"""
    
    def __init__(self, result: Dict[str, Any]):
        self._data = result
    
    def get(self, key: str):
        return self._data.get(key) 