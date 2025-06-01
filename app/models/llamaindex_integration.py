"""
LlamaIndex集成模型模块
用于管理LlamaIndex框架的索引配置和存储上下文
"""

import uuid
from sqlalchemy import Column, String, JSON, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.utils.core.database import Base
from typing import Dict, Any, Optional

class LlamaIndexIntegration(Base):
    """LlamaIndex集成模型"""
    __tablename__ = 'llamaindex_integrations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    index_name = Column(String(100), unique=True, nullable=False)  # 索引名称
    index_type = Column(String(50), nullable=False)  # 索引类型
    index_settings = Column(JSON, default={})  # 索引设置
    knowledge_base_id = Column(String(36), ForeignKey('knowledge_bases.id'))  # 关联的知识库ID
    storage_context = Column(JSON)  # 存储上下文配置
    embedding_model = Column(String(100))  # 嵌入模型
    chunk_size = Column(Integer, default=1024)  # 分块大小
    chunk_overlap = Column(Integer, default=200)  # 分块重叠
    metadata = Column(JSON, default={})  # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "id": self.id,
            "index_name": self.index_name,
            "index_type": self.index_type,
            "index_settings": self.index_settings,
            "knowledge_base_id": self.knowledge_base_id,
            "storage_context": self.storage_context,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, index_name: str, index_type: str, 
               knowledge_base_id: Optional[str] = None,
               index_settings: Dict[str, Any] = None,
               storage_context: Dict[str, Any] = None,
               embedding_model: Optional[str] = None,
               chunk_size: int = 1024,
               chunk_overlap: int = 200,
               metadata: Dict[str, Any] = None) -> 'LlamaIndexIntegration':
        """创建新的LlamaIndex集成配置
        
        Args:
            index_name: 索引名称
            index_type: 索引类型
            knowledge_base_id: 关联的知识库ID (可选)
            index_settings: 索引设置 (可选)
            storage_context: 存储上下文配置 (可选)
            embedding_model: 嵌入模型 (可选)
            chunk_size: 分块大小 (默认: 1024)
            chunk_overlap: 分块重叠 (默认: 200)
            metadata: 元数据 (可选)
            
        Returns:
            LlamaIndexIntegration: 创建的LlamaIndex集成配置实例
        """
        return cls(
            id=str(uuid.uuid4()),
            index_name=index_name,
            index_type=index_type,
            knowledge_base_id=knowledge_base_id,
            index_settings=index_settings or {},
            storage_context=storage_context,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata=metadata or {}
        )
    
    def update_index_settings(self, new_settings: Dict[str, Any]) -> None:
        """更新索引设置
        
        Args:
            new_settings: 新的索引设置
        """
        if isinstance(self.index_settings, dict) and isinstance(new_settings, dict):
            # 合并设置，保留现有未覆盖的值
            self.index_settings.update(new_settings)
        else:
            # 如果现有设置不是字典或新设置不是字典，则直接替换
            self.index_settings = new_settings
        
        self.updated_at = func.now()
    
    def update_storage_context(self, new_context: Dict[str, Any]) -> None:
        """更新存储上下文配置
        
        Args:
            new_context: 新的存储上下文配置
        """
        self.storage_context = new_context
        self.updated_at = func.now()
