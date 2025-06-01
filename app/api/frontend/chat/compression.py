"""
上下文压缩API模块 - 前端路由
提供管理和使用上下文压缩功能的接口，优化对话上下文
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.utils.core.database import get_db
from app.services.context_compression_service import ContextCompressionService
from app.schemas.context_compression import (
    CompressionToolCreate,
    CompressionToolResponse,
    AgentCompressionConfigCreate,
    AgentCompressionConfigResponse,
    CompressionExecutionResponse,
    CompressionConfig,
    CompressedContextResult
)
from app.api.frontend.dependencies import ResponseFormatter


router = APIRouter()

@router.post("/compress", response_model=CompressedContextResult)
async def compress_context(
    content: str,
    query: Optional[str] = None,
    agent_id: Optional[int] = None,
    config: Optional[CompressionConfig] = None,
    model_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    压缩上下文内容
    
    可以指定代理ID来使用其配置，或者直接提供配置对象
    """
    service = ContextCompressionService(db)
    try:
        result = await service.compress_context(
            content=content,
            query=query,
            agent_id=agent_id,
            config=config,
            model_name=model_name
        )
        return ResponseFormatter.format_success(result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"压缩上下文失败: {str(e)}")


# 工具管理接口
@router.post("/tools", response_model=CompressionToolResponse)
def create_compression_tool(
    tool: CompressionToolCreate,
    db: Session = Depends(get_db)
):
    """创建新的上下文压缩工具"""
    service = ContextCompressionService(db)
    try:
        db_tool = service.create_compression_tool(tool.dict())
        return ResponseFormatter.format_success(db_tool)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建压缩工具失败: {str(e)}")


@router.get("/tools", response_model=List[CompressionToolResponse])
def get_compression_tools(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取所有上下文压缩工具"""
    service = ContextCompressionService(db)
    try:
        tools = service.get_compression_tools(skip=skip, limit=limit)
        return ResponseFormatter.format_success(tools)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取压缩工具失败: {str(e)}")


@router.get("/tools/{tool_id}", response_model=CompressionToolResponse)
def get_compression_tool(
    tool_id: int,
    db: Session = Depends(get_db)
):
    """获取指定ID的上下文压缩工具"""
    service = ContextCompressionService(db)
    try:
        tool = service.get_compression_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="压缩工具未找到")
        return ResponseFormatter.format_success(tool)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取压缩工具失败: {str(e)}")


@router.put("/tools/{tool_id}", response_model=CompressionToolResponse)
def update_compression_tool(
    tool_id: int,
    tool_data: CompressionToolCreate,
    db: Session = Depends(get_db)
):
    """更新上下文压缩工具"""
    service = ContextCompressionService(db)
    try:
        updated_tool = service.update_compression_tool(tool_id, tool_data.dict())
        if not updated_tool:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="压缩工具未找到")
        return ResponseFormatter.format_success(updated_tool)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新压缩工具失败: {str(e)}")


@router.delete("/tools/{tool_id}", response_model=Dict[str, bool])
def delete_compression_tool(
    tool_id: int,
    db: Session = Depends(get_db)
):
    """删除上下文压缩工具"""
    service = ContextCompressionService(db)
    try:
        success = service.delete_compression_tool(tool_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="压缩工具未找到")
        return ResponseFormatter.format_success({"success": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除压缩工具失败: {str(e)}")


# 代理配置管理接口
@router.post("/agent-configs", response_model=AgentCompressionConfigResponse)
def create_agent_config(
    config: AgentCompressionConfigCreate,
    db: Session = Depends(get_db)
):
    """创建或更新智能体的上下文压缩配置"""
    service = ContextCompressionService(db)
    try:
        db_config = service.create_agent_config(config.dict())
        return ResponseFormatter.format_success(db_config)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建代理配置失败: {str(e)}")


@router.get("/agent-configs", response_model=List[AgentCompressionConfigResponse])
def get_agent_configs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取所有智能体的上下文压缩配置"""
    service = ContextCompressionService(db)
    try:
        configs = service.get_agent_configs(skip=skip, limit=limit)
        return ResponseFormatter.format_success(configs)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取代理配置失败: {str(e)}")


@router.get("/agent-configs/{config_id}", response_model=AgentCompressionConfigResponse)
def get_agent_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """获取指定ID的智能体上下文压缩配置"""
    service = ContextCompressionService(db)
    try:
        config = service.get_agent_config(config_id)
        if not config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="压缩配置未找到")
        return ResponseFormatter.format_success(config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取代理配置失败: {str(e)}")


@router.get("/agent-configs/agent/{agent_id}", response_model=AgentCompressionConfigResponse)
def get_agent_config_by_agent_id(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """根据智能体ID获取上下文压缩配置"""
    service = ContextCompressionService(db)
    try:
        config = service.get_agent_config_by_agent_id(agent_id)
        if not config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该智能体的压缩配置未找到")
        return ResponseFormatter.format_success(config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取代理配置失败: {str(e)}")


@router.put("/agent-configs/{config_id}", response_model=AgentCompressionConfigResponse)
def update_agent_config(
    config_id: int,
    config_data: AgentCompressionConfigCreate,
    db: Session = Depends(get_db)
):
    """更新智能体上下文压缩配置"""
    service = ContextCompressionService(db)
    try:
        updated_config = service.update_agent_config(config_id, config_data.dict())
        if not updated_config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="压缩配置未找到")
        return ResponseFormatter.format_success(updated_config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新代理配置失败: {str(e)}")


@router.delete("/agent-configs/{config_id}", response_model=Dict[str, bool])
def delete_agent_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """删除智能体上下文压缩配置"""
    service = ContextCompressionService(db)
    try:
        success = service.delete_agent_config(config_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="压缩配置未找到")
        return ResponseFormatter.format_success({"success": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除代理配置失败: {str(e)}")


# 执行记录接口
@router.get("/executions", response_model=List[CompressionExecutionResponse])
def get_execution_records(
    skip: int = 0,
    limit: int = 100,
    agent_id: Optional[int] = None,
    config_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取上下文压缩执行记录"""
    service = ContextCompressionService(db)
    try:
        records = service.get_execution_records(
            skip=skip,
            limit=limit,
            agent_id=agent_id,
            config_id=config_id
        )
        return ResponseFormatter.format_success(records)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取执行记录失败: {str(e)}")


@router.get("/executions/{execution_id}", response_model=CompressionExecutionResponse)
def get_execution_record(
    execution_id: str,
    db: Session = Depends(get_db)
):
    """获取指定ID的上下文压缩执行记录"""
    service = ContextCompressionService(db)
    try:
        record = service.get_execution_record(execution_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行记录未找到")
        return ResponseFormatter.format_success(record)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取执行记录失败: {str(e)}") 