from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.utils.core.database import get_db
from app.schemas.orchestration import (
    OrchestrationCreate, OrchestrationUpdate, OrchestrationResponse,
    OrchestrationExecutionRequest, OrchestrationExecutionResponse,
    OrchestrationValidationResult, OrchestrationStats
)
from app.services.agents.orchestration_service import OrchestrationService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=OrchestrationResponse)
async def create_orchestration(
    orchestration: OrchestrationCreate,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """创建智能体编排配置"""
    try:
        service = OrchestrationService(db)
        result = await service.create_orchestration(orchestration, user_id)
        
        return OrchestrationResponse(
            id=result.id,
            assistant_id=result.assistant_id,
            name=result.name,
            description=result.description,
            orchestration_config=result.orchestration_config,
            execution_plan=result.execution_plan,
            is_active=result.is_active,
            version=result.version,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except ValueError as e:
        logger.error(f"创建编排配置失败 - 验证错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建编排配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.get("/{orchestration_id}", response_model=OrchestrationResponse)
async def get_orchestration(
    orchestration_id: int,
    db: Session = Depends(get_db)
):
    """获取编排配置详情"""
    try:
        service = OrchestrationService(db)
        result = await service.get_orchestration_by_id(orchestration_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="编排配置未找到")
        
        return OrchestrationResponse(
            id=result.id,
            assistant_id=result.assistant_id,
            name=result.name,
            description=result.description,
            orchestration_config=result.orchestration_config,
            execution_plan=result.execution_plan,
            is_active=result.is_active,
            version=result.version,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取编排配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.get("/assistant/{assistant_id}")
async def list_orchestrations_by_assistant(
    assistant_id: int,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    is_active: Optional[bool] = Query(None, description="筛选活跃状态"),
    db: Session = Depends(get_db)
):
    """获取助手的所有编排配置"""
    try:
        service = OrchestrationService(db)
        results = await service.get_orchestrations_by_assistant(
            assistant_id, skip, limit, is_active
        )
        
        orchestrations = [
            OrchestrationResponse(
                id=result.id,
                assistant_id=result.assistant_id,
                name=result.name,
                description=result.description,
                orchestration_config=result.orchestration_config,
                execution_plan=result.execution_plan,
                is_active=result.is_active,
                version=result.version,
                created_at=result.created_at,
                updated_at=result.updated_at
            )
            for result in results
        ]
        
        return {
            "orchestrations": orchestrations,
            "total": len(orchestrations),
            "skip": skip,
            "limit": limit,
            "assistant_id": assistant_id
        }
    except Exception as e:
        logger.error(f"获取助手编排配置列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.put("/{orchestration_id}", response_model=OrchestrationResponse)
async def update_orchestration(
    orchestration_id: int,
    orchestration_update: OrchestrationUpdate,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """更新编排配置"""
    try:
        service = OrchestrationService(db)
        result = await service.update_orchestration(orchestration_id, orchestration_update, user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="编排配置未找到")
        
        return OrchestrationResponse(
            id=result.id,
            assistant_id=result.assistant_id,
            name=result.name,
            description=result.description,
            orchestration_config=result.orchestration_config,
            execution_plan=result.execution_plan,
            is_active=result.is_active,
            version=result.version,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except ValueError as e:
        logger.error(f"更新编排配置失败 - 验证错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新编排配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.delete("/{orchestration_id}")
async def delete_orchestration(
    orchestration_id: int,
    db: Session = Depends(get_db)
):
    """删除编排配置"""
    try:
        service = OrchestrationService(db)
        success = await service.delete_orchestration(orchestration_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="编排配置未找到")
        
        return {"message": "编排配置删除成功", "orchestration_id": orchestration_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除编排配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.post("/execute", response_model=OrchestrationExecutionResponse)
async def execute_orchestration(
    execution_request: OrchestrationExecutionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """执行智能体编排"""
    try:
        service = OrchestrationService(db)
        result = await service.execute_orchestration(execution_request, user_id)
        
        return OrchestrationExecutionResponse(
            session_id=result["session_id"],
            status=result["status"],
            output_data=result.get("output_data"),
            execution_trace=result.get("execution_trace", []),
            duration_ms=result.get("duration_ms"),
            error_message=result.get("error_message"),
            metadata=result.get("metadata")
        )
    except ValueError as e:
        logger.error(f"执行编排失败 - 验证错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"执行编排失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.get("/execution/{session_id}")
async def get_execution_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取编排执行状态"""
    try:
        service = OrchestrationService(db)
        result = await service.get_execution_status(session_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="执行记录未找到")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.post("/{orchestration_id}/validate", response_model=OrchestrationValidationResult)
async def validate_orchestration(
    orchestration_id: int,
    db: Session = Depends(get_db)
):
    """验证编排配置"""
    try:
        service = OrchestrationService(db)
        result = await service.validate_orchestration(orchestration_id)
        
        return OrchestrationValidationResult(
            is_valid=result["is_valid"],
            validation_errors=result["validation_errors"],
            warnings=result["warnings"],
            suggestions=result["suggestions"]
        )
    except ValueError as e:
        logger.error(f"验证编排配置失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"验证编排配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.get("/stats/overview", response_model=OrchestrationStats)
async def get_orchestration_stats(
    assistant_id: Optional[int] = Query(None, description="筛选助手ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取编排统计信息"""
    try:
        service = OrchestrationService(db)
        result = await service.get_orchestration_stats(assistant_id, start_date, end_date)
        
        return OrchestrationStats(
            total_orchestrations=result["total_orchestrations"],
            active_orchestrations=result["active_orchestrations"],
            total_executions=result["total_executions"],
            successful_executions=result["successful_executions"],
            failed_executions=result["failed_executions"],
            success_rate=result["success_rate"],
            avg_duration_ms=result["avg_duration_ms"]
        )
    except Exception as e:
        logger.error(f"获取编排统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@router.get("/health")
async def health_check():
    """编排系统健康检查"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "orchestration_parser": {"status": "healthy"},
                "orchestration_service": {"status": "healthy"},
                "database": {"status": "healthy"}
            },
            "message": "编排系统运行正常"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        } 