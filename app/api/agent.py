from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.agent_manager import AgentManager
from app.utils.database import get_db, AsyncSession

router = APIRouter()

# 初始化智能体管理器
agent_manager = AgentManager()

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
        # TODO: 从数据库或配置中加载指定工具
        pass
        
    try:
        # 处理任务
        result, metadata = await agent_manager.process_task(
            task=request.task,
            use_framework=request.framework,
            tools=tools
        )
        
        return TaskResponse(
            result=result,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理任务时出错: {str(e)}"
        )
