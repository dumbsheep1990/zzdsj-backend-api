"""
工具API模块
提供工具定义和管理的RESTful API端点
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
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

router = APIRouter(prefix="/tools", tags=["工具管理"])

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
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
    
    需要认证和适当的权限
    """
    return await service.create_tool(tool.dict(), current_user.id)

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    获取工具详情
    
    需要认证和适当的权限
    """
    tool = await service.get_tool(tool_id, current_user.id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在"
        )
    return tool

@router.get("/by-name/{tool_name}", response_model=ToolResponse)
async def get_tool_by_name(
    tool_name: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    通过名称获取工具
    
    需要认证和适当的权限
    """
    tool = await service.get_by_name(tool_name, current_user.id)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"名称为 '{tool_name}' 的工具不存在"
        )
    return tool

@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    获取工具列表
    
    需要认证，根据用户权限返回可访问的工具
    """
    return await service.list_tools(current_user.id, skip, limit)

@router.get("/category/{category}", response_model=List[ToolResponse])
async def list_tools_by_category(
    category: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    获取指定类别的工具列表
    
    需要认证和适当的权限
    """
    return await service.list_tools_by_category(category, current_user.id)

@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    tool: ToolUpdate,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    更新工具
    
    需要认证和适当的权限
    """
    updated = await service.update_tool(tool_id, tool.dict(exclude_unset=True), current_user.id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在"
        )
    return updated

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """
    删除工具
    
    需要认证和适当的权限
    """
    deleted = await service.delete_tool(tool_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在"
        )
    return {"detail": "工具已成功删除"}

@router.post("/{tool_id}/execute", response_model=ToolExecuteResponse)
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
    
    需要认证和适当的权限
    """
    result = await execution_service.execute_tool(
        tool_id, 
        request.input_params, 
        current_user.id, 
        request.agent_run_id
    )
    return result

@router.get("/{tool_id}/executions", response_model=List[Dict[str, Any]])
async def list_tool_executions(
    tool_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    获取工具执行记录列表
    
    需要认证和适当的权限
    """
    executions = await execution_service.list_executions_by_tool(tool_id, current_user.id, skip, limit)
    return [execution.to_dict() for execution in executions]

@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution(
    execution_id: str,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    获取工具执行记录详情
    
    需要认证和适当的权限
    """
    execution = await execution_service.get_execution(execution_id, current_user.id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )
    return execution.to_dict()

@router.get("/executions/user/{user_id}", response_model=List[Dict[str, Any]])
async def list_user_executions(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    获取用户执行记录列表
    
    需要认证和适当的权限
    """
    # 检查是否为当前用户或管理员
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此用户的执行记录"
        )
    
    executions = await execution_service.list_executions_by_user(user_id, skip, limit)
    return [execution.to_dict() for execution in executions]

@router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    execution_id: str,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """
    删除工具执行记录
    
    需要认证和适当的权限
    """
    deleted = await execution_service.delete_execution(execution_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="执行记录不存在"
        )
    return {"detail": "执行记录已成功删除"}
