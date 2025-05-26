"""
工具历史记录 - 前端路由模块
提供子问题拆分和问答路由绑定历史记录的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

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
from app.api.frontend.responses import ResponseFormatter

# 创建路由器
router = APIRouter()

# ==================== 子问题拆分历史记录API ====================

@router.post("/subquestions", summary="创建子问题拆分记录")
async def create_subquestion_record(
    data: SubQuestionRecordCreate,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    创建子问题拆分记录
    
    记录子问题拆分的过程和结果
    """
    try:
        record = await service.create_subquestion_record(data)
        return ResponseFormatter.format_success(
            data=record,
            message="子问题拆分记录创建成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建记录失败: {str(e)}",
            code=500
        )

@router.get("/subquestions", summary="获取子问题拆分记录列表")
async def list_subquestion_records(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取子问题拆分记录列表
    
    支持按智能体ID和会话ID筛选
    """
    try:
        result = await service.list_subquestion_records(
            agent_id=agent_id,
            session_id=session_id,
            skip=skip,
            limit=limit
        )
        return ResponseFormatter.format_success(
            data=result,
            message="获取子问题拆分记录列表成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取记录列表失败: {str(e)}",
            code=500
        )

@router.get("/subquestions/{record_id}", summary="获取子问题拆分记录")
async def get_subquestion_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取子问题拆分记录详情
    """
    try:
        record = await service.get_subquestion_record(record_id)
        if not record:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=record,
            message="获取子问题拆分记录成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取记录失败: {str(e)}",
            code=500
        )

@router.put("/subquestions/{record_id}/final-answer", summary="更新子问题最终答案")
async def update_subquestion_final_answer(
    record_id: str,
    answer: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    更新子问题最终答案
    
    在子问题处理完成后更新最终答案
    """
    try:
        record = await service.update_subquestion_final_answer(record_id, answer)
        if not record:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=record,
            message="最终答案更新成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"更新答案失败: {str(e)}",
            code=500
        )

@router.delete("/subquestions/{record_id}", summary="删除子问题拆分记录")
async def delete_subquestion_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    删除子问题拆分记录
    """
    try:
        success = await service.delete_subquestion_record(record_id)
        if not success:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"record_id": record_id},
            message="记录已删除"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除记录失败: {str(e)}",
            code=500
        )

# ==================== 问答路由历史记录API ====================

@router.post("/qa-routes", summary="创建问答路由记录")
async def create_qa_route_record(
    data: QARouteRecordCreate,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    创建问答路由记录
    
    记录问答路由的过程和结果
    """
    try:
        record = await service.create_qa_route_record(data)
        return ResponseFormatter.format_success(
            data=record,
            message="问答路由记录创建成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建记录失败: {str(e)}",
            code=500
        )

@router.get("/qa-routes", summary="获取问答路由记录列表")
async def list_qa_route_records(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取问答路由记录列表
    
    支持按智能体ID和会话ID筛选
    """
    try:
        result = await service.list_qa_route_records(
            agent_id=agent_id,
            session_id=session_id,
            skip=skip,
            limit=limit
        )
        return ResponseFormatter.format_success(
            data=result,
            message="获取问答路由记录列表成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取记录列表失败: {str(e)}",
            code=500
        )

@router.get("/qa-routes/{record_id}", summary="获取问答路由记录")
async def get_qa_route_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取问答路由记录详情
    """
    try:
        record = await service.get_qa_route_record(record_id)
        if not record:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=record,
            message="获取问答路由记录成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取记录失败: {str(e)}",
            code=500
        )

@router.delete("/qa-routes/{record_id}", summary="删除问答路由记录")
async def delete_qa_route_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    删除问答路由记录
    """
    try:
        success = await service.delete_qa_route_record(record_id)
        if not success:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"record_id": record_id},
            message="记录已删除"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除记录失败: {str(e)}",
            code=500
        )

# ==================== 查询处理历史记录API ====================

@router.post("/process-queries", summary="创建查询处理记录")
async def create_process_query_record(
    data: ProcessQueryRecordCreate,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    创建查询处理记录
    
    记录查询处理的过程和结果
    """
    try:
        record = await service.create_process_query_record(data)
        return ResponseFormatter.format_success(
            data=record,
            message="查询处理记录创建成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建记录失败: {str(e)}",
            code=500
        )

@router.get("/process-queries", summary="获取查询处理记录列表")
async def list_process_query_records(
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取查询处理记录列表
    
    支持按智能体ID和会话ID筛选
    """
    try:
        result = await service.list_process_query_records(
            agent_id=agent_id,
            session_id=session_id,
            skip=skip,
            limit=limit
        )
        return ResponseFormatter.format_success(
            data=result,
            message="获取查询处理记录列表成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取记录列表失败: {str(e)}",
            code=500
        )

@router.get("/process-queries/{record_id}", summary="获取查询处理记录")
async def get_process_query_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取查询处理记录详情
    """
    try:
        record = await service.get_process_query_record(record_id)
        if not record:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=record,
            message="获取查询处理记录成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取记录失败: {str(e)}",
            code=500
        )

@router.delete("/process-queries/{record_id}", summary="删除查询处理记录")
async def delete_process_query_record(
    record_id: str,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    删除查询处理记录
    """
    try:
        success = await service.delete_process_query_record(record_id)
        if not success:
            return ResponseFormatter.format_error(
                message="记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"record_id": record_id},
            message="记录已删除"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除记录失败: {str(e)}",
            code=500
        )

# ==================== 工具统计API ====================

@router.get("/stats", summary="获取工具使用统计")
async def get_tools_stats(
    agent_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    service: BaseToolsService = Depends(get_base_tools_service)
):
    """
    获取工具使用统计数据
    
    支持按智能体ID和时间范围筛选
    """
    try:
        stats = {
            "subquestion_count": await service.count_subquestion_records(agent_id, start_date, end_date),
            "qa_route_count": await service.count_qa_route_records(agent_id, start_date, end_date),
            "process_query_count": await service.count_process_query_records(agent_id, start_date, end_date),
            "agent_stats": await service.get_agent_stats(start_date, end_date) if not agent_id else None
        }
        
        return ResponseFormatter.format_success(
            data=stats,
            message="获取工具统计数据成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取统计数据失败: {str(e)}",
            code=500
        ) 