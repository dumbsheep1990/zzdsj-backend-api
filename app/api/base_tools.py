"""
[✅ 已迁移] 此文件已完成重构和迁移到 app/api/frontend/tools/base.py
基础工具API桥接文件
(已弃用) - 请使用 app.api.frontend.tools.base 模块
此文件仅用于向后兼容，所有新代码都应该使用新的模块
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any, List, Optional
import logging

from app.tools.base.integrations import (
    BaseToolsIntegration, 
    get_base_tools_integration,
    SubquestionRequest,
    SubquestionResponse,
    QARoutingRequest,
    QARoutingResponse,
    ProcessQueryRequest,
    ProcessQueryResponse
)

# 导入新的基础工具路由处理函数
from app.api.frontend.tools.base import (
    decompose_query as new_decompose_query,
    route_query as new_route_query,
    process_query as new_process_query,
    agent_decompose_query as new_agent_decompose_query,
    agent_route_query as new_agent_route_query,
    agent_process_query as new_agent_process_query
)

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/tools",
    tags=["base_tools"],
    responses={404: {"description": "Not found"}},
)

@router.post("/subquestion/decompose", response_model=SubquestionResponse)
async def decompose_query(
    request: SubquestionRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """拆分查询为子问题"""
    logger.warning(
        "使用已弃用的基础工具端点: /tools/subquestion/decompose，应使用新的端点: /api/frontend/tools/base/subquestion/decompose"
    )
    return await new_decompose_query(request=request, tools_integration=tools_integration)

@router.post("/qa/route", response_model=QARoutingResponse)
async def route_query(
    request: QARoutingRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """为查询选择合适的知识库路由"""
    logger.warning(
        "使用已弃用的基础工具端点: /tools/qa/route，应使用新的端点: /api/frontend/tools/base/qa/route"
    )
    return await new_route_query(request=request, tools_integration=tools_integration)

@router.post("/process", response_model=ProcessQueryResponse)
async def process_query(
    request: ProcessQueryRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """处理查询，应用子问题拆分和问答路由"""
    logger.warning(
        "使用已弃用的基础工具端点: /tools/process，应使用新的端点: /api/frontend/tools/base/process"
    )
    return await new_process_query(request=request, tools_integration=tools_integration)

# 代理层工具集成路由
@router.post("/agents/{agent_id}/subquestion/decompose", response_model=SubquestionResponse)
async def agent_decompose_query(
    agent_id: str,
    request: SubquestionRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """通过代理拆分查询为子问题"""
    logger.warning(
        f"使用已弃用的基础工具端点: /tools/agents/{agent_id}/subquestion/decompose，应使用新的端点: /api/frontend/tools/base/agents/{agent_id}/subquestion/decompose"
    )
    return await new_agent_decompose_query(agent_id=agent_id, request=request, tools_integration=tools_integration)

@router.post("/agents/{agent_id}/qa/route", response_model=QARoutingResponse)
async def agent_route_query(
    agent_id: str,
    request: QARoutingRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """通过代理为查询选择合适的知识库路由"""
    logger.warning(
        f"使用已弃用的基础工具端点: /tools/agents/{agent_id}/qa/route，应使用新的端点: /api/frontend/tools/base/agents/{agent_id}/qa/route"
    )
    return await new_agent_route_query(agent_id=agent_id, request=request, tools_integration=tools_integration)

@router.post("/agents/{agent_id}/process", response_model=ProcessQueryResponse)
async def agent_process_query(
    agent_id: str,
    request: ProcessQueryRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """通过代理处理查询，应用子问题拆分和问答路由"""
    logger.warning(
        f"使用已弃用的基础工具端点: /tools/agents/{agent_id}/process，应使用新的端点: /api/frontend/tools/base/agents/{agent_id}/process"
    )
    return await new_agent_process_query(agent_id=agent_id, request=request, tools_integration=tools_integration)
