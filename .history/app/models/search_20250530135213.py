"""
搜索管理模型
用于定义搜索会话和搜索结果缓存的数据库模型
"""

import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any
from app.models.database import Base


class SearchSession(Base):
    """搜索会话模型"""
    __tablename__ = 'search_sessions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), comment="用户ID")
    query = Column(Text, nullable=False, comment="搜索查询")
    search_type = Column(String(50), nullable=False, comment="搜索类型: semantic, keyword, hybrid")
    filters = Column(JSON, default={}, comment="搜索过滤器")
    results = Column(JSON, default=[], comment="搜索结果")
    metadata = Column(JSON, default={}, comment="搜索元数据")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "search_type": self.search_type,
            "filters": self.filters,
            "results": self.results,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SearchResultCache(Base):
    """搜索结果缓存模型"""
    __tablename__ = 'search_result_cache'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String(64), unique=True, nullable=False, comment="查询哈希值")
    query_text = Column(Text, nullable=False, comment="查询文本")
    search_type = Column(String(50), nullable=False, comment="搜索类型")
    filters_hash = Column(String(64), comment="过滤器哈希值")
    results = Column(JSON, nullable=False, comment="缓存的搜索结果")
    hit_count = Column(Integer, default=0, comment="缓存命中次数")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    last_accessed_at = Column(DateTime, server_default=func.now(), comment="最后访问时间")
    expires_at = Column(DateTime, comment="过期时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "query_hash": self.query_hash,
            "query_text": self.query_text,
            "search_type": self.search_type,
            "filters_hash": self.filters_hash,
            "results": self.results,
            "hit_count": self.hit_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    def increment_hit_count(self):
        """增加缓存命中次数"""
        self.hit_count += 1
        self.last_accessed_at = func.now()
    
    @property
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if self.expires_at is None:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.expires_at 