"""
智能体API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.config.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.services.assistants.agent import AgentService
from app.schemas.assistants.agent import (
    TaskRequest,
    TaskResponse,
    ToolConfig,
    FrameworkListResponse,
    ToolListResponse
)
from app.schemas.assistants.base import APIResponse
from app.core.assistants.exceptions import AssistantNotFoundError, PermissionDeniedError, ValidationError, ExternalServiceError

router = APIRouter()


def get_agent_service(db: AsyncSession = Depends(get_async_db)) -> AgentService:
    return AgentService(db)


@router.post("/task", response_model=APIResponse)
async def process_task(
        request: TaskRequest,
        current_user=Depends(get_current_user),
        service: AgentService = Depends(get_agent_service)
):
    """
    处理智能体任务

    支持的框架:
    - langchain
    - llama_index
    - autogen
    - crewai
    """
    try:
        result, metadata = await service.process_task(
            task=request.task,
            framework=request.framework,
            tools=request.tool_ids,
            parameters=request.parameters
        )

        return APIResponse(
            data={
                "result": result,
                "metadata": metadata
            },
            message="任务处理成功"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/frameworks", response_model=APIResponse)
async def list_frameworks(
        service: AgentService = Depends(get_agent_service)
):
    """获取支持的智能体框架列表"""
    frameworks = service.list_frameworks()

    return APIResponse(
        data={
            "frameworks": frameworks,
            "total": len(frameworks)
        }
    )


@router.get("/tools", response_model=APIResponse)
async def list_tools(
        service: AgentService = Depends(get_agent_service)
):
    """获取可用的工具列表"""
    tools = service.list_tools()

    return APIResponse(
        data={
            "tools": tools,
            "total": len(tools)
        }
    )


@router.post("/{agent_id}/tools", response_model=APIResponse)
async def configure_tools(
        agent_id: int,
        tools: List[ToolConfig],
        current_user=Depends(get_current_user),
        service: AgentService = Depends(get_agent_service)
):
    """
    配置智能体工具

    只有助手所有者可以配置
    """
    try:
        configured_tools = await service.configure_tools(
            agent_id=agent_id,
            tools=tools,
            user_id=current_user.id
        )

        return APIResponse(
            data={
                "tools": configured_tools,
                "count": len(configured_tools)
            },
            message="工具配置成功"
        )
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有所有者可以配置工具")