"""
依赖注入模块: 提供FastAPI依赖项，用于获取数据库会话和服务实例
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
# 导入统一知识库服务
from app.services.unified_knowledge_service import UnifiedKnowledgeService, get_unified_knowledge_service
from app.services.assistant import AssistantService
from app.services.conversation import ConversationService

# 数据库会话依赖
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话依赖"""
    return get_db()

# 服务层依赖
def get_knowledge_service(db: Session = Depends(get_db_session)) -> UnifiedKnowledgeService:
    """获取统一知识库服务依赖"""
    return get_unified_knowledge_service(db)

def get_assistant_service(db: Session = Depends(get_db_session)) -> AssistantService:
    """获取助手服务依赖"""
    return AssistantService(db)

def get_conversation_service(db: Session = Depends(get_db_session)) -> ConversationService:
    """获取对话服务依赖"""
    return ConversationService(db)

# 实体验证依赖
async def validate_knowledge_base(
    kb_id: str,
    knowledge_service: UnifiedKnowledgeService = Depends(get_knowledge_service)
) -> dict:
    """验证知识库存在"""
    kb = await knowledge_service.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库不存在: {kb_id}"
        )
    return kb

async def validate_assistant(
    assistant_id: str,
    assistant_service: AssistantService = Depends(get_assistant_service)
) -> dict:
    """验证助手存在"""
    assistant = await assistant_service.get_assistant(assistant_id)
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"助手不存在: {assistant_id}"
        )
    return assistant

async def validate_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
) -> dict:
    """验证对话存在"""
    conversation = await conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"对话不存在: {conversation_id}"
        )
    return conversation
