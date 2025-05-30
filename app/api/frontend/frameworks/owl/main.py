"""
OWL框架 - 主接口模块
提供任务处理、工作流创建和执行的主要API端点
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory
from core.owl_controller import OwlController
from app.schemas.owl import (
    TaskRequest, 
    TaskResponse, 
    WorkflowRequest, 
    WorkflowResponse,
    WorkflowExecutionRequest,
    ToolInfoResponse,
    WorkflowInfoResponse,
    ModelInfoResponse
)

# 创建响应格式化器和路由
formatter = InternalResponseFormatter()
router = APIRouter()
validator = ValidatorFactory.create("owl")

# 初始化OWL控制器
owl_controller = OwlController()

# ====================================
# 任务处理相关接口
# ====================================

@router.post("/tasks", response_model=TaskResponse)
async def process_task(
    request: TaskRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    处理任务接口，使用OWL框架处理用户提供的任务
    
    可指定使用的工具、用户ID和模型配置
    """
    # 验证请求
    validator.validate_task_request(request)
    
    try:
        # 复用原有的OWL控制器逻辑
        result = await owl_controller.process_task(
            task=request.task,
            tools=request.tools,
            user_id=context.user.id,
            model_config=request.model_config.dict() if request.model_config else None
        )
        
        return formatter.success(
            data=result,
            message="任务处理成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"任务处理失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ====================================
# 工作流相关接口
# ====================================

@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建工作流接口，根据自然语言描述创建可执行的工作流
    
    通过描述定义工作流的步骤和逻辑
    """
    # 验证请求
    validator.validate_workflow_request(request)
    
    try:
        # 复用原有的OWL工作流创建逻辑
        workflow = await owl_controller.create_workflow(
            name=request.name,
            description=request.description,
            user_id=context.user.id
        )
        
        return formatter.success(
            data=workflow,
            message="工作流创建成功",
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        return formatter.error(
            message=f"工作流创建失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/workflows/execute", response_model=Dict[str, Any])
async def execute_workflow(
    request: WorkflowExecutionRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    执行工作流接口，运行指定的工作流并传入参数
    
    返回工作流的执行结果
    """
    # 验证请求
    validator.validate_workflow_execution_request(request)
    
    try:
        # 复用原有的OWL工作流执行逻辑
        result = await owl_controller.execute_workflow(
            workflow_name=request.workflow_name,
            inputs=request.inputs,
            user_id=context.user.id
        )
        
        return formatter.success(
            data=result,
            message="工作流执行成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"工作流执行失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ====================================
# 元信息查询接口
# ====================================

@router.get("/tools", response_model=List[ToolInfoResponse])
async def get_available_tools(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取所有可用工具接口
    
    返回可被OWL框架使用的工具列表
    """
    try:
        # 复用原有的工具查询逻辑
        tools = await owl_controller.get_available_tools(user_id=context.user.id)
        
        return formatter.success(
            data=tools,
            message="获取工具列表成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"获取工具列表失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/workflows", response_model=List[WorkflowInfoResponse])
async def get_available_workflows(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取所有可用工作流接口
    
    返回当前可用的工作流定义列表
    """
    try:
        # 复用原有的工作流查询逻辑
        workflows = await owl_controller.get_available_workflows(user_id=context.user.id)
        
        return formatter.success(
            data=workflows,
            message="获取工作流列表成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"获取工作流列表失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/models", response_model=List[ModelInfoResponse])
async def get_available_models(
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取所有可用的模型列表
    
    返回当前可用于OWL框架的模型列表
    """
    try:
        # 复用原有的模型查询逻辑
        models = await owl_controller.get_available_models()
        
        return formatter.success(
            data=models,
            message="获取模型列表成功"
        )
    except Exception as e:
        return formatter.error(
            message=f"获取模型列表失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
