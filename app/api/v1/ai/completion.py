"""
V1 API - AI文本生成接口
提供AI文本生成功能，专门为第三方开发者设计
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Union
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

class CompletionRequest(BaseModel):
    """文本生成请求模型"""
    prompt: str = Field(..., min_length=1, max_length=8000, description="输入提示词")
    model: Optional[str] = Field(None, description="指定模型")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="最大生成token数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="创造性参数")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="核采样参数")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止序列")
    stream: bool = Field(default=False, description="是否流式输出")


class ChatCompletionRequest(BaseModel):
    """对话补全请求模型"""
    messages: List[Dict[str, str]] = Field(..., description="对话消息列表")
    model: Optional[str] = Field(None, description="指定模型")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="最大生成token数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="创造性参数")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="核采样参数")
    stream: bool = Field(default=False, description="是否流式输出")
    functions: Optional[List[Dict[str, Any]]] = Field(None, description="可调用函数定义")
    function_call: Optional[Union[str, Dict[str, str]]] = Field(None, description="函数调用控制")


class SummarizationRequest(BaseModel):
    """文本摘要请求模型"""
    text: str = Field(..., min_length=50, max_length=20000, description="待摘要文本")
    model: Optional[str] = Field(None, description="指定模型")
    max_summary_length: int = Field(default=200, ge=50, le=1000, description="摘要最大长度")
    style: str = Field(default="concise", description="摘要风格: concise, detailed, bullet_points")


class TranslationRequest(BaseModel):
    """文本翻译请求模型"""
    text: str = Field(..., min_length=1, max_length=5000, description="待翻译文本")
    target_language: str = Field(..., description="目标语言")
    source_language: Optional[str] = Field(None, description="源语言（自动检测）")
    model: Optional[str] = Field(None, description="指定模型")


# ================================
# API接口实现
# ================================

@router.post("/text", response_model=Dict[str, Any], summary="文本生成")
async def generate_text(
    request: CompletionRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    AI文本生成
    
    基于提示词生成文本内容，支持多种参数调整。
    """
    try:
        logger.info(f"V1 API - 文本生成: prompt={request.prompt[:50]}..., model={request.model}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 构建生成参数
        generation_params = {
            "prompt": request.prompt,
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stop": request.stop,
            "stream": request.stream,
            "api_mode": "v1_external"
        }
        
        # 处理生成请求
        if request.stream:
            # 流式生成
            return await _handle_text_stream(ai_service, generation_params)
        else:
            # 同步生成
            result = await ai_service.generate_text(generation_params)
            
            # 构建响应
            response_data = {
                "text": result.get("generated_text", ""),
                "model": result.get("model", request.model),
                "tokens_used": result.get("tokens_used", 0),
                "generation_time": result.get("generation_time", 0),
                "finish_reason": result.get("finish_reason", "stop"),
                "metadata": {
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "total_tokens": result.get("total_tokens", 0)
                }
            }
            
            return ExternalResponseFormatter.format_success(
                data=response_data,
                message="文本生成成功"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 文本生成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="文本生成失败"
        )


@router.post("/chat", response_model=Dict[str, Any], summary="对话补全")
async def chat_completion(
    request: ChatCompletionRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    对话补全
    
    基于对话历史生成AI回复，支持函数调用。
    """
    try:
        logger.info(f"V1 API - 对话补全: messages_count={len(request.messages)}, model={request.model}")
        
        # 验证消息格式
        for i, message in enumerate(request.messages):
            if "role" not in message or "content" not in message:
                raise HTTPException(
                    status_code=400,
                    detail=f"消息{i}格式错误，需要包含role和content字段"
                )
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 构建对话参数
        chat_params = {
            "messages": request.messages,
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream,
            "functions": request.functions,
            "function_call": request.function_call,
            "api_mode": "v1_external"
        }
        
        # 处理对话请求
        if request.stream:
            # 流式对话
            return await _handle_chat_stream(ai_service, chat_params)
        else:
            # 同步对话
            result = await ai_service.chat_completion(chat_params)
            
            # 构建响应
            response_data = {
                "message": {
                    "role": "assistant",
                    "content": result.get("content", ""),
                    "function_call": result.get("function_call")
                },
                "model": result.get("model", request.model),
                "tokens_used": result.get("tokens_used", 0),
                "generation_time": result.get("generation_time", 0),
                "finish_reason": result.get("finish_reason", "stop"),
                "metadata": {
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "total_tokens": result.get("total_tokens", 0)
                }
            }
            
            return ExternalResponseFormatter.format_success(
                data=response_data,
                message="对话补全成功"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API - 对话补全失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="对话补全失败"
        )


@router.post("/summarize", response_model=Dict[str, Any], summary="文本摘要")
async def summarize_text(
    request: SummarizationRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    文本摘要
    
    对长文本进行智能摘要，支持多种摘要风格。
    """
    try:
        logger.info(f"V1 API - 文本摘要: text_length={len(request.text)}, style={request.style}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 构建摘要参数
        summary_params = {
            "text": request.text,
            "model": request.model,
            "max_summary_length": request.max_summary_length,
            "style": request.style,
            "api_mode": "v1_external"
        }
        
        # 执行摘要
        result = await ai_service.summarize_text(summary_params)
        
        # 构建响应
        response_data = {
            "summary": result.get("summary", ""),
            "original_length": len(request.text),
            "summary_length": len(result.get("summary", "")),
            "compression_ratio": result.get("compression_ratio", 0),
            "model": result.get("model", request.model),
            "processing_time": result.get("processing_time", 0),
            "style": request.style,
            "metadata": {
                "tokens_used": result.get("tokens_used", 0),
                "key_points": result.get("key_points", [])
            }
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="文本摘要成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 文本摘要失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="文本摘要失败"
        )


@router.post("/translate", response_model=Dict[str, Any], summary="文本翻译")
async def translate_text(
    request: TranslationRequest,
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    文本翻译
    
    将文本翻译为指定语言。
    """
    try:
        logger.info(f"V1 API - 文本翻译: target_language={request.target_language}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 构建翻译参数
        translation_params = {
            "text": request.text,
            "target_language": request.target_language,
            "source_language": request.source_language,
            "model": request.model,
            "api_mode": "v1_external"
        }
        
        # 执行翻译
        result = await ai_service.translate_text(translation_params)
        
        # 构建响应
        response_data = {
            "translated_text": result.get("translated_text", ""),
            "source_language": result.get("detected_source_language", request.source_language),
            "target_language": request.target_language,
            "confidence": result.get("confidence", 0.0),
            "model": result.get("model", request.model),
            "processing_time": result.get("processing_time", 0),
            "metadata": {
                "tokens_used": result.get("tokens_used", 0),
                "character_count": len(request.text)
            }
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="文本翻译成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 文本翻译失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="文本翻译失败"
        )


@router.post("/continue", response_model=Dict[str, Any], summary="文本续写")
async def continue_text(
    text: str = Field(..., min_length=10, max_length=4000, description="待续写文本"),
    model: Optional[str] = Field(None, description="指定模型"),
    max_tokens: int = Field(default=500, ge=50, le=2000, description="续写最大长度"),
    style: str = Field(default="natural", description="续写风格: natural, creative, formal"),
    container: V1ServiceContainer = Depends(get_v1_service_container),
    context: V1Context = Depends(get_v1_context)
):
    """
    文本续写
    
    基于给定文本进行智能续写。
    """
    try:
        logger.info(f"V1 API - 文本续写: text_length={len(text)}, style={style}")
        
        # 获取AI服务
        ai_service = container.get_ai_service()
        
        # 构建续写参数
        continue_params = {
            "text": text,
            "model": model,
            "max_tokens": max_tokens,
            "style": style,
            "api_mode": "v1_external"
        }
        
        # 执行续写
        result = await ai_service.continue_text(continue_params)
        
        # 构建响应
        response_data = {
            "original_text": text,
            "continued_text": result.get("continued_text", ""),
            "full_text": text + result.get("continued_text", ""),
            "model": result.get("model", model),
            "style": style,
            "processing_time": result.get("processing_time", 0),
            "metadata": {
                "tokens_used": result.get("tokens_used", 0),
                "continuation_length": len(result.get("continued_text", ""))
            }
        }
        
        return ExternalResponseFormatter.format_success(
            data=response_data,
            message="文本续写成功"
        )
        
    except Exception as e:
        logger.error(f"V1 API - 文本续写失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="文本续写失败"
        )


# ================================
# 辅助函数
# ================================

async def _handle_text_stream(ai_service, generation_params):
    """处理流式文本生成"""
    
    async def generate_text_stream():
        try:
            # 发送开始事件
            start_event = {
                "event": "start",
                "data": {
                    "model": generation_params.get("model"),
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
            
            # 处理流式生成
            async for chunk in ai_service.generate_text_stream(generation_params):
                stream_event = {
                    "event": "text",
                    "data": {
                        "text": chunk.get("text", ""),
                        "tokens": chunk.get("tokens", 0),
                        "finish_reason": chunk.get("finish_reason")
                    }
                }
                
                yield f"data: {json.dumps(stream_event, ensure_ascii=False)}\n\n"
            
            # 发送完成事件
            end_event = {
                "event": "done",
                "data": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"流式文本生成异常: {str(e)}", exc_info=True)
            error_event = {
                "event": "error",
                "data": {
                    "error": "流式生成异常",
                    "code": "streaming_error"
                }
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_text_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def _handle_chat_stream(ai_service, chat_params):
    """处理流式对话补全"""
    
    async def generate_chat_stream():
        try:
            # 发送开始事件
            start_event = {
                "event": "start",
                "data": {
                    "model": chat_params.get("model"),
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
            
            # 处理流式对话
            async for chunk in ai_service.chat_completion_stream(chat_params):
                stream_event = {
                    "event": "delta",
                    "data": {
                        "delta": {
                            "role": chunk.get("role", "assistant"),
                            "content": chunk.get("content", ""),
                            "function_call": chunk.get("function_call")
                        },
                        "finish_reason": chunk.get("finish_reason")
                    }
                }
                
                yield f"data: {json.dumps(stream_event, ensure_ascii=False)}\n\n"
            
            # 发送完成事件
            end_event = {
                "event": "done",
                "data": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"流式对话补全异常: {str(e)}", exc_info=True)
            error_event = {
                "event": "error",
                "data": {
                    "error": "流式对话异常",
                    "code": "streaming_error"
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
            "X-Accel-Buffering": "no"
        }
    ) 