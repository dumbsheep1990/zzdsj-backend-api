"""
基础工具系统数据库模型

定义子问题拆分和问答路由绑定相关的数据库模型。
"""

from sqlalchemy import Column, String, JSON, Boolean, Integer, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.utils.database import Base

def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4())

class SubQuestionRecord(Base):
    """子问题拆分记录表
    
    记录子问题拆分的历史记录，包括原始问题、拆分结果、执行顺序等。
    """
    __tablename__ = "base_tool_subquestion_records"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    agent_id = Column(String(36), index=True, nullable=True)
    session_id = Column(String(36), index=True, nullable=True)
    
    original_question = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    mode = Column(String(20), nullable=False, default="basic")
    execution_order = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联子问题
    subquestions = relationship("SubQuestion", back_populates="record", cascade="all, delete-orphan")
    
    # 关联最终答案
    final_answer = relationship("SubQuestionFinalAnswer", uselist=False, back_populates="record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SubQuestionRecord id={self.id} original_question={self.original_question[:30]}...>"

class SubQuestion(Base):
    """子问题表
    
    存储子问题详情，包括子问题内容、答案、搜索结果等。
    """
    __tablename__ = "base_tool_subquestions"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    record_id = Column(String(36), ForeignKey("base_tool_subquestion_records.id", ondelete="CASCADE"), nullable=False)
    
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending") # pending, processing, completed, failed
    search_results = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联记录
    record = relationship("SubQuestionRecord", back_populates="subquestions")
    
    def __repr__(self):
        return f"<SubQuestion id={self.id} question={self.question[:30]}...>"

class SubQuestionFinalAnswer(Base):
    """子问题最终答案表
    
    存储基于子问题回答合成的最终答案。
    """
    __tablename__ = "base_tool_subquestion_final_answers"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    record_id = Column(String(36), ForeignKey("base_tool_subquestion_records.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联记录
    record = relationship("SubQuestionRecord", back_populates="final_answer")
    
    def __repr__(self):
        return f"<SubQuestionFinalAnswer id={self.id} answer={self.answer[:30]}...>"

class QARouteRecord(Base):
    """问答路由记录表
    
    记录问答路由的历史记录，包括原始问题、路由结果、选中的知识库等。
    """
    __tablename__ = "base_tool_qa_route_records"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    agent_id = Column(String(36), index=True, nullable=True)
    session_id = Column(String(36), index=True, nullable=True)
    
    original_query = Column(Text, nullable=False)
    processed_query = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    mode = Column(String(20), nullable=False, default="sequential")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联选中的知识库
    selected_knowledge_bases = relationship("QARouteKnowledgeBase", back_populates="route_record", cascade="all, delete-orphan")
    
    # 关联搜索结果
    search_results = relationship("QARouteSearchResult", back_populates="route_record", cascade="all, delete-orphan")
    
    # 关联QA对匹配
    qa_pair_match = relationship("QARoutePairMatch", uselist=False, back_populates="route_record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<QARouteRecord id={self.id} original_query={self.original_query[:30]}...>"

class QARouteKnowledgeBase(Base):
    """问答路由知识库表
    
    存储路由选中的知识库信息，包括知识库ID、名称、置信度等。
    """
    __tablename__ = "base_tool_qa_route_knowledge_bases"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    route_record_id = Column(String(36), ForeignKey("base_tool_qa_route_records.id", ondelete="CASCADE"), nullable=False)
    
    kb_id = Column(String(36), nullable=False, index=True)
    kb_name = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True, default=1.0)
    order = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联路由记录
    route_record = relationship("QARouteRecord", back_populates="selected_knowledge_bases")
    
    def __repr__(self):
        return f"<QARouteKnowledgeBase id={self.id} kb_id={self.kb_id}>"

class QARouteSearchResult(Base):
    """问答路由搜索结果表
    
    存储路由后执行搜索的结果信息。
    """
    __tablename__ = "base_tool_qa_route_search_results"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    route_record_id = Column(String(36), ForeignKey("base_tool_qa_route_records.id", ondelete="CASCADE"), nullable=False)
    
    doc_id = Column(String(100), nullable=False)
    kb_id = Column(String(36), nullable=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    score = Column(Float, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联路由记录
    route_record = relationship("QARouteRecord", back_populates="search_results")
    
    def __repr__(self):
        return f"<QARouteSearchResult id={self.id} doc_id={self.doc_id}>"

class QARoutePairMatch(Base):
    """问答路由QA对匹配表
    
    存储路由匹配到的问答对信息。
    """
    __tablename__ = "base_tool_qa_route_pair_matches"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    route_record_id = Column(String(36), ForeignKey("base_tool_qa_route_records.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    qa_id = Column(String(36), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联路由记录
    route_record = relationship("QARouteRecord", back_populates="qa_pair_match")
    
    def __repr__(self):
        return f"<QARoutePairMatch id={self.id} qa_id={self.qa_id}>"

class ProcessQueryRecord(Base):
    """查询处理记录表
    
    记录综合查询处理的历史记录，包括子问题拆分和问答路由的结果。
    """
    __tablename__ = "base_tool_process_query_records"
    
    id = Column(String(36), primary_key=True, index=True, default=generate_uuid)
    agent_id = Column(String(36), index=True, nullable=True)
    session_id = Column(String(36), index=True, nullable=True)
    
    original_query = Column(Text, nullable=False)
    processed_query = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    
    subquestion_record_id = Column(String(36), ForeignKey("base_tool_subquestion_records.id", ondelete="SET NULL"), nullable=True)
    qa_route_record_id = Column(String(36), ForeignKey("base_tool_qa_route_records.id", ondelete="SET NULL"), nullable=True)
    
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联子问题记录
    subquestion_record = relationship("SubQuestionRecord")
    
    # 关联问答路由记录
    qa_route_record = relationship("QARouteRecord")
    
    def __repr__(self):
        return f"<ProcessQueryRecord id={self.id} original_query={self.original_query[:30]}...>"
