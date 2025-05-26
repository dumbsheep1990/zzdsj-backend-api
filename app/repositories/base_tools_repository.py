"""
基础工具数据访问层

提供子问题拆分和问答路由绑定相关的数据库操作。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
import json

from app.models.base_tools import (
    SubQuestionRecord,
    SubQuestion,
    SubQuestionFinalAnswer,
    QARouteRecord,
    QARouteKnowledgeBase,
    QARouteSearchResult,
    QARoutePairMatch,
    ProcessQueryRecord
)

class BaseToolsRepository:
    """基础工具数据访问层"""
    
    def __init__(self, db: Session):
        """初始化
        
        Args:
            db: 数据库会话
        """
        self.db = db
        
    # ==================== 子问题拆分相关操作 ====================
    
    def create_subquestion_record(self, data: Dict[str, Any]) -> SubQuestionRecord:
        """创建子问题拆分记录
        
        Args:
            data: 记录数据
            
        Returns:
            创建的记录
        """
        record = SubQuestionRecord(**{k: v for k, v in data.items() 
                                    if k in ['id', 'agent_id', 'session_id', 'original_question', 
                                            'reasoning', 'mode', 'execution_order']})
        
        self.db.add(record)
        self.db.flush()
        
        # 创建子问题
        if 'subquestions' in data and isinstance(data['subquestions'], list):
            for i, sq_data in enumerate(data['subquestions']):
                sq = SubQuestion(
                    record_id=record.id,
                    order=i,
                    **{k: v for k, v in sq_data.items() 
                      if k in ['id', 'question', 'answer', 'status', 'search_results']}
                )
                self.db.add(sq)
                
        # 创建最终答案
        if 'final_answer' in data and data['final_answer']:
            final_answer = SubQuestionFinalAnswer(
                record_id=record.id,
                answer=data['final_answer']
            )
            self.db.add(final_answer)
            
        self.db.commit()
        self.db.refresh(record)
        return record
        
    def get_subquestion_record(self, record_id: str) -> Optional[SubQuestionRecord]:
        """获取子问题拆分记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象
        """
        return self.db.query(SubQuestionRecord).filter(SubQuestionRecord.id == record_id).first()
        
    def list_subquestion_records(self, 
                               agent_id: Optional[str] = None,
                               session_id: Optional[str] = None,
                               skip: int = 0,
                               limit: int = 20) -> Tuple[List[SubQuestionRecord], int]:
        """获取子问题拆分记录列表
        
        Args:
            agent_id: 智能体ID
            session_id: 会话ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            记录列表和总数
        """
        query = self.db.query(SubQuestionRecord)
        
        # 应用过滤条件
        if agent_id:
            query = query.filter(SubQuestionRecord.agent_id == agent_id)
        if session_id:
            query = query.filter(SubQuestionRecord.session_id == session_id)
            
        # 获取总数
        total = query.count()
        
        # 应用分页并排序
        query = query.order_by(desc(SubQuestionRecord.created_at)).offset(skip).limit(limit)
        
        return query.all(), total
        
    def update_subquestion(self, subquestion_id: str, data: Dict[str, Any]) -> Optional[SubQuestion]:
        """更新子问题
        
        Args:
            subquestion_id: 子问题ID
            data: 更新数据
            
        Returns:
            更新后的子问题
        """
        subquestion = self.db.query(SubQuestion).filter(SubQuestion.id == subquestion_id).first()
        if not subquestion:
            return None
            
        for key, value in data.items():
            if hasattr(subquestion, key):
                setattr(subquestion, key, value)
                
        self.db.commit()
        self.db.refresh(subquestion)
        return subquestion
        
    def update_subquestion_final_answer(self, record_id: str, answer: str) -> Optional[SubQuestionFinalAnswer]:
        """更新或创建子问题最终答案
        
        Args:
            record_id: 记录ID
            answer: 答案内容
            
        Returns:
            最终答案对象
        """
        final_answer = self.db.query(SubQuestionFinalAnswer).filter(
            SubQuestionFinalAnswer.record_id == record_id
        ).first()
        
        if final_answer:
            # 更新现有答案
            final_answer.answer = answer
        else:
            # 创建新答案
            final_answer = SubQuestionFinalAnswer(
                record_id=record_id,
                answer=answer
            )
            self.db.add(final_answer)
            
        self.db.commit()
        self.db.refresh(final_answer)
        return final_answer
        
    def delete_subquestion_record(self, record_id: str) -> bool:
        """删除子问题拆分记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        record = self.db.query(SubQuestionRecord).filter(SubQuestionRecord.id == record_id).first()
        if not record:
            return False
            
        self.db.delete(record)
        self.db.commit()
        return True
        
    # ==================== 问答路由相关操作 ====================
    
    def create_qa_route_record(self, data: Dict[str, Any]) -> QARouteRecord:
        """创建问答路由记录
        
        Args:
            data: 记录数据
            
        Returns:
            创建的记录
        """
        record = QARouteRecord(**{k: v for k, v in data.items() 
                                if k in ['id', 'agent_id', 'session_id', 'original_query', 
                                        'processed_query', 'reasoning', 'mode']})
        
        self.db.add(record)
        self.db.flush()
        
        # 创建选中的知识库
        if 'selected_knowledge_bases' in data and isinstance(data['selected_knowledge_bases'], list):
            for i, kb_data in enumerate(data['selected_knowledge_bases']):
                kb = QARouteKnowledgeBase(
                    route_record_id=record.id,
                    order=i,
                    **{k: v for k, v in kb_data.items() 
                      if k in ['kb_id', 'kb_name', 'confidence']}
                )
                self.db.add(kb)
                
        # 创建搜索结果
        if 'search_results' in data and isinstance(data['search_results'], list):
            for sr_data in data['search_results']:
                sr = QARouteSearchResult(
                    route_record_id=record.id,
                    **{k: v for k, v in sr_data.items() 
                      if k in ['doc_id', 'kb_id', 'title', 'content', 'source', 'score', 'metadata']}
                )
                self.db.add(sr)
                
        # 创建QA对匹配
        if 'qa_pair_match' in data and data['qa_pair_match']:
            qa_match = QARoutePairMatch(
                route_record_id=record.id,
                **{k: v for k, v in data['qa_pair_match'].items() 
                  if k in ['qa_id', 'question', 'answer', 'score']}
            )
            self.db.add(qa_match)
            
        self.db.commit()
        self.db.refresh(record)
        return record
        
    def get_qa_route_record(self, record_id: str) -> Optional[QARouteRecord]:
        """获取问答路由记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象
        """
        return self.db.query(QARouteRecord).filter(QARouteRecord.id == record_id).first()
        
    def list_qa_route_records(self, 
                            agent_id: Optional[str] = None,
                            session_id: Optional[str] = None,
                            skip: int = 0,
                            limit: int = 20) -> Tuple[List[QARouteRecord], int]:
        """获取问答路由记录列表
        
        Args:
            agent_id: 智能体ID
            session_id: 会话ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            记录列表和总数
        """
        query = self.db.query(QARouteRecord)
        
        # 应用过滤条件
        if agent_id:
            query = query.filter(QARouteRecord.agent_id == agent_id)
        if session_id:
            query = query.filter(QARouteRecord.session_id == session_id)
            
        # 获取总数
        total = query.count()
        
        # 应用分页并排序
        query = query.order_by(desc(QARouteRecord.created_at)).offset(skip).limit(limit)
        
        return query.all(), total
        
    def delete_qa_route_record(self, record_id: str) -> bool:
        """删除问答路由记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        record = self.db.query(QARouteRecord).filter(QARouteRecord.id == record_id).first()
        if not record:
            return False
            
        self.db.delete(record)
        self.db.commit()
        return True
        
    # ==================== 查询处理相关操作 ====================
    
    def create_process_query_record(self, data: Dict[str, Any]) -> ProcessQueryRecord:
        """创建查询处理记录
        
        Args:
            data: 记录数据
            
        Returns:
            创建的记录
        """
        record = ProcessQueryRecord(**{k: v for k, v in data.items() 
                                    if k in ['id', 'agent_id', 'session_id', 'original_query',
                                            'processed_query', 'answer', 'subquestion_record_id',
                                            'qa_route_record_id', 'metadata']})
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
        
    def get_process_query_record(self, record_id: str) -> Optional[ProcessQueryRecord]:
        """获取查询处理记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象
        """
        return self.db.query(ProcessQueryRecord).filter(ProcessQueryRecord.id == record_id).first()
        
    def list_process_query_records(self, 
                                agent_id: Optional[str] = None,
                                session_id: Optional[str] = None,
                                skip: int = 0,
                                limit: int = 20) -> Tuple[List[ProcessQueryRecord], int]:
        """获取查询处理记录列表
        
        Args:
            agent_id: 智能体ID
            session_id: 会话ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            记录列表和总数
        """
        query = self.db.query(ProcessQueryRecord)
        
        # 应用过滤条件
        if agent_id:
            query = query.filter(ProcessQueryRecord.agent_id == agent_id)
        if session_id:
            query = query.filter(ProcessQueryRecord.session_id == session_id)
            
        # 获取总数
        total = query.count()
        
        # 应用分页并排序
        query = query.order_by(desc(ProcessQueryRecord.created_at)).offset(skip).limit(limit)
        
        return query.all(), total
        
    def delete_process_query_record(self, record_id: str) -> bool:
        """删除查询处理记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        record = self.db.query(ProcessQueryRecord).filter(ProcessQueryRecord.id == record_id).first()
        if not record:
            return False
            
        self.db.delete(record)
        self.db.commit()
        return True
