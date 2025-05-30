"""
基础工具服务层

提供子问题拆分和问答路由绑定相关的业务逻辑。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from fastapi import Depends
import logging

from app.utils.database import get_db
from app.repositories.base_tools_repository import BaseToolsRepository
from app.schemas.base_tools import (
    SubQuestionRecordCreate,
    SubQuestionRecordResponse,
    SubQuestionRecordList,
    QARouteRecordCreate,
    QARouteRecordResponse,
    QARouteRecordList,
    ProcessQueryRecordCreate,
    ProcessQueryRecordResponse,
    ProcessQueryRecordList
)

logger = logging.getLogger(__name__)

class BaseToolsService:
    """基础工具服务"""
    
    def __init__(self, db: Session = Depends(get_db)):
        """初始化
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = BaseToolsRepository(db)
        
    # ==================== 子问题拆分相关服务 ====================
    
    async def create_subquestion_record(self, data: SubQuestionRecordCreate) -> SubQuestionRecordResponse:
        """创建子问题拆分记录
        
        Args:
            data: 记录数据
            
        Returns:
            创建的记录
        """
        try:
            record_data = data.dict()
            record = self.repository.create_subquestion_record(record_data)
            
            # 转换为响应模型
            return SubQuestionRecordResponse.from_orm(record)
        except Exception as e:
            logger.error(f"创建子问题拆分记录失败: {str(e)}")
            raise
            
    async def get_subquestion_record(self, record_id: str) -> Optional[SubQuestionRecordResponse]:
        """获取子问题拆分记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象
        """
        record = self.repository.get_subquestion_record(record_id)
        if not record:
            return None
            
        return SubQuestionRecordResponse.from_orm(record)
        
    async def list_subquestion_records(self, 
                                     agent_id: Optional[str] = None,
                                     session_id: Optional[str] = None,
                                     skip: int = 0,
                                     limit: int = 20) -> SubQuestionRecordList:
        """获取子问题拆分记录列表
        
        Args:
            agent_id: 智能体ID
            session_id: 会话ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            记录列表和总数
        """
        records, total = self.repository.list_subquestion_records(
            agent_id=agent_id,
            session_id=session_id,
            skip=skip,
            limit=limit
        )
        
        return SubQuestionRecordList(
            items=[SubQuestionRecordResponse.from_orm(record) for record in records],
            total=total
        )
        
    async def update_subquestion_final_answer(self, record_id: str, answer: str) -> Optional[SubQuestionRecordResponse]:
        """更新子问题最终答案
        
        Args:
            record_id: 记录ID
            answer: 答案内容
            
        Returns:
            更新后的记录
        """
        self.repository.update_subquestion_final_answer(record_id, answer)
        return await self.get_subquestion_record(record_id)
        
    async def delete_subquestion_record(self, record_id: str) -> bool:
        """删除子问题拆分记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        return self.repository.delete_subquestion_record(record_id)
        
    # ==================== 问答路由相关服务 ====================
    
    async def create_qa_route_record(self, data: QARouteRecordCreate) -> QARouteRecordResponse:
        """创建问答路由记录
        
        Args:
            data: 记录数据
            
        Returns:
            创建的记录
        """
        try:
            record_data = data.dict()
            record = self.repository.create_qa_route_record(record_data)
            
            # 转换为响应模型
            return QARouteRecordResponse.from_orm(record)
        except Exception as e:
            logger.error(f"创建问答路由记录失败: {str(e)}")
            raise
            
    async def get_qa_route_record(self, record_id: str) -> Optional[QARouteRecordResponse]:
        """获取问答路由记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象
        """
        record = self.repository.get_qa_route_record(record_id)
        if not record:
            return None
            
        return QARouteRecordResponse.from_orm(record)
        
    async def list_qa_route_records(self, 
                                  agent_id: Optional[str] = None,
                                  session_id: Optional[str] = None,
                                  skip: int = 0,
                                  limit: int = 20) -> QARouteRecordList:
        """获取问答路由记录列表
        
        Args:
            agent_id: 智能体ID
            session_id: 会话ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            记录列表和总数
        """
        records, total = self.repository.list_qa_route_records(
            agent_id=agent_id,
            session_id=session_id,
            skip=skip,
            limit=limit
        )
        
        return QARouteRecordList(
            items=[QARouteRecordResponse.from_orm(record) for record in records],
            total=total
        )
        
    async def delete_qa_route_record(self, record_id: str) -> bool:
        """删除问答路由记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        return self.repository.delete_qa_route_record(record_id)
        
    # ==================== 查询处理相关服务 ====================
    
    async def create_process_query_record(self, data: ProcessQueryRecordCreate) -> ProcessQueryRecordResponse:
        """创建查询处理记录
        
        Args:
            data: 记录数据
            
        Returns:
            创建的记录
        """
        try:
            record_data = data.dict()
            record = self.repository.create_process_query_record(record_data)
            
            # 转换为响应模型
            return ProcessQueryRecordResponse.from_orm(record)
        except Exception as e:
            logger.error(f"创建查询处理记录失败: {str(e)}")
            raise
            
    async def get_process_query_record(self, record_id: str) -> Optional[ProcessQueryRecordResponse]:
        """获取查询处理记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象
        """
        record = self.repository.get_process_query_record(record_id)
        if not record:
            return None
            
        return ProcessQueryRecordResponse.from_orm(record)
        
    async def list_process_query_records(self, 
                                      agent_id: Optional[str] = None,
                                      session_id: Optional[str] = None,
                                      skip: int = 0,
                                      limit: int = 20) -> ProcessQueryRecordList:
        """获取查询处理记录列表
        
        Args:
            agent_id: 智能体ID
            session_id: 会话ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            记录列表和总数
        """
        records, total = self.repository.list_process_query_records(
            agent_id=agent_id,
            session_id=session_id,
            skip=skip,
            limit=limit
        )
        
        return ProcessQueryRecordList(
            items=[ProcessQueryRecordResponse.from_orm(record) for record in records],
            total=total
        )
        
    async def delete_process_query_record(self, record_id: str) -> bool:
        """删除查询处理记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        return self.repository.delete_process_query_record(record_id)

# 服务实例获取函数
_base_tools_service_instance = None

def get_base_tools_service(db: Session = Depends(get_db)) -> BaseToolsService:
    """获取基础工具服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        基础工具服务实例
    """
    return BaseToolsService(db)
