"""
知识图谱数据模型
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from app.utils.core.database.base import Base

class KnowledgeGraph(Base):
    """知识图谱数据模型"""
    
    __tablename__ = "knowledge_graphs"
    
    # 基础字段
    id = Column(String(255), primary_key=True, index=True, comment="图谱唯一标识")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="创建用户ID")
    name = Column(String(255), nullable=False, comment="图谱名称")
    description = Column(Text, comment="图谱描述")
    
    # 关联字段
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True, index=True, comment="关联知识库ID")
    
    # 状态字段
    status = Column(String(50), nullable=False, default="created", index=True, comment="处理状态")
    
    # 配置字段
    extraction_config = Column(JSON, nullable=False, default={}, comment="实体提取配置")
    visualization_config = Column(JSON, nullable=False, default={}, comment="可视化配置")
    
    # 访问控制
    is_public = Column(Boolean, default=False, index=True, comment="是否公开")
    
    # 标签和分类
    tags = Column(ARRAY(String), default=[], comment="标签列表")
    
    # 时间字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 源文件信息
    source_files = Column(ARRAY(String), default=[], comment="源文件路径列表")
    
    # 统计信息（冗余存储，提高查询性能）
    entity_count = Column(Integer, default=0, comment="实体数量")
    relation_count = Column(Integer, default=0, comment="关系数量")
    file_count = Column(Integer, default=0, comment="文件数量")
    
    # 关系定义
    user = relationship("User", back_populates="knowledge_graphs")
    knowledge_base = relationship("KnowledgeBase", back_populates="knowledge_graphs")
    
    def __repr__(self):
        return f"<KnowledgeGraph(id='{self.id}', name='{self.name}', status='{self.status}')>"
    
    class Config:
        from_attributes = True 