from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.utils.database import get_db
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_definition_repository import AgentDefinitionRepository
from app.schemas.agent_definition import AgentRunRequest, AgentRunResponse
from app.core.agent_builder import AgentBuilder
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/run", response_model=AgentRunResponse)
async def run_agent_task(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    运行自定义智能体任务
    
    - **request**: 任务请求参数
    - 返回运行ID和初始状态
    """
    try:
        # 验证智能体定义是否存在
        definition_repo = AgentDefinitionRepository()
        definition = await definition_repo.get_by_id(request.definition_id, db)
        
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到智能体定义: {request.definition_id}"
            )
        
        # 检查访问权限
        if (not definition.is_public and 
            not definition.is_system and 
            definition.creator_id != current_user.id and 
            not current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限使用此智能体定义"
            )
        
        # 创建运行记录
        run_repo = AgentRunRepository()
        run_data = {
            "agent_definition_id": request.definition_id,
            "user_id": current_user.id,
            "task": request.task,
            "status": "pending",
            "metadata": {"parameters": request.parameters} if request.parameters else {}
        }
        
        run = await run_repo.create(run_data, db)
        
        # 在后台运行任务
        background_tasks.add_task(
            process_agent_task, 
            run_id=run.id, 
            definition_id=request.definition_id,
            task=request.task,
            parameters=request.parameters
        )
        
        return AgentRunResponse(
            run_id=run.id,
            status="pending",
            metadata={"message": "任务已提交，正在处理中"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {str(e)}"
        )

@router.get("/runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    agent_definition_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    列出智能体运行记录
    
    - **skip**: 跳过数量
    - **limit**: 限制数量
    - **agent_definition_id**: 按智能体定义ID筛选
    - **status**: 按状态筛选
    - 返回运行记录列表
    """
    try:
        repo = AgentRunRepository()
        runs = await repo.get_all(
            db, skip=skip, limit=limit,
            user_id=current_user.id,  # 只返回当前用户的运行记录
            agent_definition_id=agent_definition_id,
            status=status
        )
        
        return [
            AgentRunResponse(
                run_id=run.id,
                result=run.result,
                status=run.status,
                metadata={
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "duration": run.duration,
                    "agent_definition_id": run.agent_definition_id,
                    "task": run.task,
                    **run.metadata if run.metadata else {}
                }
            )
            for run in runs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取运行记录列表失败: {str(e)}"
        )

@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取特定智能体运行记录
    
    - **run_id**: 运行记录ID
    - 返回指定的运行记录
    """
    try:
        repo = AgentRunRepository()
        run = await repo.get_by_id(run_id, db)
        
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到运行记录: {run_id}"
            )
        
        # 检查访问权限
        if run.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此运行记录"
            )
        
        return AgentRunResponse(
            run_id=run.id,
            result=run.result,
            status=run.status,
            metadata={
                "start_time": run.start_time,
                "end_time": run.end_time,
                "duration": run.duration,
                "agent_definition_id": run.agent_definition_id,
                "task": run.task,
                "tool_calls": run.tool_calls,
                "error": run.error,
                **run.metadata if run.metadata else {}
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取运行记录失败: {str(e)}"
        )

@router.get("/runs/{run_id}/logs", response_model=Dict[str, Any])
async def get_agent_run_logs(
    run_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取智能体运行日志
    
    - **run_id**: 运行记录ID
    - 返回运行日志
    """
    try:
        repo = AgentRunRepository()
        run = await repo.get_by_id(run_id, db)
        
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到运行记录: {run_id}"
            )
        
        # 检查访问权限
        if run.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此运行记录日志"
            )
        
        # 获取工具调用记录作为日志
        logs = {
            "task": run.task,
            "status": run.status,
            "tool_calls": run.tool_calls or [],
            "start_time": run.start_time,
            "end_time": run.end_time,
            "duration": run.duration,
            "error": run.error
        }
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取运行日志失败: {str(e)}"
        )

async def process_agent_task(
    run_id: int, 
    definition_id: int, 
    task: str, 
    parameters: Optional[Dict[str, Any]] = None
):
    """
    后台处理智能体任务
    
    Args:
        run_id: 运行记录ID
        definition_id: 智能体定义ID
        task: 任务内容
        parameters: 任务参数
    """
    # 获取数据库会话
    db = next(get_db())
    
    # 获取仓库
    run_repo = AgentRunRepository()
    
    try:
        # 更新运行状态为进行中
        await run_repo.update_status(
            run_id, 
            status="running",
            metadata={"message": "任务已开始执行"},
            db=db
        )
        
        # 记录开始时间
        start_time = datetime.now().isoformat()
        await run_repo.update_status(
            run_id,
            status="running",
            metadata={"start_time": start_time},
            db=db
        )
        
        # 构建智能体
        agent_builder = AgentBuilder()
        agent = await agent_builder.build_from_definition(definition_id, db)
        
        # 处理任务参数
        formatted_task = task
        if parameters:
            for key, value in parameters.items():
                placeholder = f"{{{key}}}"
                if placeholder in formatted_task:
                    formatted_task = formatted_task.replace(placeholder, str(value))
        
        # 运行任务
        try:
            # 记录工具调用的回调函数
            async def tool_call_callback(tool_name, input_params, output):
                await run_repo.add_tool_call(
                    run_id,
                    {
                        "tool_name": tool_name,
                        "input": input_params,
                        "output": output,
                        "timestamp": datetime.now().isoformat()
                    },
                    db
                )
            
            # 设置回调
            if hasattr(agent, "set_tool_callback"):
                agent.set_tool_callback(tool_call_callback)
            
            # 执行任务
            result, metadata = await agent.run_task(formatted_task)
            
            # 更新运行记录
            await run_repo.update_status(
                run_id,
                status="completed",
                result=result,
                metadata=metadata,
                db=db
            )
        except Exception as e:
            # 记录执行错误
            await run_repo.update_status(
                run_id,
                status="failed",
                error=str(e),
                metadata={"error_details": str(e)},
                db=db
            )
            raise
    except Exception as e:
        # 确保任何未捕获的错误都被记录
        try:
            await run_repo.update_status(
                run_id,
                status="failed",
                error=f"处理任务时出错: {str(e)}",
                db=db
            )
        except Exception:
            pass
        
        # 记录错误日志
        import logging
        logging.error(f"处理任务 {run_id} 失败: {str(e)}", exc_info=True)
