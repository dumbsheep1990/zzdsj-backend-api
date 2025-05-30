"""
OWL框架工具API端点模块
提供OWL框架工具的HTTP API接口，与原有owl_api.py功能兼容
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory
from app.core.owl_controller import OwlController
from app.schemas.owl import (
    ToolExecuteRequest, 
    ToolExecuteResponse,
    ToolListResponse,
    ToolMetadataResponse
)
from app.schemas.common import StandardResponse

# 创建响应格式化器和路由
formatter = InternalResponseFormatter()
router = APIRouter()
validator = ValidatorFactory.create("owl_api")

# 初始化OWL控制器
owl_controller = OwlController()

@router.get("/tools", response_model=ToolListResponse)
async def list_tools(
    toolkit: Optional[str] = None,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取可用的OWL工具列表
    
    可选择按工具包筛选工具
    """
    try:
        # 复用原有控制器逻辑
        tool_list = await owl_controller.list_tools(
            toolkit=toolkit, 
            user_id=context.user.id
        )
        
        return formatter.success(
            data={"tools": tool_list, "count": len(tool_list)},
            message="获取工具列表成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"获取工具列表失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/tools/{tool_name}", response_model=ToolMetadataResponse)
async def get_tool_metadata(
    tool_name: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取工具的详细元数据
    
    返回工具名称、描述、参数和返回类型等信息
    """
    try:
        # 复用原有控制器逻辑
        metadata = await owl_controller.get_tool_metadata(
            tool_name=tool_name, 
            user_id=context.user.id
        )
        
        if not metadata:
            return formatter.error(
                message=f"找不到工具: {tool_name}",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        return formatter.success(
            data=metadata,
            message="获取工具元数据成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"获取工具元数据失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/tools/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    执行指定的工具
    
    传入工具名称和执行参数，返回执行结果
    """
    # 验证请求
    validator.validate_tool_execute_request(request)
    
    try:
        # 复用原有控制器逻辑
        result = await owl_controller.execute_tool(
            tool_name=tool_name,
            params=request.parameters,
            user_id=context.user.id
        )
        
        return formatter.success(
            data={"result": result},
            message="工具执行成功"
        )
    except ValueError as e:
        return formatter.error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return formatter.error(
            message=f"工具执行失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/tasks/execute", response_model=Dict[str, Any])
async def execute_task(
    task: str,
    tools: Optional[List[str]] = Query(None),
    model: Optional[str] = None,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    使用OWL框架处理任务
    
    传入任务描述和可用工具列表，返回处理结果
    """
    try:
        # 复用原有控制器逻辑
        result = await owl_controller.execute_task(
            task=task,
            tools=tools,
            model=model,
            user_id=context.user.id
        )
        
        return formatter.success(
            data=result,
            message="任务执行成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"任务执行失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/toolkits/{toolkit_name}/load", response_model=StandardResponse)
async def load_toolkit(
    toolkit_name: str,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    加载指定的工具包
    
    需要管理员权限
    """
    # 检查管理员权限
    if not context.user.is_admin:
        return formatter.error(
            message="需要管理员权限",
            status_code=status.HTTP_403_FORBIDDEN
        )
        
    try:
        # 复用原有控制器逻辑
        success = await owl_controller.load_toolkit(toolkit_name=toolkit_name)
        
        if success:
            return formatter.success(
                data={"toolkit": toolkit_name},
                message=f"成功加载工具包: {toolkit_name}"
            )
        else:
            return formatter.error(
                message=f"无法加载工具包: {toolkit_name}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return formatter.error(
            message=f"加载工具包失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/toolkits", response_model=Dict[str, Any])
async def list_available_toolkits(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    列出所有可用的工具包
    
    返回工具包列表及其包含的工具
    """
    try:
        # 复用原有控制器逻辑
        toolkits = await owl_controller.list_available_toolkits()
        
        return formatter.success(
            data={"toolkits": toolkits},
            message="获取工具包列表成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"获取工具包列表失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
