"""
智能体服务API: 提供智能体任务处理和工具调用的接口
"""


from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.utils.database import get_db
from app.services_new.agent_services_new import AgentService
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.dependencies import get_current_user, ResponseFormatter
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskRequest(BaseModel):
    """任务请求模型"""
    task: str = Field(..., min_length=1, description="任务描述")
    framework: Optional[str] = Field(None, description="使用的框架")
    tool_ids: Optional[List[str]] = Field(None, description="工具ID列表")
    parameters: Optional[Dict[str, Any]] = Field(None, description="额外参数")


class TaskResponse(BaseModel):
    """任务响应模型"""
    result: str = Field(..., description="任务结果")
    metadata: Dict[str, Any] = Field(..., description="元数据")


class ToolConfig(BaseModel):
    """工具配置模型"""
    tool_id: Optional[str] = Field(None, description="工具ID")
    tool_type: str = Field(..., description="工具类型: mcp, query_engine, function")
    tool_name: str = Field(..., description="工具名称")
    enabled: bool = Field(True, description="是否启用")
    settings: Optional[Dict[str, Any]] = Field(None, description="工具设置")


@router.post("/task", response_model=Dict[str, Any])
async def process_task(
        request: TaskRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    处理智能体任务

    支持多种框架和工具调用
    """
    try:
        service = AgentService(db)
        result, metadata = await service.process_task(
            task=request.task,
            framework=request.framework,
            tool_ids=request.tool_ids,
            parameters=request.parameters,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "result": result,
                "metadata": metadata
            },
            message="任务处理成功"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"处理任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="处理任务时出错")


@router.get("/frameworks", response_model=Dict[str, Any])
async def list_frameworks(db: Session = Depends(get_db)):
    """获取可用的智能体框架列表"""
    try:
        service = AgentService(db)
        frameworks = service.list_available_frameworks()

        return ResponseFormatter.format_success(
            data={
                "frameworks": frameworks,
                "total": len(frameworks)
            }
        )

    except Exception as e:
        logger.error(f"获取框架列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取框架列表时出错")


@router.post("/assistants/{assistant_id}/tools", response_model=Dict[str, Any])
async def configure_assistant_tools(
        assistant_id: int,
        tools: List[ToolConfig],
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    配置助手工具

    只有助手所有者可以配置
    """
    try:
        service = AgentService(db)
        configured_tools = await service.configure_agent_tools(
            agent_id=assistant_id,
            tool_configs=[tool.model_dump() for tool in tools],
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "tools": configured_tools,
                "count": len(configured_tools)
            },
            message="工具配置成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"配置助手工具失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="配置助手工具时出错")


@router.get("/assistants/{assistant_id}/tools", response_model=Dict[str, Any])
async def get_assistant_tools(
        assistant_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手工具配置"""
    try:
        service = AgentService(db)
        tools = await service.get_agent_tools(assistant_id)

        return ResponseFormatter.format_success(
            data={
                "tools": tools,
                "count": len(tools)
            }
        )

    except Exception as e:
        logger.error(f"获取助手工具配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取助手工具配置时出错")

