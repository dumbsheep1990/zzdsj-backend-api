"""
LightRAG API v1路由模块
提供LightRAG知识图谱服务的API接口
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from enum import Enum

from app.utils.common.logger import setup_logger
from app.utils.core.database import get_db
from app.messaging.core.models import MessageRole, TextMessage
from app.messaging.services.message_service import MessageService
from app.messaging.services.stream_service import StreamService
from app.messaging.response_formatter import ResponseFormatter
from app.messaging.adapters.lightrag import LightRAGAdapter, LightRAGQueryMode
from app.schemas.lightrag import (
    LightRAGQueryRequest,
    LightRAGModeQueryRequest,
    GraphReference
)
from app.api.v1.dependencies import get_lightrag_adapter, get_message_service, get_stream_service
from app.frameworks.lightrag.client import get_lightrag_client

router = APIRouter()
logger = setup_logger("lightrag_api")

@router.post("/query", response_model=Dict[str, Any])
async def query_knowledge_graph(
    query_request: LightRAGQueryRequest,
    lightrag_adapter: LightRAGAdapter = Depends(get_lightrag_adapter),
    db: Session = Depends(get_db)
):
    """
    查询知识图谱
    使用默认hybrid模式，自动处理查询前缀
    """
    # 验证请求参数
    if not query_request.graph_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供一个图谱ID"
        )
    
    # 检查LightRAG服务是否可用
    client = get_lightrag_client()
    if not client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LightRAG服务不可用"
        )
    
    # 创建查询消息
    query_message = TextMessage(
        content=query_request.query,
        role=MessageRole.USER
    )
    
    # 使用LightRAG适配器处理查询
    try:
        if query_request.stream:
            # 流式响应
            stream_service = await lightrag_adapter.to_sse_response(
                messages=[query_message],
                graph_ids=query_request.graph_ids,
                model_name=query_request.model_name
            )
            return Response(
                content=stream_service.get_stream_content(),
                media_type="text/event-stream"
            )
        else:
            # 同步响应
            response_messages = await lightrag_adapter.process_messages(
                messages=[query_message],
                graph_ids=query_request.graph_ids,
                model_name=query_request.model_name
            )
            
            # 使用OpenAI兼容格式返回结果
            return ResponseFormatter.format_openai_compatible(response_messages)
    except Exception as e:
        logger.error(f"知识图谱查询错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识图谱查询出错: {str(e)}"
        )


@router.post("/query-with-mode", response_model=Dict[str, Any])
async def query_with_mode(
    query_request: LightRAGModeQueryRequest,
    lightrag_adapter: LightRAGAdapter = Depends(get_lightrag_adapter),
    db: Session = Depends(get_db)
):
    """
    使用指定模式查询知识图谱
    支持所有LightRAG查询模式和前缀
    """
    # 验证请求参数
    if not query_request.graph_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供一个图谱ID"
        )
    
    # 检查LightRAG服务是否可用
    client = get_lightrag_client()
    if not client.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LightRAG服务不可用"
        )
    
    # 创建查询消息
    query_message = TextMessage(
        content=query_request.query,
        role=MessageRole.USER
    )
    
    # 使用LightRAG适配器处理查询
    try:
        if query_request.stream:
            # 流式响应
            stream_service = await lightrag_adapter.to_sse_response(
                messages=[query_message],
                graph_ids=query_request.graph_ids,
                query_mode=query_request.mode,
                return_context_only=query_request.return_context_only,
                bypass_rag=query_request.bypass_rag,
                model_name=query_request.model_name
            )
            return Response(
                content=stream_service.get_stream_content(),
                media_type="text/event-stream"
            )
        else:
            # 同步响应
            response_messages = await lightrag_adapter.process_messages(
                messages=[query_message],
                graph_ids=query_request.graph_ids,
                query_mode=query_request.mode,
                return_context_only=query_request.return_context_only,
                bypass_rag=query_request.bypass_rag,
                model_name=query_request.model_name
            )
            
            # 使用OpenAI兼容格式返回结果
            return ResponseFormatter.format_openai_compatible(response_messages)
    except Exception as e:
        logger.error(f"知识图谱查询错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识图谱查询出错: {str(e)}"
        )


@router.get("/graphs", response_model=Dict[str, Any])
async def list_knowledge_graphs(
    db: Session = Depends(get_db)
):
    """
    获取所有知识图谱列表
    """
    try:
        client = get_lightrag_client()
        if not client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LightRAG服务不可用"
            )
        
        result = client.list_workdirs()
        if result.get("success", False):
            return {
                "success": True,
                "graphs": result.get("graphs", [])
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "获取知识图谱列表失败")
            )
    except Exception as e:
        logger.error(f"获取知识图谱列表错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识图谱列表错误: {str(e)}"
        )


@router.get("/graphs/{graph_id}", response_model=Dict[str, Any])
async def get_knowledge_graph(
    graph_id: str,
    db: Session = Depends(get_db)
):
    """
    获取知识图谱详情
    """
    try:
        client = get_lightrag_client()
        if not client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LightRAG服务不可用"
            )
        
        result = client.get_workdir_info(graph_id)
        if result.get("success", False):
            return {
                "success": True,
                "graph": result.get("graph", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "知识图谱不存在")
            )
    except Exception as e:
        logger.error(f"获取知识图谱详情错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识图谱详情错误: {str(e)}"
        )


@router.get("/graphs/{graph_id}/stats", response_model=Dict[str, Any])
async def get_knowledge_graph_stats(
    graph_id: str,
    db: Session = Depends(get_db)
):
    """
    获取知识图谱统计信息
    """
    try:
        client = get_lightrag_client()
        if not client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LightRAG服务不可用"
            )
        
        result = client.get_workdir_stats(graph_id)
        if result.get("success", False):
            return {
                "success": True,
                "stats": result.get("stats", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "知识图谱不存在")
            )
    except Exception as e:
        logger.error(f"获取知识图谱统计信息错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识图谱统计信息错误: {str(e)}"
        )
