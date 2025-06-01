"""
工具管理 - 前端路由模块
提供工具定义和管理的RESTful API端点
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.models.tool import Tool
from app.schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolExecuteRequest,
    ToolExecuteResponse
)
from app.services.tool_service import ToolService
from app.services.tool_execution_service import ToolExecutionService
from app.api.deps import get_current_user
from app.api.frontend.responses import ResponseFormatter

router = APIRouter()

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED, summary="创建工具")
async def create_tool(
    tool: ToolCreate,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    创建新的工具
    
    - **name**: 工具名称（必须唯一）
    - **description**: 工具描述
    - **function_def**: 函数定义（JSON格式）
    - **implementation_type**: 实现类型（如python_function, http_api, shell_command等）
    - **implementation_details**: 实现详情（JSON格式）
    - **category**: 工具类别（可选）
    - **config_schema**: 配置模式（可选）
    """
    try:
        result = await service.create_tool(tool.dict(), current_user.id)
        return ResponseFormatter.format_success(
            data=result,
            message="工具创建成功",
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"创建工具失败: {str(e)}",
            code=500
        )

@router.get("/{tool_id}", response_model=ToolResponse, summary="获取工具详情")
async def get_tool(
    tool_id: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    获取工具详情
    """
    try:
        tool = await service.get_tool(tool_id, current_user.id)
        if not tool:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="获取工具详情成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具详情失败: {str(e)}",
            code=500
        )

@router.get("/by-name/{tool_name}", response_model=ToolResponse, summary="通过名称获取工具")
async def get_tool_by_name(
    tool_name: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    通过名称获取工具
    """
    try:
        tool = await service.get_by_name(tool_name, current_user.id)
        if not tool:
            return ResponseFormatter.format_error(
                message=f"名称为 '{tool_name}' 的工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=tool,
            message="获取工具详情成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具详情失败: {str(e)}",
            code=500
        )

@router.get("/", summary="获取工具列表")
async def list_tools(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    获取工具列表
    
    根据用户权限返回可访问的工具
    """
    try:
        tools = await service.list_tools(current_user.id, skip, limit)
        return ResponseFormatter.format_success(
            data=tools,
            message="获取工具列表成功",
            metadata={
                "total": len(tools),
                "skip": skip,
                "limit": limit
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具列表失败: {str(e)}",
            code=500
        )

@router.get("/category/{category}", summary="获取指定类别的工具列表")
async def list_tools_by_category(
    category: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    获取指定类别的工具列表
    """
    try:
        tools = await service.list_tools_by_category(category, current_user.id)
        return ResponseFormatter.format_success(
            data=tools,
            message=f"获取类别 '{category}' 的工具列表成功",
            metadata={
                "total": len(tools),
                "category": category
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取工具列表失败: {str(e)}",
            code=500
        )

@router.put("/{tool_id}", response_model=ToolResponse, summary="更新工具")
async def update_tool(
    tool_id: str,
    tool: ToolUpdate,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    更新工具
    """
    try:
        updated = await service.update_tool(tool_id, tool.dict(exclude_unset=True), current_user.id)
        if not updated:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=updated,
            message="工具更新成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"更新工具失败: {str(e)}",
            code=500
        )

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除工具")
async def delete_tool(
    tool_id: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    删除工具
    """
    try:
        deleted = await service.delete_tool(tool_id, current_user.id)
        if not deleted:
            return ResponseFormatter.format_error(
                message="工具不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"tool_id": tool_id},
            message="工具已成功删除",
            status_code=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除工具失败: {str(e)}",
            code=500
        )

@router.post("/{tool_id}/execute", response_model=ToolExecuteResponse, summary="执行工具")
async def execute_tool(
    tool_id: str,
    request: ToolExecuteRequest,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    执行工具
    
    - **input_params**: 输入参数（JSON格式）
    - **agent_run_id**: 智能体运行ID（可选）
    """
    try:
        result = await execution_service.execute_tool(
            tool_id, 
            request.input_params, 
            current_user.id, 
            request.agent_run_id
        )
        return ResponseFormatter.format_success(
            data=result,
            message="工具执行成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"执行工具失败: {str(e)}",
            code=500
        )

@router.get("/{tool_id}/executions", summary="获取工具执行记录列表")
async def list_tool_executions(
    tool_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    获取工具执行记录列表
    """
    try:
        executions = await execution_service.list_executions_by_tool(tool_id, current_user.id, skip, limit)
        return ResponseFormatter.format_success(
            data=[execution.to_dict() for execution in executions],
            message="获取执行记录列表成功",
            metadata={
                "total": len(executions),
                "skip": skip,
                "limit": limit,
                "tool_id": tool_id
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取执行记录列表失败: {str(e)}",
            code=500
        )

@router.get("/executions/{execution_id}", summary="获取工具执行记录详情")
async def get_execution(
    execution_id: str,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    获取工具执行记录详情
    """
    try:
        execution = await execution_service.get_execution(execution_id, current_user.id)
        if not execution:
            return ResponseFormatter.format_error(
                message="执行记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data=execution.to_dict(),
            message="获取执行记录详情成功"
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取执行记录详情失败: {str(e)}",
            code=500
        )

@router.get("/executions/user/{user_id}", summary="获取用户执行记录列表")
async def list_user_executions(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    获取用户执行记录列表
    """
    try:
        # 检查是否为当前用户或管理员
        if current_user.id != user_id and current_user.role != "admin":
            return ResponseFormatter.format_error(
                message="没有权限访问此用户的执行记录",
                code=403
            )
        
        executions = await execution_service.list_executions_by_user(user_id, skip, limit)
        return ResponseFormatter.format_success(
            data=[execution.to_dict() for execution in executions],
            message="获取用户执行记录列表成功",
            metadata={
                "total": len(executions),
                "skip": skip,
                "limit": limit,
                "user_id": user_id
            }
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"获取用户执行记录列表失败: {str(e)}",
            code=500
        )

@router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除工具执行记录")
async def delete_execution(
    execution_id: str,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    删除工具执行记录
    """
    try:
        deleted = await execution_service.delete_execution(execution_id, current_user.id)
        if not deleted:
            return ResponseFormatter.format_error(
                message="执行记录不存在",
                code=404
            )
        return ResponseFormatter.format_success(
            data={"execution_id": execution_id},
            message="执行记录已成功删除",
            status_code=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return ResponseFormatter.format_error(
            message=f"删除执行记录失败: {str(e)}",
            code=500
        ) 