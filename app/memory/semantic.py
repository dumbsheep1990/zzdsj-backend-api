"""
智能体记忆系统 - 语义记忆实现

实现基于向量相似度检索的语义记忆。
"""

from .base import BaseMemory
from .interfaces import MemoryConfig, MemoryType
from typing import Any, Dict, List, Optional, Tuple
import json
from datetime import datetime
from app.utils.core.database import get_db_engine

class SemanticMemory(BaseMemory[Dict[str, Any]]):
    """语义记忆实现，基于向量相似度检索"""
    
    def __init__(self, memory_id: str, owner_id: str, config: MemoryConfig):
        super().__init__(memory_id, owner_id, config)
        self.items = {}  # 键到记忆项的映射
        
        # 初始化向量存储
        self.vector_store = self._initialize_vector_store(config.vector_backend)
        
    def _initialize_vector_store(self, vector_backend: Optional[str]):
        """初始化向量存储"""
        if vector_backend == "milvus":
            from app.utils.milvus_client import get_milvus_client
            return get_milvus_client()
        elif vector_backend == "elasticsearch":
            from app.utils.elasticsearch_client import get_elasticsearch_client
            return get_elasticsearch_client()
        elif vector_backend == "pgvector":
            return get_db_engine()
        else:
            # 默认使用内存向量存储
            # 使用新的标准化向量存储组件
            from app.utils.storage.vector_storage import InMemoryVectorStore
            return InMemoryVectorStore()
    
    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        from app.utils.embedding import get_embedding
        return await get_embedding(text)
    
    async def add(self, key: str, value: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加记忆项"""
        await super().add(key, value, metadata)
        
        # 提取文本内容
        text = value.get("text", "")
        if not text and "content" in value:
            text = value["content"]
            
        if not text:
            text = json.dumps(value)
        
        # 获取嵌入向量
        embedding = await self._get_embedding(text)
        
        # 创建记忆项
        memory_item = {
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "embedding": embedding,
            "created_at": datetime.now().isoformat()
        }
        
        # 存储记忆项
        self.items[key] = memory_item
        
        # 添加到向量存储
        await self.vector_store.add_vector(
            id=key,
            vector=embedding,
            metadata={
                "memory_id": self.memory_id,
                "owner_id": self.owner_id,
                "key": key,
                **metadata or {}
            }
        )
        
        return True
    
    async def query(self, query: str, top_k: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        """查询最相关记忆"""
        await super().query(query)
        
        # 空查询时返回最近的项
        if not query:
            items = list(self.items.values())
            items.sort(key=lambda x: x["created_at"], reverse=True)
            return [(item["key"], item["value"], 1.0) for item in items[:top_k]]
        
        # 获取查询嵌入向量
        query_embedding = await self._get_embedding(query)
        
        # 向量检索
        results = await self.vector_store.search_vectors(
            query_vector=query_embedding,
            filter={"memory_id": self.memory_id},
            top_k=top_k
        )
        
        # 整理结果
        memory_results = []
        for result in results:
            key = result["id"]
            if key in self.items:
                memory_results.append(
                    (key, self.items[key]["value"], result["score"])
                )
                
        return memory_results
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取记忆项"""
        await super().get(key)
        
        if key not in self.items:
            return None
            
        return self.items[key]["value"]
    
    async def update(self, key: str, value: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新记忆项"""
        # 删除旧项
        if key in self.items:
            await self.delete(key)
            
        # 添加新项
        return await self.add(key, value, metadata)
    
    async def delete(self, key: str) -> bool:
        """删除记忆项"""
        await super().delete(key)
        
        if key not in self.items:
            return False
            
        # 从向量存储删除
        await self.vector_store.delete_vector(key)
        
        # 从本地存储删除
        del self.items[key]
        
        return True
    
    async def clear(self) -> bool:
        """清空所有记忆"""
        await super().clear()
        
        # 删除所有向量
        for key in list(self.items.keys()):
            await self.delete(key)
            
        return True
