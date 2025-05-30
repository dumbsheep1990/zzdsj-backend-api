"""
LightRAG框架集成模型模块
用于管理LightRAG框架的文档处理器、图谱和查询引擎配置
"""

import uuid
from sqlalchemy import Column, String, JSON, Text, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
from typing import Dict, Any, Optional

class LightRAGIntegration(Base):
    """LightRAG框架集成模型"""
    __tablename__ = 'lightrag_integrations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    index_name = Column(String(100), unique=True, nullable=False)  # 索引名称
    document_processor_config = Column(JSON)  # 文档处理器配置
    graph_config = Column(JSON)  # 图谱配置
    query_engine_config = Column(JSON)  # 查询引擎配置
    workdir_path = Column(Text)  # 工作目录路径
    api_key = Column(String(255))  # API密钥
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
            "document_processor_config": self.document_processor_config,
            "graph_config": self.graph_config,
            "query_engine_config": self.query_engine_config,
            "workdir_path": self.workdir_path,
            "api_key": self.api_key,  # 注意：在实际返回中应该隐藏或加密API密钥
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """转换为安全的字典表示（不包含敏感信息）
        
        Returns:
            Dict[str, Any]: 不含敏感信息的字典表示
        """
        result = self.to_dict()
        if "api_key" in result:
            result["api_key"] = "********" if result["api_key"] else None
        return result
    
    @classmethod
    def create(cls, index_name: str,
               document_processor_config: Dict[str, Any] = None,
               graph_config: Dict[str, Any] = None,
               query_engine_config: Dict[str, Any] = None,
               workdir_path: Optional[str] = None,
               api_key: Optional[str] = None) -> 'LightRAGIntegration':
        """创建新的LightRAG框架集成配置
        
        Args:
            index_name: 索引名称
            document_processor_config: 文档处理器配置 (可选)
            graph_config: 图谱配置 (可选)
            query_engine_config: 查询引擎配置 (可选)
            workdir_path: 工作目录路径 (可选)
            api_key: API密钥 (可选)
            
        Returns:
            LightRAGIntegration: 创建的LightRAG框架集成配置实例
        """
        return cls(
            id=str(uuid.uuid4()),
            index_name=index_name,
            document_processor_config=document_processor_config,
            graph_config=graph_config,
            query_engine_config=query_engine_config,
            workdir_path=workdir_path,
            api_key=api_key
        )
    
    def update_document_processor_config(self, new_config: Dict[str, Any]) -> None:
        """更新文档处理器配置
        
        Args:
            new_config: 新的文档处理器配置
        """
        self.document_processor_config = new_config
        self.updated_at = func.now()
    
    def update_graph_config(self, new_config: Dict[str, Any]) -> None:
        """更新图谱配置
        
        Args:
            new_config: 新的图谱配置
        """
        self.graph_config = new_config
        self.updated_at = func.now()
    
    def update_query_engine_config(self, new_config: Dict[str, Any]) -> None:
        """更新查询引擎配置
        
        Args:
            new_config: 新的查询引擎配置
        """
        self.query_engine_config = new_config
        self.updated_at = func.now()
    
    def set_api_key(self, api_key: str) -> None:
        """设置API密钥
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self.updated_at = func.now()


class LightRAGGraph(Base):
    """LightRAG图谱模型"""
    __tablename__ = 'lightrag_graphs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, comment="图谱名称")
    description = Column(Text, comment="图谱描述")
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.id'), comment="关联知识库ID")
    config = Column(JSON, nullable=False, comment="图谱配置")
    status = Column(String(20), default='building', comment="图谱状态: building, ready, error")
    node_count = Column(Integer, default=0, comment="节点数量")
    edge_count = Column(Integer, default=0, comment="边数量")
    last_updated_at = Column(DateTime, comment="最后更新时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    queries = relationship("LightRAGQuery", back_populates="graph", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "knowledge_base_id": self.knowledge_base_id,
            "config": self.config,
            "status": self.status,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class LightRAGQuery(Base):
    """LightRAG查询记录模型"""
    __tablename__ = 'lightrag_queries'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    graph_id = Column(String(36), ForeignKey('lightrag_graphs.id', ondelete='CASCADE'), 
                     nullable=False, comment="图谱ID")
    query_text = Column(Text, nullable=False, comment="查询文本")
    query_type = Column(String(20), nullable=False, comment="查询类型: naive, local, global, hybrid")
    results = Column(JSON, comment="查询结果")
    execution_time_ms = Column(Integer, comment="执行时间(毫秒)")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    # 关系
    graph = relationship("LightRAGGraph", back_populates="queries")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "graph_id": self.graph_id,
            "query_text": self.query_text,
            "query_type": self.query_type,
            "results": self.results,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
