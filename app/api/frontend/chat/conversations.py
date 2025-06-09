"""
Frontend API - 对话管理接口
基于原有chat.py完整迁移，适配前端应用需求
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
from datetime import datetime
import io

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory
from app.schemas.chat import (
    Conversation as ConversationSchema,
    ConversationCreate,
    ConversationUpdate,
    ConversationWithMessages,
    Message as MessageSchema,
    MessageCreate,
    ChatRequest,
    ChatResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 请求/响应模型（扩展原有模型）
# ================================

from pydantic import BaseModel, Field

class FrontendChatRequest(BaseModel):
    """前端聊天请求模型"""
    assistant_id: int = Field(..., description="助手ID")
    conversation_id: Optional[int] = Field(None, description="对话ID，为空则创建新对话")
    message: str = Field(..., min_length=1, description="用户消息")
    stream: bool = Field(default=False, description="是否流式响应")
    include_context: bool = Field(default=True, description="是否包含上下文")
    max_tokens: Optional[int] = Field(None, description="最大生成tokens")


class FrontendConversationCreate(BaseModel):
    """前端对话创建请求"""
    assistant_id: int = Field(..., description="助手ID")
    title: Optional[str] = Field(None, max_length=255, description="对话标题")
    initial_message: Optional[str] = Field(None, description="初始消息")


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    conversations: List[Dict[str, Any]]
    total: int
    has_more: bool
    assistant_info: Optional[Dict[str, Any]] = None


# ================================
# 对话管理接口
# ================================

@router.get("/conversations", response_model=Dict[str, Any], summary="获取对话列表")
async def get_conversations(
    assistant_id: Optional[int] = Query(None, description="助手ID筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的对话列表
    
    支持按助手筛选、搜索、分页功能
    """
    try:
        logger.info(f"Frontend API - 获取对话列表: user_id={context.user.id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 获取对话列表（扩展原有功能）
        conversations = await chat_service.get_conversations(
            assistant_id=assistant_id,
            user_id=context.user.id,  # 添加用户筛选
            skip=offset,
            limit=limit
        )
        
        # 如果有搜索关键词，进行过滤
        if search:
            conversations = [
                conv for conv in conversations
                if search.lower() in conv.title.lower()
            ]
        
        # 获取助手信息（如果指定了助手ID）
        assistant_info = None
        if assistant_id:
            assistant_service = container.get_assistant_service()
            assistant = await assistant_service.get_assistant_by_id(assistant_id)
            if assistant:
                assistant_info = {
                    "id": assistant.id,
                    "name": assistant.name,
                    "description": assistant.description,
                    "model": assistant.model
                }
        
        # 构建响应数据
        response_data = {
            "conversations": [
                {
                    "id": conv.id,
                    "assistant_id": conv.assistant_id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                    "message_count": getattr(conv, 'message_count', 0),
                    "last_message_at": getattr(conv, 'last_message_at', None),
                    "metadata": getattr(conv, 'metadata', {})
                }
                for conv in conversations
            ],
            "total": len(conversations),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(conversations),
            "assistant_info": assistant_info
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取对话列表成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取对话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取对话列表失败"
        )


@router.post("/conversations", response_model=Dict[str, Any], summary="创建对话")
async def create_conversation(
    request: FrontendConversationCreate,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建新对话
    
    支持指定助手、标题和初始消息
    """
    try:
        logger.info(f"Frontend API - 创建对话: user_id={context.user.id}, assistant_id={request.assistant_id}")
        
        # 验证助手是否存在
        assistant_service = container.get_assistant_service()
        assistant = await assistant_service.get_assistant_by_id(request.assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="指定的助手不存在"
            )
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 构建对话创建数据
        conversation_data = ConversationCreate(
            assistant_id=request.assistant_id,
            title=request.title or f"与 {assistant.name} 的对话",
            metadata={
                "user_id": context.user.id,
                "created_via": "frontend_api",
                "initial_message": request.initial_message
            }
        )
        
        # 创建对话
        conversation = await chat_service.create_conversation(conversation_data)
        
        # 如果有初始消息，添加到对话中
        if request.initial_message:
            try:
                # 创建初始消息
                initial_message_data = {
                    "conversation_id": conversation.id,
                    "role": "user",
                    "content": request.initial_message,
                    "metadata": {
                        "is_initial": True,
                        "created_by": context.user.id
                    }
                }
                
                # 保存初始消息到数据库
                await chat_service.add_message(initial_message_data)
                
                logger.info(f"已添加初始消息到对话 {conversation.id}")
            except Exception as e:
                logger.warning(f"添加初始消息失败: {str(e)}")
                # 初始消息失败不影响对话创建
        
        # 构建响应数据
        response_data = {
            "id": conversation.id,
            "assistant_id": conversation.assistant_id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "metadata": conversation.metadata,
            "assistant": {
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="对话创建成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 创建对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="对话创建失败"
        )


@router.get("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="获取对话详情")
async def get_conversation(
    conversation_id: int = Path(..., description="对话ID"),
    include_messages: bool = Query(True, description="是否包含消息"),
    message_limit: int = Query(50, ge=1, le=200, description="消息数量限制"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取对话详情及消息
    
    返回对话信息和消息列表
    """
    try:
        logger.info(f"Frontend API - 获取对话详情: user_id={context.user.id}, conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 获取对话（原有功能）
        conversation = await chat_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="对话不存在"
            )
        
        # 验证用户权限（新增用户权限检查）
        if hasattr(conversation, 'metadata') and conversation.metadata:
            conversation_user_id = conversation.metadata.get('user_id')
            if conversation_user_id and conversation_user_id != context.user.id:
                raise HTTPException(
                    status_code=403,
                    detail="无权访问该对话"
                )
        
        # 获取助手信息
        assistant_service = container.get_assistant_service()
        assistant = await assistant_service.get_assistant_by_id(conversation.assistant_id)
        
        # 构建响应数据
        response_data = {
            "id": conversation.id,
            "assistant_id": conversation.assistant_id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "metadata": conversation.metadata,
            "assistant": {
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "model": assistant.model
            } if assistant else None
        }
        
        # 添加消息列表（如果需要）
        if include_messages and hasattr(conversation, 'messages'):
            messages = conversation.messages[-message_limit:] if conversation.messages else []
            response_data["messages"] = [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "metadata": getattr(msg, 'metadata', {})
                }
                for msg in messages
            ]
            response_data["message_count"] = len(conversation.messages) if conversation.messages else 0
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取对话详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 获取对话详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取对话详情失败"
        )


@router.put("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="更新对话")
async def update_conversation(
    conversation_id: int = Path(..., description="对话ID"),
    request: ConversationUpdate = None,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    更新对话信息
    
    允许更新标题等信息
    """
    try:
        logger.info(f"Frontend API - 更新对话: user_id={context.user.id}, conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 验证对话是否存在和权限
        conversation = await chat_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="对话不存在"
            )
        
        # 验证用户权限
        if hasattr(conversation, 'metadata') and conversation.metadata:
            conversation_user_id = conversation.metadata.get('user_id')
            if conversation_user_id and conversation_user_id != context.user.id:
                raise HTTPException(
                    status_code=403,
                    detail="无权修改该对话"
                )
        
        # 更新对话（原有功能）
        updated_conversation = await chat_service.update_conversation(conversation_id, request)
        if not updated_conversation:
            raise HTTPException(
                status_code=500,
                detail="对话更新失败"
            )
        
        # 构建响应数据
        response_data = {
            "id": updated_conversation.id,
            "assistant_id": updated_conversation.assistant_id,
            "title": updated_conversation.title,
            "updated_at": updated_conversation.updated_at.isoformat() if updated_conversation.updated_at else None,
            "metadata": updated_conversation.metadata
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="对话更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 更新对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="对话更新失败"
        )


@router.delete("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="删除对话")
async def delete_conversation(
    conversation_id: int = Path(..., description="对话ID"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    删除对话
    
    永久删除对话及其所有消息
    """
    try:
        logger.info(f"Frontend API - 删除对话: user_id={context.user.id}, conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 验证对话是否存在和权限
        conversation = await chat_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="对话不存在"
            )
        
        # 验证用户权限
        if hasattr(conversation, 'metadata') and conversation.metadata:
            conversation_user_id = conversation.metadata.get('user_id')
            if conversation_user_id and conversation_user_id != context.user.id:
                raise HTTPException(
                    status_code=403,
                    detail="无权删除该对话"
                )
        
        # 删除对话（原有功能）
        success = await chat_service.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="对话删除失败"
            )
        
        return InternalResponseFormatter.format_success(
            data={"conversation_id": conversation_id},
            message="对话删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 删除对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="对话删除失败"
        )


# ================================
# 聊天功能接口
# ================================

@router.post("/chat", response_model=Dict[str, Any], summary="发送聊天消息")
async def chat(
    request: FrontendChatRequest,
    background_tasks: BackgroundTasks,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    发送消息并获取AI响应
    
    支持流式和非流式响应
    """
    try:
        logger.info(f"Frontend API - 发送聊天消息: user_id={context.user.id}, assistant_id={request.assistant_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 验证助手是否存在
        assistant_service = container.get_assistant_service()
        assistant = await assistant_service.get_assistant_by_id(request.assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="指定的助手不存在"
            )
        
        # 如果没有指定对话ID，创建新对话
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_data = ConversationCreate(
                assistant_id=request.assistant_id,
                title=f"与 {assistant.name} 的对话",
                metadata={"user_id": context.user.id}
            )
            conversation = await chat_service.create_conversation(conversation_data)
            conversation_id = conversation.id
        
        # 构建聊天请求（使用原有模型）
        chat_request = ChatRequest(
            assistant_id=request.assistant_id,
            conversation_id=conversation_id,
            message=request.message,
            user_id=context.user.id,  # 添加用户ID
            stream=request.stream,
            metadata={
                "include_context": request.include_context,
                "max_tokens": request.max_tokens,
                "frontend_api": True
            }
        )
        
        # 处理聊天（原有功能）
        response = await chat_service.process_chat(chat_request, background_tasks)
        
        # 构建响应数据
        response_data = {
            "conversation_id": conversation_id,
            "message": response.message,
            "response": response.response,
            "assistant_id": request.assistant_id,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "tokens_used": getattr(response, 'tokens_used', 0),
                "processing_time": getattr(response, 'processing_time', 0),
                "model": assistant.model
            }
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="消息发送成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 发送聊天消息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="消息发送失败"
        )


# ================================
# 语音聊天功能接口（基于原有voice功能迁移）
# ================================

@router.post("/chat/voice", response_model=Dict[str, Any], summary="语音聊天")
async def chat_with_voice(
    assistant_id: int = Form(..., description="助手ID"),
    conversation_id: Optional[int] = Form(None, description="对话ID"),
    message: Optional[str] = Form(None, description="文本消息"),
    audio_file: Optional[UploadFile] = File(None, description="语音文件"),
    enable_voice_input: bool = Form(True, description="启用语音输入"),
    enable_voice_output: bool = Form(True, description="启用语音输出"),
    voice: Optional[str] = Form(None, description="语音声音"),
    speed: Optional[float] = Form(None, description="语音速度"),
    transcribe_only: bool = Form(False, description="仅转录模式"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    语音聊天接口
    
    支持语音输入、语音输出和纯转录模式
    """
    try:
        logger.info(f"Frontend API - 语音聊天: user_id={context.user.id}, assistant_id={assistant_id}")
        
        # 验证参数
        if not audio_file and not message:
            raise HTTPException(
                status_code=400,
                detail="必须提供语音文件或文本消息"
            )
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 验证助手是否存在
        assistant_service = container.get_assistant_service()
        assistant = await assistant_service.get_assistant_by_id(assistant_id)
        if not assistant:
            raise HTTPException(
                status_code=404,
                detail="指定的助手不存在"
            )
        
        # 获取语音管理器（需要从依赖注入获取）
        try:
            from core.voice.voice_manager import VoiceAgentManager
            voice_manager = VoiceAgentManager()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="语音服务暂不可用"
            )
        
        # 处理语音聊天（基于原有功能）
        result = await chat_service.process_voice_chat(
            assistant_id=assistant_id,
            conversation_id=conversation_id,
            user_id=context.user.id,  # 添加用户ID
            message=message,
            audio_file=audio_file,
            enable_voice_input=enable_voice_input,
            enable_voice_output=enable_voice_output,
            voice=voice,
            speed=speed,
            transcribe_only=transcribe_only,
            background_tasks=background_tasks,
            voice_manager=voice_manager
        )
        
        return InternalResponseFormatter.format_success(
            data=result,
            message="语音聊天处理成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 语音聊天失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="语音聊天处理失败"
        )


@router.post("/voice/speech", response_class=StreamingResponse, summary="文本转语音")
async def text_to_speech(
    text: str = Form(..., description="要转换的文本"),
    voice: Optional[str] = Form(None, description="语音声音"),
    speed: Optional[float] = Form(None, description="语音速度"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    文本转语音
    
    将文本转换为语音并返回音频流
    """
    try:
        logger.info(f"Frontend API - 文本转语音: user_id={context.user.id}")
        
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="文本不能为空"
            )
        
        # 获取语音管理器
        try:
            from core.voice.voice_manager import VoiceAgentManager
            voice_manager = VoiceAgentManager()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="语音服务暂不可用"
            )
        
        # 设置语音参数
        voice_params = {
            "enable_voice_output": True,
            "voice": voice,
            "speed": speed,
        }
        
        # 生成语音（基于原有功能）
        audio_data = await voice_manager.process_voice_output(text, voice_params)
        
        if not audio_data:
            raise HTTPException(
                status_code=500,
                detail="语音合成失败"
            )
        
        # 返回音频流
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mp3",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3",
                "Content-Length": str(len(audio_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 文本转语音失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="语音合成失败"
        )


# ================================
# 对话历史和管理功能
# ================================

@router.get("/conversations/{conversation_id}/messages", response_model=Dict[str, Any], summary="获取对话消息")
async def get_conversation_messages(
    conversation_id: int = Path(..., description="对话ID"),
    limit: int = Query(50, ge=1, le=200, description="消息数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    order: str = Query("asc", regex="^(asc|desc)$", description="排序方式"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取对话的消息列表
    
    支持分页和排序
    """
    try:
        logger.info(f"Frontend API - 获取对话消息: user_id={context.user.id}, conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 验证对话是否存在和权限
        conversation = await chat_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="对话不存在"
            )
        
        # 验证用户权限
        if hasattr(conversation, 'metadata') and conversation.metadata:
            conversation_user_id = conversation.metadata.get('user_id')
            if conversation_user_id and conversation_user_id != context.user.id:
                raise HTTPException(
                    status_code=403,
                    detail="无权访问该对话"
                )
        
        # 获取消息列表（这里需要扩展原有服务）
        # 暂时使用对话中的消息
        messages = []
        if hasattr(conversation, 'messages') and conversation.messages:
            all_messages = conversation.messages
            
            # 排序
            if order == "desc":
                all_messages = sorted(all_messages, key=lambda x: x.created_at, reverse=True)
            else:
                all_messages = sorted(all_messages, key=lambda x: x.created_at)
            
            # 分页
            start = offset
            end = offset + limit
            messages = all_messages[start:end]
        
        # 构建响应数据
        response_data = {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "metadata": getattr(msg, 'metadata', {}),
                    "tokens": getattr(msg, 'tokens', 0)
                }
                for msg in messages
            ],
            "total": len(conversation.messages) if hasattr(conversation, 'messages') and conversation.messages else 0,
            "limit": limit,
            "offset": offset,
            "order": order
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取消息列表成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 获取对话消息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取消息列表失败"
        )


@router.post("/conversations/{conversation_id}/export", response_model=Dict[str, Any], summary="导出对话")
async def export_conversation(
    conversation_id: int = Path(..., description="对话ID"),
    format: str = Query("json", regex="^(json|markdown|txt)$", description="导出格式"),
    include_metadata: bool = Query(False, description="包含元数据"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    导出对话数据
    
    支持多种格式导出
    """
    try:
        logger.info(f"Frontend API - 导出对话: user_id={context.user.id}, conversation_id={conversation_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 验证对话是否存在和权限
        conversation = await chat_service.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="对话不存在"
            )
        
        # 验证用户权限
        if hasattr(conversation, 'metadata') and conversation.metadata:
            conversation_user_id = conversation.metadata.get('user_id')
            if conversation_user_id and conversation_user_id != context.user.id:
                raise HTTPException(
                    status_code=403,
                    detail="无权导出该对话"
                )
        
        # 构建导出数据
        export_data = {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None
            },
            "messages": []
        }
        
        if hasattr(conversation, 'messages') and conversation.messages:
            for msg in conversation.messages:
                message_data = {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                
                if include_metadata:
                    message_data["metadata"] = getattr(msg, 'metadata', {})
                    message_data["tokens"] = getattr(msg, 'tokens', 0)
                
                export_data["messages"].append(message_data)
        
        # 根据格式处理数据
        if format == "json":
            export_content = export_data
        elif format == "markdown":
            # 转换为Markdown格式
            md_content = f"# {export_data['conversation']['title']}\n\n"
            md_content += f"**创建时间**: {export_data['conversation']['created_at']}\n\n"
            
            for msg in export_data["messages"]:
                role_name = "用户" if msg["role"] == "user" else "助手"
                md_content += f"## {role_name}\n\n"
                md_content += f"{msg['content']}\n\n"
                if include_metadata and msg.get("created_at"):
                    md_content += f"*时间: {msg['created_at']}*\n\n"
            
            export_content = {"content": md_content, "format": "markdown"}
        else:  # txt
            # 转换为纯文本格式
            txt_content = f"{export_data['conversation']['title']}\n"
            txt_content += f"创建时间: {export_data['conversation']['created_at']}\n"
            txt_content += "="*50 + "\n\n"
            
            for msg in export_data["messages"]:
                role_name = "用户" if msg["role"] == "user" else "助手"
                txt_content += f"[{role_name}]\n"
                txt_content += f"{msg['content']}\n"
                if include_metadata and msg.get("created_at"):
                    txt_content += f"时间: {msg['created_at']}\n"
                txt_content += "\n" + "-"*30 + "\n\n"
            
            export_content = {"content": txt_content, "format": "text"}
        
        return InternalResponseFormatter.format_success(
            data=export_content,
            message="对话导出成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frontend API - 导出对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="对话导出失败"
        ) 