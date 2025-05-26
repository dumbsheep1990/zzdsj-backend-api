"""
基础工具系统Pydantic模式

定义子问题拆分和问答路由绑定相关的API请求和响应模式。
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# ==================== 通用模式 ====================

def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4())

class BaseRecord(BaseModel):
    """基础记录模型"""
    id: Optional[str] = Field(default_factory=generate_uuid)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# ==================== 子问题相关模式 ====================

class SubQuestionCreate(BaseModel):
    """子问题创建模式"""
    id: Optional[str] = Field(default_factory=generate_uuid)
    question: str = Field(..., description="子问题内容")
    order: Optional[int] = Field(0, description="执行顺序")
    status: Optional[str] = Field("pending", description="状态")
    answer: Optional[str] = Field(None, description="子问题答案")
    search_results: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="搜索结果")

class SubQuestion(SubQuestionCreate):
    """子问题模式"""
    record_id: str = Field(..., description="记录ID")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class SubQuestionFinalAnswerCreate(BaseModel):
    """子问题最终答案创建模式"""
    answer: str = Field(..., description="最终答案内容")

class SubQuestionFinalAnswer(SubQuestionFinalAnswerCreate):
    """子问题最终答案模式"""
    id: str = Field(..., description="答案ID")
    record_id: str = Field(..., description="记录ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        orm_mode = True

class SubQuestionRecordCreate(BaseModel):
    """子问题拆分记录创建模式"""
    id: Optional[str] = Field(default_factory=generate_uuid)
    agent_id: Optional[str] = Field(None, description="智能体ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    original_question: str = Field(..., description="原始问题")
    reasoning: Optional[str] = Field(None, description="拆分推理过程")
    mode: Optional[str] = Field("basic", description="拆分模式")
    execution_order: Optional[List[str]] = Field(default_factory=list, description="执行顺序")
    subquestions: Optional[List[SubQuestionCreate]] = Field(default_factory=list, description="子问题列表")
    final_answer: Optional[str] = Field(None, description="最终答案")

class SubQuestionRecordResponse(BaseRecord):
    """子问题拆分记录响应模式"""
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    original_question: str
    reasoning: Optional[str] = None
    mode: str
    execution_order: Optional[List[str]] = None
    subquestions: List[SubQuestion] = []
    final_answer: Optional[SubQuestionFinalAnswer] = None
    
    class Config:
        orm_mode = True

class SubQuestionRecordList(BaseModel):
    """子问题拆分记录列表模式"""
    items: List[SubQuestionRecordResponse] = []
    total: int = 0

# ==================== 问答路由相关模式 ====================

class QARouteKnowledgeBaseCreate(BaseModel):
    """问答路由知识库创建模式"""
    kb_id: str = Field(..., description="知识库ID")
    kb_name: Optional[str] = Field(None, description="知识库名称")
    confidence: Optional[float] = Field(1.0, description="置信度")
    order: Optional[int] = Field(0, description="排序顺序")

class QARouteKnowledgeBase(QARouteKnowledgeBaseCreate):
    """问答路由知识库模式"""
    id: str = Field(..., description="记录ID")
    route_record_id: str = Field(..., description="路由记录ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        orm_mode = True

class QARouteSearchResultCreate(BaseModel):
    """问答路由搜索结果创建模式"""
    doc_id: str = Field(..., description="文档ID")
    kb_id: Optional[str] = Field(None, description="知识库ID")
    title: Optional[str] = Field(None, description="文档标题")
    content: Optional[str] = Field(None, description="文档内容")
    source: Optional[str] = Field(None, description="文档来源")
    score: Optional[float] = Field(None, description="相关性得分")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class QARouteSearchResult(QARouteSearchResultCreate):
    """问答路由搜索结果模式"""
    id: str = Field(..., description="记录ID")
    route_record_id: str = Field(..., description="路由记录ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        orm_mode = True

class QARoutePairMatchCreate(BaseModel):
    """问答路由QA对匹配创建模式"""
    qa_id: str = Field(..., description="问答对ID")
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    score: Optional[float] = Field(None, description="匹配得分")

class QARoutePairMatch(QARoutePairMatchCreate):
    """问答路由QA对匹配模式"""
    id: str = Field(..., description="记录ID")
    route_record_id: str = Field(..., description="路由记录ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        orm_mode = True

class QARouteRecordCreate(BaseModel):
    """问答路由记录创建模式"""
    id: Optional[str] = Field(default_factory=generate_uuid)
    agent_id: Optional[str] = Field(None, description="智能体ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    original_query: str = Field(..., description="原始查询")
    processed_query: Optional[str] = Field(None, description="处理后的查询")
    reasoning: Optional[str] = Field(None, description="路由推理过程")
    mode: Optional[str] = Field("sequential", description="路由模式")
    selected_knowledge_bases: Optional[List[QARouteKnowledgeBaseCreate]] = Field(default_factory=list, description="选中的知识库")
    search_results: Optional[List[QARouteSearchResultCreate]] = Field(default_factory=list, description="搜索结果")
    qa_pair_match: Optional[QARoutePairMatchCreate] = Field(None, description="匹配到的问答对")

class QARouteRecordResponse(BaseRecord):
    """问答路由记录响应模式"""
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    original_query: str
    processed_query: Optional[str] = None
    reasoning: Optional[str] = None
    mode: str
    selected_knowledge_bases: List[QARouteKnowledgeBase] = []
    search_results: List[QARouteSearchResult] = []
    qa_pair_match: Optional[QARoutePairMatch] = None
    
    class Config:
        orm_mode = True

class QARouteRecordList(BaseModel):
    """问答路由记录列表模式"""
    items: List[QARouteRecordResponse] = []
    total: int = 0

# ==================== 查询处理相关模式 ====================

class ProcessQueryRecordCreate(BaseModel):
    """查询处理记录创建模式"""
    id: Optional[str] = Field(default_factory=generate_uuid)
    agent_id: Optional[str] = Field(None, description="智能体ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    original_query: str = Field(..., description="原始查询")
    processed_query: Optional[str] = Field(None, description="处理后的查询")
    answer: Optional[str] = Field(None, description="最终答案")
    subquestion_record_id: Optional[str] = Field(None, description="子问题记录ID")
    qa_route_record_id: Optional[str] = Field(None, description="问答路由记录ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ProcessQueryRecordResponse(BaseRecord):
    """查询处理记录响应模式"""
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    original_query: str
    processed_query: Optional[str] = None
    answer: Optional[str] = None
    subquestion_record_id: Optional[str] = None
    qa_route_record_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True

class ProcessQueryRecordList(BaseModel):
    """查询处理记录列表模式"""
    items: List[ProcessQueryRecordResponse] = []
    total: int = 0

# ==================== 统计相关模式 ====================

class BaseToolsStats(BaseModel):
    """基础工具统计信息"""
    total_subquestions: int = Field(0, description="子问题总数")
    total_qa_routes: int = Field(0, description="问答路由总数")
    total_process_queries: int = Field(0, description="查询处理总数")
    avg_subquestions_per_query: float = Field(0.0, description="每个查询的平均子问题数")
    avg_selected_kbs_per_route: float = Field(0.0, description="每个路由的平均选中知识库数")
    qa_pair_match_rate: float = Field(0.0, description="问答对匹配率")
    modes_distribution: Dict[str, int] = Field(default_factory=dict, description="模式分布")
