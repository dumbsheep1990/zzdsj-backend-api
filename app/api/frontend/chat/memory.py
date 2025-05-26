"""
智能体记忆系统 - 前端API路由

提供记忆系统的REST API接口，为聊天和助手功能提供记忆支持。
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.utils.database import get_db
from app.memory.manager import get_memory_manager
from app.schemas.memory import (
    MemoryCreateRequest, 
    MemoryUpdateRequest,
    MemoryResponse,
    MemoryQueryRequest,
    MemoryQueryResponse
)
from app.api.frontend.dependencies import ResponseFormatter

router = APIRouter()

# 创建记忆
@router.post("/agents/{agent_id}", response_model=MemoryResponse)
async def create_agent_memory(
    agent_id: str = Path(..., description="智能体ID"),
    memory_data: MemoryCreateRequest = None,
    db: Session = Depends(get_db)
):
    """为智能体创建新记忆"""
    memory_manager = get_memory_manager()
    
    try:
        from app.memory.interfaces import MemoryConfig, MemoryType
        
        # 解析配置
        config = None
        if memory_data and memory_data.config:
            config = MemoryConfig(
                memory_type=MemoryType[memory_data.config.memory_type],
                ttl=memory_data.config.ttl,
                max_tokens=memory_data.config.max_tokens,
                max_items=memory_data.config.max_items,
                retrieval_strategy=memory_data.config.retrieval_strategy,
                storage_backend=memory_data.config.storage_backend,
                vector_backend=memory_data.config.vector_backend
            )
            
        memory_content = memory_data.content if memory_data else None
        
        # 创建记忆
        memory = await memory_manager.create_agent_memory(
            agent_id=agent_id,
            config=config,
            content=memory_content,
            db=db
        )
        
        result = {
            "memory_id": memory.memory_id,
            "agent_id": agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__,
            "status": "created"
        }
        
        return ResponseFormatter.format_success(result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建记忆失败: {str(e)}")

# 获取记忆
@router.get("/agents/{agent_id}", response_model=MemoryResponse)
async def get_agent_memory(
    agent_id: str = Path(..., description="智能体ID"),
    db: Session = Depends(get_db)
):
    """获取智能体记忆"""
    memory_manager = get_memory_manager()
    
    try:
        # 获取记忆
        memory = await memory_manager.get_agent_memory(agent_id, db)
        
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到智能体 {agent_id} 的记忆")
        
        result = {
            "memory_id": memory.memory_id,
            "agent_id": agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__,
            "status": "active"
        }
        
        return ResponseFormatter.format_success(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取记忆失败: {str(e)}")

# 查询记忆内容
@router.post("/agents/{agent_id}/query", response_model=MemoryQueryResponse)
async def query_agent_memory(
    agent_id: str = Path(..., description="智能体ID"),
    query_data: MemoryQueryRequest = None,
    db: Session = Depends(get_db)
):
    """查询智能体记忆内容"""
    memory_manager = get_memory_manager()
    
    try:
        # 获取记忆
        memory = await memory_manager.get_agent_memory(agent_id, db)
        
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到智能体 {agent_id} 的记忆")
        
        # 执行查询
        query = query_data.query if query_data else ""
        top_k = query_data.top_k if query_data else 5
        
        memory_items = await memory.query(query, top_k)
        
        # 格式化结果
        results = []
        for key, value, score in memory_items:
            results.append({
                "key": key,
                "content": value,
                "relevance_score": score
            })
        
        result = {
            "agent_id": agent_id,
            "query": query,
            "results": results,
            "total": len(results)
        }
        
        return ResponseFormatter.format_success(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"查询记忆失败: {str(e)}")

# 添加记忆项
@router.post("/agents/{agent_id}/items", response_model=MemoryResponse)
async def add_memory_item(
    agent_id: str = Path(..., description="智能体ID"),
    item_data: Dict[str, Any] = None,
    key: str = Query(None, description="记忆键名"),
    db: Session = Depends(get_db)
):
    """为智能体添加记忆项"""
    memory_manager = get_memory_manager()
    
    try:
        # 获取记忆
        memory = await memory_manager.get_agent_memory(agent_id, db)
        
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到智能体 {agent_id} 的记忆")
        
        # 生成键名
        if not key:
            import uuid
            key = f"item_{uuid.uuid4()}"
        
        # 添加记忆项
        await memory.add(key, item_data)
        
        result = {
            "memory_id": memory.memory_id,
            "agent_id": agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__,
            "status": "updated"
        }
        
        return ResponseFormatter.format_success(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"添加记忆项失败: {str(e)}")

# 清空记忆
@router.delete("/agents/{agent_id}", response_model=MemoryResponse)
async def clear_agent_memory(
    agent_id: str = Path(..., description="智能体ID"),
    db: Session = Depends(get_db)
):
    """清空智能体记忆"""
    memory_manager = get_memory_manager()
    
    try:
        # 获取记忆
        memory = await memory_manager.get_agent_memory(agent_id, db)
        
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到智能体 {agent_id} 的记忆")
        
        # 清空记忆
        await memory.clear()
        
        result = {
            "memory_id": memory.memory_id,
            "agent_id": agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__,
            "status": "cleared"
        }
        
        return ResponseFormatter.format_success(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"清空记忆失败: {str(e)}")

# 删除记忆项
@router.delete("/agents/{agent_id}/items/{key}", response_model=MemoryResponse)
async def delete_memory_item(
    agent_id: str = Path(..., description="智能体ID"),
    key: str = Path(..., description="记忆键名"),
    db: Session = Depends(get_db)
):
    """删除智能体记忆项"""
    memory_manager = get_memory_manager()
    
    try:
        # 获取记忆
        memory = await memory_manager.get_agent_memory(agent_id, db)
        
        if not memory:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到智能体 {agent_id} 的记忆")
        
        # 删除记忆项
        success = await memory.delete(key)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到记忆项 {key}")
        
        result = {
            "memory_id": memory.memory_id,
            "agent_id": agent_id,
            "created_at": memory.created_at,
            "updated_at": memory.last_accessed,
            "config": memory.config.__dict__,
            "status": "updated"
        }
        
        return ResponseFormatter.format_success(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除记忆项失败: {str(e)}") 