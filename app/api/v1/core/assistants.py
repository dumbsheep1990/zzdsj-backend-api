"""
V1 API - 智能助手接口
提供简化的助手调用功能，专门为第三方开发者设计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

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

class AssistantListRequest(BaseModel):
    """助手列表请求模型"""
    category: Optional[str] = Field(None, description="助手分类")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    is_public: Optional[bool] = Field(True, description="是否只显示公开助手")
    limit: int = Field(default=20, ge=1, le=50, description="返回数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")


class AssistantCallRequest(BaseModel):
    """助手调用请求模型"""
    assistant_id: str = Field(..., description="助手ID")
    message: str = Field(..., min_length=1, max_length=4000, description="用户消息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    parameters: Optional[Dict[str, Any]] = Field(None, description="调用参数")
    stream: bool = Field(default=False, description="是否流式响应")


class AssistantCallResponse(BaseModel):
    """助手调用响应模型"""
    assistant_id: str = Field(..., description="助手ID")
    message_id: str = Field(..., description="消息ID")
    response: str = Field(..., description="助手回复")
    tokens_used: int = Field(..., description="使用的token数量")
    response_time: float = Field(..., description="响应时间（秒）")
    metadata: Dict[str, Any] = Field(default={}, description="元数据")


# ================================
# API接口实现
# ================================

@router.get("/list", response_model=Dict[str, Any], summary="获取助手列表")
async def list_assistants(
    category: Optional[str] = Query(None, description="助手分类"),
    tags: Optional[str] = Query(None, description="标签（逗号分隔）"),
    is_public: bool = Query(True, description="是否只显示公开助手"),
    limit: int = Query(20, ge=1, le=50, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取可用的智能助手列表
    
    返回第三方开发者可以调用的助手列表，包含基本信息和能力描述。
    """
    try:
        logger.info(f"V1 API - 获取助手列表: category={category}, limit={limit}")
        
        # 解析标签
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 构建查询参数
        query_params = {
            "category": category,
            "tags": tag_list,
            "is_public": is_public,
            "limit": limit,
            "offset": offset
        }
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 查询助手列表
        assistants_data = await assistant_service.list_public_assistants(query_params)
        
        # 过滤数据（移除敏感信息）
        filtered_assistants = []
        for assistant in assistants_data.get("items", []):
            filtered_assistant = V1DataFilter.filter_assistant_data(assistant)
            filtered_assistants.append(filtered_assistant)
        
        # 构建响应
        response_data = {
            "assistants": filtered_assistants,
            "total": assistants_data.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < assistants_data.get("total", 0)
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="获取助手列表成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手列表失败"
        )


@router.get("/{assistant_id}", response_model=Dict[str, Any], summary="获取助手详情")
async def get_assistant(
    assistant_id: str,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取指定助手的详细信息
    
    返回助手的基本信息、能力描述和使用说明。
    """
    try:
        logger.info(f"V1 API - 获取助手详情: assistant_id={assistant_id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 查询助手详情
        assistant_data = await assistant_service.get_assistant_public_info(assistant_id)
        
        if not assistant_data:
            raise HTTPException(
                status_code=404,
                detail="助手不存在或不可访问"
            )
        
        # 过滤数据
        filtered_assistant = V1DataFilter.filter_assistant_data(assistant_data)
        
        return ExternalResponseFormatter.format_success(
            data=filtered_assistant,
            message="获取助手详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取助手详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手详情失败"
        )


@router.post("/call", response_model=Dict[str, Any], summary="调用助手")
async def call_assistant(
    request: AssistantCallRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    调用指定助手进行对话
    
    发送消息给助手并获取回复。支持同步和流式响应。
    """
    try:
        logger.info(f"V1 API - 调用助手: assistant_id={request.assistant_id}")
        
        # 数据验证
        validated_data = ValidatorFactory.validate_data("v1_chat_request", {
            "message": request.message,
            "assistant_id": request.assistant_id,
            "stream": request.stream
        })
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 构建调用参数
        call_params = {
            "assistant_id": request.assistant_id,
            "message": validated_data["message"],
            "context": request.context or {},
            "parameters": request.parameters or {},
            "stream": request.stream,
            "api_mode": "v1_external"  # 标识为V1 API调用
        }
        
        # 调用助手
        if request.stream:
            # 流式响应
            return await _handle_streaming_response(chat_service, call_params)
        else:
            # 同步响应
            result = await chat_service.call_assistant_sync(call_params)
            
            # 过滤响应数据
            filtered_result = V1DataFilter.filter_chat_data(result)
            
            return ExternalResponseFormatter.format_success(
                data=filtered_result,
                message="助手调用成功"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 调用助手失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="助手调用失败"
        )


@router.get("/{assistant_id}/capabilities", response_model=Dict[str, Any], summary="获取助手能力")
async def get_assistant_capabilities(
    assistant_id: str,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取助手的能力描述
    
    返回助手支持的功能、工具和使用限制。
    """
    try:
        logger.info(f"V1 API - 获取助手能力: assistant_id={assistant_id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 查询助手能力
        capabilities = await assistant_service.get_assistant_capabilities(assistant_id)
        
        if not capabilities:
            raise HTTPException(
                status_code=404,
                detail="助手不存在或不可访问"
            )
        
        # 构建能力信息
        capability_data = {
            "assistant_id": assistant_id,
            "capabilities": capabilities.get("capabilities", []),
            "supported_tools": capabilities.get("tools", []),
            "model_info": {
                "model": capabilities.get("model"),
                "max_tokens": capabilities.get("max_tokens"),
                "temperature": capabilities.get("temperature")
            },
            "limitations": capabilities.get("limitations", {}),
            "usage_examples": capabilities.get("examples", [])
        }
        
        return ExternalResponseFormatter.format_success(
            data=capability_data,
            message="获取助手能力成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 获取助手能力失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手能力失败"
        )


@router.get("/categories", response_model=Dict[str, Any], summary="获取助手分类")
async def get_assistant_categories(
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    获取助手分类列表
    
    返回所有可用的助手分类和每个分类下的助手数量。
    """
    try:
        logger.info("V1 API - 获取助手分类")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 查询分类信息
        categories = await assistant_service.get_assistant_categories()
        
        return ExternalResponseFormatter.format_success(
            data={"categories": categories},
            message="获取助手分类成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 获取助手分类失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手分类失败"
        )


# ================================
# 辅助函数
# ================================

async def _handle_streaming_response(chat_service, call_params):
    """处理流式响应"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate_stream():
        try:
            async for chunk in chat_service.call_assistant_stream(call_params):
                # 过滤流式数据
                filtered_chunk = V1DataFilter.filter_chat_data(chunk)
                
                # 构建SSE格式响应
                sse_data = {
                    "status": "success",
                    "data": filtered_chunk,
                    "timestamp": chunk.get("timestamp")
                }
                
                yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"流式响应异常: {str(e)}", exc_info=True)
            error_data = {
                "status": "error",
                "message": "流式响应异常",
                "code": "streaming_error"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    ) 