"""
[✅ 已迁移] 此文件已完成重构和迁移到 app/api/frontend/tools/history.py
基础工具历史记录API桥接文件
(已弃用) - 请使用 app.api.frontend.tools.history 模块
此文件仅用于向后兼容，所有新代码都应该使用新的模块
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

from app.utils.database import get_db
from app.services.base_tools_service import BaseToolsService, get_base_tools_service
from app.schemas.base_tools import (
    SubQuestionRecordCreate,
    SubQuestionRecordResponse,
    SubQuestionRecordList,
    QARouteRecordCreate,
    QARouteRecordResponse,
    QARouteRecordList,
    ProcessQueryRecordCreate,
    ProcessQueryRecordResponse,
    ProcessQueryRecordList,
    BaseToolsStats
)

# 导入新的工具历史记录路由处理函数
from app.api.frontend.tools.history import (
    create_subquestion_record as new_create_subquestion_record,
    list_subquestion_records as new_list_subquestion_records,
    get_subquestion_record as new_get_subquestion_record,
    update_subquestion_final_answer as new_update_subquestion_final_answer,
    delete_subquestion_record as new_delete_subquestion_record,
    create_qa_route_record as new_create_qa_route_record,
    list_qa_route_records as new_list_qa_route_records,
    get_qa_route_record as new_get_qa_route_record,
    delete_qa_route_record as new_delete_qa_route_record,
    create_process_query_record as new_create_process_query_record,
    list_process_query_records as new_list_process_query_records,
    get_process_query_record as new_get_process_query_record,
    delete_process_query_record as new_delete_process_query_record,
    get_tools_stats as new_get_tools_stats
)

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/tools/history",
    tags=["base_tools_history"],
    responses={404: {"description": "Not found"}},
)

# ==================== 子问题拆分历史记录API ====================

@router.post("/subquestions", response_model=SubQuestionRecordResponse)
async def create_subquestion_record(
    data: SubQuestionRecordCreate,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """创建子问题拆分记录"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/subquestions，应使用新的端点: /api/frontend/tools/history/subquestions"
    )
    return await new_create_subquestion_record(data=data, service=service)

@router.get("/subquestions", response_model=SubQuestionRecordList)
async def list_subquestion_records(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取子问题拆分记录列表"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/subquestions，应使用新的端点: /api/frontend/tools/history/subquestions"
    )
    return await new_list_subquestion_records(
        agent_id=agent_id,
        session_id=session_id,
        skip=skip,
        limit=limit,
        service=service
    )

@router.get("/subquestions/{record_id}", response_model=SubQuestionRecordResponse)
async def get_subquestion_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取子问题拆分记录"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/subquestions/{record_id}，应使用新的端点: /api/frontend/tools/history/subquestions/{record_id}"
    )
    return await new_get_subquestion_record(record_id=record_id, service=service)

@router.put("/subquestions/{record_id}/final-answer", response_model=SubQuestionRecordResponse)
async def update_subquestion_final_answer(
    record_id: str,
    answer: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """更新子问题最终答案"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/subquestions/{record_id}/final-answer，应使用新的端点: /api/frontend/tools/history/subquestions/{record_id}/final-answer"
    )
    return await new_update_subquestion_final_answer(record_id=record_id, answer=answer, service=service)

@router.delete("/subquestions/{record_id}")
async def delete_subquestion_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """删除子问题拆分记录"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/subquestions/{record_id}，应使用新的端点: /api/frontend/tools/history/subquestions/{record_id}"
    )
    return await new_delete_subquestion_record(record_id=record_id, service=service)

# ==================== 问答路由历史记录API ====================

@router.post("/qa-routes", response_model=QARouteRecordResponse)
async def create_qa_route_record(
    data: QARouteRecordCreate,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """创建问答路由记录"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/qa-routes，应使用新的端点: /api/frontend/tools/history/qa-routes"
    )
    return await new_create_qa_route_record(data=data, service=service)

@router.get("/qa-routes", response_model=QARouteRecordList)
async def list_qa_route_records(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取问答路由记录列表"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/qa-routes，应使用新的端点: /api/frontend/tools/history/qa-routes"
    )
    return await new_list_qa_route_records(
        agent_id=agent_id,
        session_id=session_id,
        skip=skip,
        limit=limit,
        service=service
    )

@router.get("/qa-routes/{record_id}", response_model=QARouteRecordResponse)
async def get_qa_route_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取问答路由记录"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/qa-routes/{record_id}，应使用新的端点: /api/frontend/tools/history/qa-routes/{record_id}"
    )
    return await new_get_qa_route_record(record_id=record_id, service=service)

@router.delete("/qa-routes/{record_id}")
async def delete_qa_route_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """删除问答路由记录"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/qa-routes/{record_id}，应使用新的端点: /api/frontend/tools/history/qa-routes/{record_id}"
    )
    return await new_delete_qa_route_record(record_id=record_id, service=service)

# ==================== 查询处理历史记录API ====================

@router.post("/process-queries", response_model=ProcessQueryRecordResponse)
async def create_process_query_record(
    data: ProcessQueryRecordCreate,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """创建查询处理记录"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/process-queries，应使用新的端点: /api/frontend/tools/history/process-queries"
    )
    return await new_create_process_query_record(data=data, service=service)

@router.get("/process-queries", response_model=ProcessQueryRecordList)
async def list_process_query_records(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取查询处理记录列表"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/process-queries，应使用新的端点: /api/frontend/tools/history/process-queries"
    )
    return await new_list_process_query_records(
        agent_id=agent_id,
        session_id=session_id,
        skip=skip,
        limit=limit,
        service=service
    )

@router.get("/process-queries/{record_id}", response_model=ProcessQueryRecordResponse)
async def get_process_query_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取查询处理记录"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/process-queries/{record_id}，应使用新的端点: /api/frontend/tools/history/process-queries/{record_id}"
    )
    return await new_get_process_query_record(record_id=record_id, service=service)

@router.delete("/process-queries/{record_id}")
async def delete_process_query_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """删除查询处理记录"""
    logger.warning(
        f"使用已弃用的工具历史记录端点: /tools/history/process-queries/{record_id}，应使用新的端点: /api/frontend/tools/history/process-queries/{record_id}"
    )
    return await new_delete_process_query_record(record_id=record_id, service=service)

# ==================== 工具统计API ====================

@router.get("/stats")
async def get_tools_stats(
    agent_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """获取工具使用统计"""
    logger.warning(
        "使用已弃用的工具历史记录端点: /tools/history/stats，应使用新的端点: /api/frontend/tools/history/stats"
    )
    return await new_get_tools_stats(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date,
        service=service
    )
