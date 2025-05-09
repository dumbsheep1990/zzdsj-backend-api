"""
问答助手API路由
提供统一的问答助手管理和交互接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.models.database import get_db
from app.models.assistant_qa import QAAssistant, QAInteraction
from app.schemas.assistant_qa import (
    QAAssistant as QAAssistantSchema,
    QAAssistantCreate,
    QAAssistantUpdate,
    QAInteraction as QAInteractionSchema,
    QARequest,
    QAResponse
)
from app.api.v1.dependencies import (
    get_agent_adapter, ResponseFormatter, get_request_context
)
from app.messaging.adapters.agent import AgentAdapter
from app.messaging.core.models import (
    Message as CoreMessage, MessageRole, TextMessage
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/assistants", response_model=List[QAAssistantSchema])
async def get_qa_assistants(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有问答助手，支持过滤和搜索
    """
    query = db.query(QAAssistant)
    
    if is_active is not None:
        query = query.filter(QAAssistant.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            QAAssistant.name.ilike(search_term) | 
            QAAssistant.description.ilike(search_term)
        )
    
    assistants = query.order_by(QAAssistant.created_at.desc()).offset(skip).limit(limit).all()
    return ResponseFormatter.format_success(assistants)


@router.post("/assistants", response_model=QAAssistantSchema)
async def create_qa_assistant(
    assistant: QAAssistantCreate,
    db: Session = Depends(get_db)
):
    """
    创建新问答助手
    """
    # 创建助手记录
    db_assistant = QAAssistant(
        name=assistant.name,
        description=assistant.description,
        model=assistant.model,
        system_prompt=assistant.system_prompt,
        temperature=assistant.temperature,
        is_active=assistant.is_active,
        knowledge_scope=assistant.knowledge_scope,
        config=assistant.config or {},
        metadata=assistant.metadata or {}
    )
    
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    
    return ResponseFormatter.format_success(db_assistant)


@router.get("/assistants/{assistant_id}", response_model=QAAssistantSchema)
async def get_qa_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取问答助手
    """
    assistant = db.query(QAAssistant).filter(QAAssistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答助手不存在")
    
    return ResponseFormatter.format_success(assistant)


@router.put("/assistants/{assistant_id}", response_model=QAAssistantSchema)
async def update_qa_assistant(
    assistant_id: int,
    assistant_update: QAAssistantUpdate,
    db: Session = Depends(get_db)
):
    """
    更新问答助手
    """
    db_assistant = db.query(QAAssistant).filter(QAAssistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答助手不存在")
    
    # 更新字段
    if assistant_update.name is not None:
        db_assistant.name = assistant_update.name
    
    if assistant_update.description is not None:
        db_assistant.description = assistant_update.description
    
    if assistant_update.model is not None:
        db_assistant.model = assistant_update.model
    
    if assistant_update.system_prompt is not None:
        db_assistant.system_prompt = assistant_update.system_prompt
    
    if assistant_update.temperature is not None:
        db_assistant.temperature = assistant_update.temperature
    
    if assistant_update.is_active is not None:
        db_assistant.is_active = assistant_update.is_active
    
    if assistant_update.knowledge_scope is not None:
        db_assistant.knowledge_scope = assistant_update.knowledge_scope
    
    if assistant_update.config is not None:
        db_assistant.config = assistant_update.config
    
    if assistant_update.metadata is not None:
        # 合并元数据，保留现有字段
        db_assistant.metadata.update(assistant_update.metadata)
    
    db_assistant.updated_at = datetime.now()
    db.commit()
    db.refresh(db_assistant)
    
    return ResponseFormatter.format_success(db_assistant)


@router.delete("/assistants/{assistant_id}")
async def delete_qa_assistant(
    assistant_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除或停用问答助手
    """
    db_assistant = db.query(QAAssistant).filter(QAAssistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答助手不存在")
    
    if permanent:
        # 删除关联的交互记录
        db.query(QAInteraction).filter(QAInteraction.assistant_id == assistant_id).delete()
        
        # 删除助手
        db.delete(db_assistant)
    else:
        # 仅停用助手
        db_assistant.is_active = False
        db_assistant.updated_at = datetime.now()
    
    db.commit()
    
    return ResponseFormatter.format_success(None, message=f"问答助手已{'删除' if permanent else '停用'}")


@router.get("/assistants/{assistant_id}/interactions", response_model=List[QAInteractionSchema])
async def get_qa_interactions(
    assistant_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取问答助手的交互记录
    """
    # 检查助手是否存在
    assistant = db.query(QAAssistant).filter(QAAssistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答助手不存在")
    
    # 获取交互记录
    interactions = db.query(QAInteraction).filter(
        QAInteraction.assistant_id == assistant_id
    ).order_by(QAInteraction.created_at.desc()).offset(skip).limit(limit).all()
    
    return ResponseFormatter.format_success(interactions)


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    qa_request: QARequest,
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    向问答助手提问并获取回答
    """
    # 检查助手是否存在
    assistant = db.query(QAAssistant).filter(QAAssistant.id == qa_request.assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问答助手不存在")
    
    # 创建问题消息
    question_message = TextMessage(
        content=qa_request.question,
        role=MessageRole.USER
    )
    
    # 创建交互记录
    interaction = QAInteraction(
        assistant_id=assistant.id,
        question=qa_request.question,
        user_id=qa_request.user_id,
        metadata=qa_request.metadata or {}
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    
    # 使用统一消息系统处理请求
    try:
        # 选择适当的回复格式
        if qa_request.stream:
            # 异步处理返回SSE流
            return await agent_adapter.to_sse_response(
                messages=[question_message],
                model_name=assistant.model,
                temperature=assistant.temperature,
                system_prompt=assistant.system_prompt,
                memory_key=f"qa_assistant_{assistant.id}"
            )
        else:
            # 同步处理返回JSON
            response_messages = await agent_adapter.process_messages(
                messages=[question_message],
                model_name=assistant.model,
                temperature=assistant.temperature,
                system_prompt=assistant.system_prompt,
                memory_key=f"qa_assistant_{assistant.id}"
            )
            
            # 获取助手回复
            answer = ""
            for msg in response_messages:
                if msg.role == MessageRole.ASSISTANT:
                    answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break
            
            # 更新交互记录
            interaction.answer = answer
            interaction.status = "completed"
            interaction.completed_at = datetime.now()
            db.commit()
            
            # 使用OpenAI兼容格式返回结果
            return ResponseFormatter.format_openai_compatible(response_messages)
    except Exception as e:
        logger.error(f"问答处理错误: {str(e)}")
        
        # 更新交互记录状态
        interaction.status = "error"
        interaction.metadata["error"] = str(e)
        db.commit()
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"问答处理出错: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(
    qa_request: QARequest,
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    流式问答接口，返回SSE格式的响应流
    """
    # 确保请求使用流模式
    qa_request.stream = True
    return await ask_question(qa_request, agent_adapter, background_tasks, db)
