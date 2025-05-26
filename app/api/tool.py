"""
[✅ 已迁移] 此文件已完成重构和迁移到 app/api/frontend/tools/manager.py
工具管理API桥接文件
(已弃用) - 请使用 app.api.frontend.tools.manager 模块
此文件仅用于向后兼容，所有新代码都应该使用新的模块
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

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

# 导入新的工具管理路由处理函数
from app.api.frontend.tools.manager import (
    create_tool as new_create_tool,
    get_tool as new_get_tool,
    get_tool_by_name as new_get_tool_by_name,
    list_tools as new_list_tools,
    list_tools_by_category as new_list_tools_by_category,
    update_tool as new_update_tool,
    delete_tool as new_delete_tool,
    execute_tool as new_execute_tool,
    list_tool_executions as new_list_tool_executions,
    get_execution as new_get_execution,
    list_user_executions as new_list_user_executions,
    delete_execution as new_delete_execution
)

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["工具管理"])

@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool: ToolCreate,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """创建新的工具"""
    logger.warning(
        "使用已弃用的工具管理端点: /tools/，应使用新的端点: /api/frontend/tools/"
    )
    return await new_create_tool(tool=tool, current_user=current_user, service=service)

@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """获取工具详情"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/{tool_id}，应使用新的端点: /api/frontend/tools/{tool_id}"
    )
    return await new_get_tool(tool_id=tool_id, current_user=current_user, service=service)

@router.get("/by-name/{tool_name}", response_model=ToolResponse)
async def get_tool_by_name(
    tool_name: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """通过名称获取工具"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/by-name/{tool_name}，应使用新的端点: /api/frontend/tools/by-name/{tool_name}"
    )
    return await new_get_tool_by_name(tool_name=tool_name, current_user=current_user, service=service)

@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """获取工具列表"""
    logger.warning(
        "使用已弃用的工具管理端点: /tools/，应使用新的端点: /api/frontend/tools/"
    )
    return await new_list_tools(skip=skip, limit=limit, current_user=current_user, service=service)

@router.get("/category/{category}", response_model=List[ToolResponse])
async def list_tools_by_category(
    category: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """获取指定类别的工具列表"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/category/{category}，应使用新的端点: /api/frontend/tools/category/{category}"
    )
    return await new_list_tools_by_category(category=category, current_user=current_user, service=service)

@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    tool: ToolUpdate,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """更新工具"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/{tool_id}，应使用新的端点: /api/frontend/tools/{tool_id}"
    )
    return await new_update_tool(tool_id=tool_id, tool=tool, current_user=current_user, service=service)

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    current_user = Depends(get_current_user),
    service: ToolService = Depends()
):
    """删除工具"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/{tool_id}，应使用新的端点: /api/frontend/tools/{tool_id}"
    )
    return await new_delete_tool(tool_id=tool_id, current_user=current_user, service=service)

@router.post("/{tool_id}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_id: str,
    request: ToolExecuteRequest,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """执行工具"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/{tool_id}/execute，应使用新的端点: /api/frontend/tools/{tool_id}/execute"
    )
    return await new_execute_tool(tool_id=tool_id, request=request, current_user=current_user, execution_service=execution_service)

@router.get("/{tool_id}/executions", response_model=List[Dict[str, Any]])
async def list_tool_executions(
    tool_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """获取工具执行记录列表"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/{tool_id}/executions，应使用新的端点: /api/frontend/tools/{tool_id}/executions"
    )
    return await new_list_tool_executions(tool_id=tool_id, skip=skip, limit=limit, current_user=current_user, execution_service=execution_service)

@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution(
    execution_id: str,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """获取工具执行记录详情"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/executions/{execution_id}，应使用新的端点: /api/frontend/tools/executions/{execution_id}"
    )
    return await new_get_execution(execution_id=execution_id, current_user=current_user, execution_service=execution_service)

@router.get("/executions/user/{user_id}", response_model=List[Dict[str, Any]])
async def list_user_executions(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """获取用户执行记录列表"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/executions/user/{user_id}，应使用新的端点: /api/frontend/tools/executions/user/{user_id}"
    )
    return await new_list_user_executions(user_id=user_id, skip=skip, limit=limit, current_user=current_user, execution_service=execution_service)

@router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    execution_id: str,
    current_user = Depends(get_current_user),
    execution_service: ToolExecutionService = Depends()
):
    """删除工具执行记录"""
    logger.warning(
        f"使用已弃用的工具管理端点: /tools/executions/{execution_id}，应使用新的端点: /api/frontend/tools/executions/{execution_id}"
    )
    return await new_delete_execution(execution_id=execution_id, current_user=current_user, execution_service=execution_service)
