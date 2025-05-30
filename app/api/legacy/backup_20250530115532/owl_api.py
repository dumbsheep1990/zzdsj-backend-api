"""
OWL框架工具API端点
提供OWL框架工具的HTTP API接口
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin_role
from core.owl_controller import OwlController
from app.models.user import User
from app.schemas.owl import (
    ToolExecuteRequest, 
    ToolExecuteResponse,
    ToolListResponse,
    ToolMetadataResponse
)
from app.schemas.common import StandardResponse

router = APIRouter(
    prefix="/owl",
    tags=["owl"],
    responses={401: {"description": "未授权"}},
)

@router.get("/tools", response_model=ToolListResponse)
async def list_tools(
    toolkit: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ToolListResponse:
    """
    获取可用的OWL工具列表
    
    Args:
        toolkit: 可选参数，按工具包筛选工具
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        ToolListResponse: 工具列表响应
    """
    controller = OwlController(db)
    tools = await controller.get_available_tools()
    
    # 如果指定了工具包，筛选结果
    if toolkit:
        tools = [tool for tool in tools if tool.get("toolkit", "") == toolkit]
    
    return {
        "status": "success",
        "data": tools,
        "total": len(tools)
    }

@router.get("/tools/{tool_name}", response_model=ToolMetadataResponse)
async def get_tool_metadata(
    tool_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ToolMetadataResponse:
    """
    获取工具的详细元数据
    
    Args:
        tool_name: 工具名称
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        ToolMetadataResponse: 工具元数据响应
    """
    controller = OwlController(db)
    
    try:
        metadata = await controller.get_tool_metadata(tool_name)
        return {
            "status": "success",
            "data": metadata
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具 '{tool_name}' 不存在"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具元数据时出错: {str(e)}"
        )

@router.post("/tools/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ToolExecuteResponse:
    """
    执行指定的工具
    
    Args:
        tool_name: 工具名称
        request: 工具执行请求参数
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        ToolExecuteResponse: 工具执行响应
    """
    controller = OwlController(db)
    
    try:
        result = await controller.execute_tool(tool_name, request.parameters)
        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具 '{tool_name}' 不存在或未启用"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行工具时出错: {str(e)}"
        )

@router.post("/task", response_model=Dict[str, Any])
async def execute_task(
    task: str,
    tools: Optional[List[str]] = Query(None),
    model: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    使用OWL框架处理任务
    
    Args:
        task: 任务描述
        tools: 可用工具列表
        model: 可选的模型名称
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict[str, Any]: 任务处理结果
    """
    controller = OwlController(db)
    
    model_config = None
    if model:
        model_config = {"model": model}
    
    try:
        result = await controller.process_task(
            task=task,
            tools=tools,
            user_id=str(current_user.id),
            model_config=model_config
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理任务时出错: {str(e)}"
        )

@router.post("/toolkits/{toolkit_name}/load", response_model=StandardResponse)
async def load_toolkit(
    toolkit_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
) -> StandardResponse:
    """
    加载指定的工具包
    
    Args:
        toolkit_name: 工具包名称
        db: 数据库会话
        current_user: 当前用户（需要管理员权限）
        
    Returns:
        StandardResponse: 标准响应
    """
    controller = OwlController(db)
    
    if not controller.toolkit_integrator:
        await controller.initialize()
        
    if not controller.toolkit_integrator:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="工具包集成器初始化失败"
        )
    
    try:
        await controller.toolkit_integrator.load_toolkit(toolkit_name)
        return {
            "status": "success",
            "message": f"工具包 '{toolkit_name}' 已成功加载"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具包 '{toolkit_name}' 不存在"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载工具包时出错: {str(e)}"
        )

@router.get("/toolkits", response_model=Dict[str, Any])
async def list_available_toolkits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    列出所有可用的工具包
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict[str, Any]: 工具包列表
    """
    controller = OwlController(db)
    
    if not controller.toolkit_integrator:
        await controller.initialize()
        
    if not controller.toolkit_integrator:
        return {
            "status": "success",
            "data": [],
            "total": 0
        }
    
    try:
        toolkits = await controller.toolkit_integrator.list_available_toolkits()
        return {
            "status": "success",
            "data": toolkits,
            "total": len(toolkits)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具包列表时出错: {str(e)}"
        )
