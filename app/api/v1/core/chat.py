"""
V1 API - 对话聊天接口
提供基础的对话功能，专门为第三方开发者设计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import json
from datetime import datetime

from app.api.v1.dependencies import (
    V1ServiceContainer, 
    V1Context, 
    V1DataFilter,
    get_v1_service_container,
    get_v1_context,
    APIKey
)
from app.api.shared.responses import ExternalResponseFormatter
from app.api.shared.validators import ValidatorFactory

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 请求/响应模型
# ================================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    assistant_id: Optional[str] = Field(None, description="指定助手ID（可选）")
    conversation_id: Optional[str] = Field(None, description="对话ID（用于继续对话）")
    stream: bool = Field(default=False, description="是否流式响应")
    model: Optional[str] = Field(None, description="指定模型（可选）")
    parameters: Optional[Dict[str, Any]] = Field(None, description="对话参数")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message_id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    response: str = Field(..., description="助手回复")
    assistant_id: Optional[str] = Field(None, description="使用的助手ID")
    model: str = Field(..., description="使用的模型")
    tokens_used: int = Field(..., description="消耗的token数量")
    response_time: float = Field(..., description="响应时间（秒）")
    created_at: str = Field(..., description="创建时间")


class ConversationHistoryRequest(BaseModel):
    """对话历史请求模型"""
    conversation_id: str = Field(..., description="对话ID")
    limit: int = Field(default=20, ge=1, le=100, description="返回消息数量")
    offset: int = Field(default=0, ge=0, description="偏移量")


# ================================
# API接口实现
# ================================

@router.post("/message", response_model=Dict[str, Any], summary="发送消息")
async def send_message(
    request: ChatRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    发送消息并获取AI回复
    
    支持指定助手、继续对话、流式响应等功能。
    """
    try:
        logger.info(f"V1 API - 发送消息: assistant_id={request.assistant_id}, stream={request.stream}")
        
        # 数据验证
        validated_data = ValidatorFactory.validate_data("v1_chat_request", {
            "message": request.message,
            "assistant_id": request.assistant_id or "default",
            "stream": request.stream
        })
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 构建聊天参数
        chat_params = {
            "message": validated_data["message"],
            "assistant_id": request.assistant_id,
            "conversation_id": request.conversation_id,
            "model": request.model,
            "parameters": request.parameters or {},
            "api_mode": "v1_external",
            "stream": request.stream
        }
        
        # 处理聊天请求
        if request.stream:
            # 流式响应
            return await _handle_chat_stream(chat_service, chat_params)
        else:
            # 同步响应
            result = await chat_service.send_message(chat_params)
            
            # 过滤响应数据
            filtered_result = V1DataFilter.filter_chat_data(result)
            
            return ExternalResponseFormatter.format_success(
                data=filtered_result,
                message="消息发送成功"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 发送消息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="消息发送失败"
        )


@router.get("/conversations/{conversation_id}/history", response_model=Dict[str, Any], summary="获取对话历史")
async def get_conversation_history(
    conversation_id: str,
    limit: int = Query(20, ge=1, le=100, description="返回消息数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取指定对话的历史记录
    
    返回对话中的消息列表，支持分页。
    """
    try:
        logger.info(f"V1 API - 获取对话历史: conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 查询对话历史
        history_data = await chat_service.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            api_mode="v1_external"
        )
        
        if not history_data:
            raise HTTPException(
                status_code=404,
                detail="对话不存在或无权访问"
            )
        
        # 过滤历史数据
        filtered_messages = []
        for message in history_data.get("messages", []):
            filtered_message = V1DataFilter.filter_chat_data(message)
            filtered_messages.append(filtered_message)
        
        # 构建响应
        response_data = {
            "conversation_id": conversation_id,
            "messages": filtered_messages,
            "total": history_data.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < history_data.get("total", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="获取对话历史成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取对话历史失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取对话历史失败"
        )


@router.get("/conversations", response_model=Dict[str, Any], summary="获取对话列表")
async def list_conversations(
    limit: int = Query(20, ge=1, le=50, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取用户的对话列表
    
    返回当前API用户的所有对话，包含基本信息。
    """
    try:
        logger.info("V1 API - 获取对话列表")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 查询对话列表（基于API用户）
        conversations_data = await chat_service.list_conversations(
            api_mode="v1_external",
            limit=limit,
            offset=offset
        )
        
        # 过滤对话数据
        filtered_conversations = []
        for conversation in conversations_data.get("items", []):
            filtered_conversation = V1DataFilter.filter_chat_data(conversation)
            filtered_conversations.append(filtered_conversation)
        
        # 构建响应
        response_data = {
            "conversations": filtered_conversations,
            "total": conversations_data.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < conversations_data.get("total", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="获取对话列表成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取对话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取对话列表失败"
        )


@router.post("/conversations", response_model=Dict[str, Any], summary="创建新对话")
async def create_conversation(
    title: Optional[str] = Field(None, description="对话标题"),
    assistant_id: Optional[str] = Field(None, description="指定助手ID"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    创建新的对话
    
    创建一个新的对话会话，可以指定助手和标题。
    """
    try:
        logger.info(f"V1 API - 创建对话: assistant_id={assistant_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 创建对话参数
        create_params = {
            "title": title,
            "assistant_id": assistant_id,
            "api_mode": "v1_external"
        }
        
        # 创建对话
        conversation_data = await chat_service.create_conversation(create_params)
        
        # 过滤响应数据
        filtered_conversation = V1DataFilter.filter_chat_data(conversation_data)
        
        return ExternalResponseFormatter.format_success(
            data=filtered_conversation,
            message="创建对话成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 创建对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="创建对话失败"
        )


@router.delete("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="删除对话")
async def delete_conversation(
    conversation_id: str,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    删除指定对话
    
    永久删除对话及其所有消息记录。
    """
    try:
        logger.info(f"V1 API - 删除对话: conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 删除对话
        success = await chat_service.delete_conversation(
            conversation_id=conversation_id,
            api_mode="v1_external"
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="对话不存在或无权删除"
            )
        
        return ExternalResponseFormatter.format_success(
            data={"conversation_id": conversation_id, "deleted": True},
            message="删除对话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 删除对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="删除对话失败"
        )


@router.get("/models", response_model=Dict[str, Any], summary="获取可用模型")
async def list_available_models(
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取可用的AI模型列表
    
    返回当前可用于对话的AI模型信息。
    """
    try:
        logger.info("V1 API - 获取可用模型")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 查询可用模型
        models_data = await ai_service.list_available_models(api_mode="v1_external")
        
        return ExternalResponseFormatter.format_success(
            data={"models": models_data},
            message="获取模型列表成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取模型列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取模型列表失败"
        )


# ================================
# 辅助函数
# ================================

async def _handle_chat_stream(chat_service, chat_params):
    """处理流式聊天响应"""
    
    async def generate_chat_stream():
        try:
            # 初始化流式对话
            stream_generator = chat_service.send_message_stream(chat_params)
            
            # 发送开始事件
            start_event = {
                "event": "start",
                "data": {
                    "conversation_id": chat_params.get("conversation_id"),
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
            
            # 处理流式数据
            async for chunk in stream_generator:
                # 过滤流式数据
                filtered_chunk = V1DataFilter.filter_chat_data(chunk)
                
                # 构建流式事件
                stream_event = {
                    "event": "message",
                    "data": filtered_chunk
                }
                
                yield f"data: {json.dumps(stream_event, ensure_ascii=False)}\n\n"
            
            # 发送结束事件
            end_event = {
                "event": "end",
                "data": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"流式聊天异常: {str(e)}", exc_info=True)
            error_event = {
                "event": "error",
                "data": {
                    "error": "流式响应异常",
                    "code": "streaming_error",
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_chat_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream"
        }
    ) 