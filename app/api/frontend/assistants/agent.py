"""
智能体服务API: 提供智能体任务处理和工具调用的接口
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.agent_manager import AgentManager
from app.utils.core.database import get_db, AsyncSession
from app.api.frontend.dependencies import ResponseFormatter

router = APIRouter()

# 初始化智能体管理器和日志
agent_manager = AgentManager()
logger = logging.getLogger(__name__)

class TaskRequest(BaseModel):
    """任务请求模型"""
    task: str
    framework: Optional[str] = None
    tool_ids: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    """任务响应模型"""
    result: str
    metadata: Dict[str, Any]

@router.post("/task", response_model=TaskResponse)
async def process_task(request: TaskRequest, db: AsyncSession = Depends(get_db)):
    """处理任务
    
    Args:
        request: 任务请求
        db: 数据库会话
        
    Returns:
        TaskResponse: 任务响应
    """
    # 加载指定工具
    tools = []
    if request.tool_ids:
        try:
            # 从工具管理器获取工具实例
            for tool_id in request.tool_ids:
                tool = await agent_manager.get_tool_by_id(tool_id)
                if tool:
                    tools.append(tool)
                else:
                    # 记录警告但不中断执行
                    logger.warning(f"找不到工具ID: {tool_id}")
        except Exception as e:
            logger.error(f"加载工具时发生错误: {str(e)}")
            # 如果工具加载失败，使用空工具列表继续执行
            tools = []
        
    try:
        # 处理任务
        result, metadata = await agent_manager.process_task(
            task=request.task,
            use_framework=request.framework,
            tools=tools
        )
        
        response = TaskResponse(
            result=result,
            metadata=metadata
        )
        
        return ResponseFormatter.format_success(response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理任务时出错: {str(e)}"
        )

@router.get("/frameworks")
async def list_frameworks():
    """获取可用的智能体框架列表"""
    try:
        frameworks = agent_manager.list_available_frameworks()
        return ResponseFormatter.format_success(frameworks)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取框架列表时出错: {str(e)}"
        )

@router.get("/tools")
async def list_tools():
    """获取可用的智能体工具列表"""
    try:
        tools = agent_manager.list_available_tools()
        return ResponseFormatter.format_success(tools)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具列表时出错: {str(e)}"
        ) 