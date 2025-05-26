"""
基础工具 - 前端路由模块
提供基础工具的REST API接口，包括子问题拆分和问答路由功能
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any, List, Optional

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
from app.api.frontend.responses import ResponseFormatter

# 创建路由器
router = APIRouter()

@router.post("/subquestion/decompose", summary="拆分查询为子问题")
async def decompose_query(
    request: SubquestionRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """
    拆分查询为子问题
    
    将复杂查询拆分为多个简单子问题，便于后续处理
    """
    try:
        result = await tools_integration.decompose_query(request)
        return ResponseFormatter.format_success(
            data=result,
            message="查询成功拆分为子问题"
        )
    except ValueError as e:
        return ResponseFormatter.format_error(
            message=str(e),
            code=400
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"拆分查询失败: {str(e)}",
            code=500
        )

@router.post("/qa/route", summary="为查询选择合适的知识库路由")
async def route_query(
    request: QARoutingRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """
    为查询选择合适的知识库路由
    
    根据查询内容智能选择最合适的知识库进行查询
    """
    try:
        result = await tools_integration.route_query(request)
        return ResponseFormatter.format_success(
            data=result,
            message="成功为查询选择路由"
        )
    except ValueError as e:
        return ResponseFormatter.format_error(
            message=str(e),
            code=400
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"路由查询失败: {str(e)}",
            code=500
        )

@router.post("/process", summary="处理查询，应用子问题拆分和问答路由")
async def process_query(
    request: ProcessQueryRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """
    处理查询，应用子问题拆分和问答路由
    
    综合应用子问题拆分和知识库路由功能，完整处理查询
    """
    try:
        result = await tools_integration.process_query(request)
        return ResponseFormatter.format_success(
            data=result,
            message="查询处理完成"
        )
    except ValueError as e:
        return ResponseFormatter.format_error(
            message=str(e),
            code=400
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"处理查询失败: {str(e)}",
            code=500
        )

# 代理层工具集成路由
@router.post("/agents/{agent_id}/subquestion/decompose", summary="通过代理拆分查询为子问题")
async def agent_decompose_query(
    agent_id: str,
    request: SubquestionRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """
    通过代理拆分查询为子问题
    
    使用指定的代理将复杂查询拆分为多个简单子问题
    """
    request.agent_id = agent_id
    try:
        result = await tools_integration.decompose_query(request)
        return ResponseFormatter.format_success(
            data=result,
            message=f"代理 {agent_id} 成功拆分查询为子问题"
        )
    except ValueError as e:
        return ResponseFormatter.format_error(
            message=str(e),
            code=400
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"代理拆分查询失败: {str(e)}",
            code=500
        )

@router.post("/agents/{agent_id}/qa/route", summary="通过代理为查询选择合适的知识库路由")
async def agent_route_query(
    agent_id: str,
    request: QARoutingRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """
    通过代理为查询选择合适的知识库路由
    
    使用指定的代理为查询选择最合适的知识库
    """
    request.agent_id = agent_id
    try:
        result = await tools_integration.route_query(request)
        return ResponseFormatter.format_success(
            data=result,
            message=f"代理 {agent_id} 成功为查询选择路由"
        )
    except ValueError as e:
        return ResponseFormatter.format_error(
            message=str(e),
            code=400
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"代理路由查询失败: {str(e)}",
            code=500
        )

@router.post("/agents/{agent_id}/process", summary="通过代理处理查询")
async def agent_process_query(
    agent_id: str,
    request: ProcessQueryRequest,
    tools_integration: BaseToolsIntegration = Depends(get_base_tools_integration)
):
    """
    通过代理处理查询，应用子问题拆分和问答路由
    
    使用指定的代理综合处理查询，包括拆分和路由
    """
    request.agent_id = agent_id
    try:
        result = await tools_integration.process_query(request)
        return ResponseFormatter.format_success(
            data=result,
            message=f"代理 {agent_id} 成功处理查询"
        )
    except ValueError as e:
        return ResponseFormatter.format_error(
            message=str(e),
            code=400
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"代理处理查询失败: {str(e)}",
            code=500
        ) 