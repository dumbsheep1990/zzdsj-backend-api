"""
基础工具服务层
已重构为使用核心业务逻辑层，遵循分层架构原则

提供子问题拆分和问答路由绑定相关的业务逻辑。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from fastapi import Depends
import logging

from app.utils.database import get_db
# 导入核心业务逻辑层
from app.repositories.tool_repository import ToolRepository
from core.tools import ToolManager
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
    """基础工具服务 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, db: Session = Depends(get_db)):
        """初始化
        
        Args:
            db: 数据库会话
        """
        self.db = db
        # 使用核心业务逻辑层
        self.tool_manager = ToolManager(db)
        
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
            
            # 使用核心层创建工具记录 (以子问题记录的形式)
            tool_data = {
                "name": f"subquestion_{record_data.get('id', 'unknown')}",
                "description": "子问题拆分记录",
                "tool_type": "subquestion",
                "config": record_data,
                "category": "subquestion",
                "metadata": {
                    "type": "subquestion_record",
                    "agent_id": record_data.get("agent_id"),
                    "session_id": record_data.get("session_id")
                }
            }
            
            result = await self.tool_manager.create_tool(**tool_data)
            if result["success"]:
                # 转换回子问题记录格式
                tool_record = result["data"]
                subquestion_record = {
                    "id": tool_record["id"],
                    **tool_record["config"]
                }
                
                # 创建响应对象
                class MockRecord:
                    def __init__(self, data):
                        for k, v in data.items():
                            setattr(self, k, v)
                
                mock_record = MockRecord(subquestion_record)
                return SubQuestionRecordResponse.from_orm(mock_record)
            else:
                raise Exception(result["error"])
                
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
        result = await self.tool_manager.get_tool(record_id)
        if not result["success"]:
            return None
            
        tool_data = result["data"]
        if tool_data.get("tool_type") != "subquestion":
            return None
            
        # 转换为子问题记录格式
        subquestion_record = {
            "id": tool_data["id"],
            **tool_data["config"]
        }
        
        class MockRecord:
            def __init__(self, data):
                for k, v in data.items():
                    setattr(self, k, v)
        
        mock_record = MockRecord(subquestion_record)
        return SubQuestionRecordResponse.from_orm(mock_record)
        
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
        # 使用核心层获取子问题类型的工具
        result = await self.tool_manager.list_tools(
            skip=skip, 
            limit=limit, 
            tool_type="subquestion"
        )
        
        if not result["success"]:
            return SubQuestionRecordList(items=[], total=0)
        
        tools = result["data"]["tools"]
        total = result["data"]["total"]
        
        # 过滤并转换为子问题记录
        filtered_records = []
        for tool_data in tools:
            metadata = tool_data.get("metadata", {})
            
            # 应用过滤条件
            if agent_id and metadata.get("agent_id") != agent_id:
                continue
            if session_id and metadata.get("session_id") != session_id:
                continue
                
            # 转换为子问题记录格式
            subquestion_record = {
                "id": tool_data["id"],
                **tool_data["config"]
            }
            
            class MockRecord:
                def __init__(self, data):
                    for k, v in data.items():
                        setattr(self, k, v)
            
            mock_record = MockRecord(subquestion_record)
            filtered_records.append(SubQuestionRecordResponse.from_orm(mock_record))
        
        return SubQuestionRecordList(
            items=filtered_records,
            total=len(filtered_records)
        )
        
    async def update_subquestion_final_answer(self, record_id: str, answer: str) -> Optional[SubQuestionRecordResponse]:
        """更新子问题最终答案
        
        Args:
            record_id: 记录ID
            answer: 答案内容
            
        Returns:
            更新后的记录
        """
        # 获取现有记录
        result = await self.tool_manager.get_tool(record_id)
        if not result["success"]:
            return None
            
        tool_data = result["data"]
        if tool_data.get("tool_type") != "subquestion":
            return None
        
        # 更新配置中的最终答案
        updated_config = tool_data["config"].copy()
        updated_config["final_answer"] = answer
        
        # 使用核心层更新工具
        update_result = await self.tool_manager.update_tool(record_id, {
            "config": updated_config
        })
        
        if update_result["success"]:
            return await self.get_subquestion_record(record_id)
        
        return None
        
    async def delete_subquestion_record(self, record_id: str) -> bool:
        """删除子问题拆分记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        result = await self.tool_manager.delete_tool(record_id)
        return result.get("success", False)
        
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
            
            # 使用核心层创建工具记录 (以问答路由记录的形式)
            tool_data = {
                "name": f"qa_route_{record_data.get('id', 'unknown')}",
                "description": "问答路由记录",
                "tool_type": "qa_route",
                "config": record_data,
                "category": "qa_route",
                "metadata": {
                    "type": "qa_route_record",
                    "agent_id": record_data.get("agent_id"),
                    "session_id": record_data.get("session_id")
                }
            }
            
            result = await self.tool_manager.create_tool(**tool_data)
            if result["success"]:
                # 转换回问答路由记录格式
                tool_record = result["data"]
                qa_route_record = {
                    "id": tool_record["id"],
                    **tool_record["config"]
                }
                
                class MockRecord:
                    def __init__(self, data):
                        for k, v in data.items():
                            setattr(self, k, v)
                
                mock_record = MockRecord(qa_route_record)
                return QARouteRecordResponse.from_orm(mock_record)
            else:
                raise Exception(result["error"])
                
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
        result = await self.tool_manager.get_tool(record_id)
        if not result["success"]:
            return None
            
        tool_data = result["data"]
        if tool_data.get("tool_type") != "qa_route":
            return None
            
        # 转换为问答路由记录格式
        qa_route_record = {
            "id": tool_data["id"],
            **tool_data["config"]
        }
        
        class MockRecord:
            def __init__(self, data):
                for k, v in data.items():
                    setattr(self, k, v)
        
        mock_record = MockRecord(qa_route_record)
        return QARouteRecordResponse.from_orm(mock_record)
        
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
        # 使用核心层获取问答路由类型的工具
        result = await self.tool_manager.list_tools(
            skip=skip, 
            limit=limit, 
            tool_type="qa_route"
        )
        
        if not result["success"]:
            return QARouteRecordList(items=[], total=0)
        
        tools = result["data"]["tools"]
        total = result["data"]["total"]
        
        # 过滤并转换为问答路由记录
        filtered_records = []
        for tool_data in tools:
            metadata = tool_data.get("metadata", {})
            
            # 应用过滤条件
            if agent_id and metadata.get("agent_id") != agent_id:
                continue
            if session_id and metadata.get("session_id") != session_id:
                continue
                
            # 转换为问答路由记录格式
            qa_route_record = {
                "id": tool_data["id"],
                **tool_data["config"]
            }
            
            class MockRecord:
                def __init__(self, data):
                    for k, v in data.items():
                        setattr(self, k, v)
            
            mock_record = MockRecord(qa_route_record)
            filtered_records.append(QARouteRecordResponse.from_orm(mock_record))
        
        return QARouteRecordList(
            items=filtered_records,
            total=len(filtered_records)
        )
        
    async def delete_qa_route_record(self, record_id: str) -> bool:
        """删除问答路由记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        result = await self.tool_manager.delete_tool(record_id)
        return result.get("success", False)
        
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
            
            # 使用核心层创建工具记录 (以查询处理记录的形式)
            tool_data = {
                "name": f"process_query_{record_data.get('id', 'unknown')}",
                "description": "查询处理记录",
                "tool_type": "process_query",
                "config": record_data,
                "category": "process_query",
                "metadata": {
                    "type": "process_query_record",
                    "agent_id": record_data.get("agent_id"),
                    "session_id": record_data.get("session_id")
                }
            }
            
            result = await self.tool_manager.create_tool(**tool_data)
            if result["success"]:
                # 转换回查询处理记录格式
                tool_record = result["data"]
                process_query_record = {
                    "id": tool_record["id"],
                    **tool_record["config"]
                }
                
                class MockRecord:
                    def __init__(self, data):
                        for k, v in data.items():
                            setattr(self, k, v)
                
                mock_record = MockRecord(process_query_record)
                return ProcessQueryRecordResponse.from_orm(mock_record)
            else:
                raise Exception(result["error"])
                
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
        result = await self.tool_manager.get_tool(record_id)
        if not result["success"]:
            return None
            
        tool_data = result["data"]
        if tool_data.get("tool_type") != "process_query":
            return None
            
        # 转换为查询处理记录格式
        process_query_record = {
            "id": tool_data["id"],
            **tool_data["config"]
        }
        
        class MockRecord:
            def __init__(self, data):
                for k, v in data.items():
                    setattr(self, k, v)
        
        mock_record = MockRecord(process_query_record)
        return ProcessQueryRecordResponse.from_orm(mock_record)
        
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
        # 使用核心层获取查询处理类型的工具
        result = await self.tool_manager.list_tools(
            skip=skip, 
            limit=limit, 
            tool_type="process_query"
        )
        
        if not result["success"]:
            return ProcessQueryRecordList(items=[], total=0)
        
        tools = result["data"]["tools"]
        total = result["data"]["total"]
        
        # 过滤并转换为查询处理记录
        filtered_records = []
        for tool_data in tools:
            metadata = tool_data.get("metadata", {})
            
            # 应用过滤条件
            if agent_id and metadata.get("agent_id") != agent_id:
                continue
            if session_id and metadata.get("session_id") != session_id:
                continue
                
            # 转换为查询处理记录格式
            process_query_record = {
                "id": tool_data["id"],
                **tool_data["config"]
            }
            
            class MockRecord:
                def __init__(self, data):
                    for k, v in data.items():
                        setattr(self, k, v)
            
            mock_record = MockRecord(process_query_record)
            filtered_records.append(ProcessQueryRecordResponse.from_orm(mock_record))
        
        return ProcessQueryRecordList(
            items=filtered_records,
            total=len(filtered_records)
        )
        
    async def delete_process_query_record(self, record_id: str) -> bool:
        """删除查询处理记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否成功
        """
        result = await self.tool_manager.delete_tool(record_id)
        return result.get("success", False)

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
