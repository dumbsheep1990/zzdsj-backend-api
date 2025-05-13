from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.owl_controller import OwlController
from app.utils.database import get_db, AsyncSession
from app.config import settings

router = APIRouter()

# 初始化OWL控制器
owl_controller = OwlController()

class ModelConfig(BaseModel):
    """模型配置模型"""
    model_name: Optional[str] = Field(None, description="模型名称")
    temperature: Optional[float] = Field(None, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大输出标记数")

class TaskRequest(BaseModel):
    """任务请求模型"""
    task: str = Field(..., description="任务描述")
    tools: Optional[List[str]] = Field(None, description="指定使用的工具ID列表")
    user_id: Optional[str] = Field(None, description="用户ID，用于个性化处理")
    model_config: Optional[ModelConfig] = Field(None, description="模型配置，支持用户自定义")

class TaskResponse(BaseModel):
    """任务响应模型"""
    result: str = Field(..., description="任务处理结果")
    chat_history: List[Dict[str, Any]] = Field([], description="聊天历史")
    metadata: Dict[str, Any] = Field({}, description="元数据")

class WorkflowRequest(BaseModel):
    """工作流创建请求模型"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流自然语言描述")

class WorkflowResponse(BaseModel):
    """工作流创建响应模型"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    workflow: Dict[str, Any] = Field(..., description="工作流定义")

class WorkflowExecutionRequest(BaseModel):
    """工作流执行请求模型"""
    workflow_name: str = Field(..., description="工作流名称")
    inputs: Dict[str, Any] = Field(..., description="输入参数")

class ToolInfoResponse(BaseModel):
    """工具信息响应模型"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")

class WorkflowInfoResponse(BaseModel):
    """工作流信息响应模型"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    steps_count: int = Field(..., description="步骤数量")
    
class ModelInfoResponse(BaseModel):
    """模型信息响应模型"""
    id: str = Field(..., description="模型内部ID")
    name: str = Field(..., description="模型显示名称")
    provider: str = Field(..., description="模型提供商")
    category: str = Field(..., description="模型类别")

@router.post("/task", response_model=TaskResponse, summary="处理任务")
async def process_task(request: TaskRequest, db: AsyncSession = Depends(get_db)):
    """
    处理任务接口，使用OWL框架处理用户提供的任务
    
    - **task**: 任务描述
    - **tools**: 可选的工具ID列表，用于指定任务可用的工具
    - **user_id**: 可选的用户ID，用于个性化处理
    - **model_config**: 可选的模型配置，用于指定使用的模型参数
    
    返回：
    - **result**: 任务处理结果
    - **chat_history**: 任务处理过程中的对话历史
    - **metadata**: 任务处理的元数据信息
    """
    try:
        # 将用户模型配置转换为字典
        model_config = None
        if request.model_config:
            model_config = request.model_config.dict(exclude_none=True)
            
        result = await owl_controller.process_task(
            task=request.task,
            tools=request.tools,
            user_id=request.user_id,
            model_config=model_config
        )
        
        return TaskResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理任务时出错: {str(e)}"
        )

@router.post("/workflow", response_model=WorkflowResponse, summary="创建工作流")
async def create_workflow(request: WorkflowRequest, db: AsyncSession = Depends(get_db)):
    """
    创建工作流接口，根据自然语言描述创建可执行的工作流
    
    - **name**: 工作流名称
    - **description**: 工作流的自然语言描述，系统将基于此生成结构化工作流
    
    返回：
    - **name**: 工作流名称
    - **description**: 工作流描述
    - **workflow**: 完整的工作流定义
    """
    try:
        result = await owl_controller.create_workflow(
            name=request.name,
            description=request.description
        )
        
        return WorkflowResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建工作流时出错: {str(e)}"
        )

@router.post("/workflow/execute", response_model=Dict[str, Any], summary="执行工作流")
async def execute_workflow(request: WorkflowExecutionRequest, db: AsyncSession = Depends(get_db)):
    """
    执行工作流接口，运行指定的工作流并传入参数
    
    - **workflow_name**: 工作流名称
    - **inputs**: 工作流输入参数
    
    返回：
    - 工作流执行结果
    """
    try:
        result = await owl_controller.execute_workflow(
            workflow_name=request.workflow_name,
            inputs=request.inputs
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行工作流时出错: {str(e)}"
        )

@router.get("/tools", response_model=List[ToolInfoResponse], summary="获取可用工具")
async def get_available_tools(db: AsyncSession = Depends(get_db)):
    """
    获取所有可用工具接口
    
    返回：
    - 工具列表，每个工具包含名称和描述
    """
    try:
        tools = await owl_controller.get_available_tools()
        return tools
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用工具时出错: {str(e)}"
        )

@router.get("/workflows", response_model=List[WorkflowInfoResponse], summary="获取可用工作流")
async def get_available_workflows(db: AsyncSession = Depends(get_db)):
    """
    获取所有可用工作流接口
    
    返回：
    - 工作流列表，每个工作流包含名称、描述和步骤数量
    """
    try:
        workflows = await owl_controller.get_available_workflows()
        return workflows
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用工作流时出错: {str(e)}"
        )

@router.get("/models", response_model=List[ModelInfoResponse], summary="获取可用模型")
async def get_available_models(db: AsyncSession = Depends(get_db)):
    """
    获取所有可用的模型列表
    
    返回：
    - 模型列表，每个模型包含模型ID、名称、提供商和类别
    """
    try:
        # 从系统设置获取可用模型
        models = settings.system_model.available_models
        chat_models = [model for model in models if model.get("category") == "chat"]
        return chat_models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用模型时出错: {str(e)}"
        )
