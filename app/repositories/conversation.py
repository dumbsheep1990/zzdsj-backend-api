"""
对话仓库模块: 提供对话和消息的数据访问
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.assistant import Conversation, Message
from app.repositories.base import BaseRepository

class ConversationRepository(BaseRepository[Conversation]):
    """对话仓库"""
    
    def __init__(self, db: Session):
        super().__init__(Conversation, db)
    
    def get_with_messages(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话及其所有消息"""
        return self.db.query(Conversation).options(
            joinedload(Conversation.messages)
        ).filter(Conversation.id == conversation_id).first()
    
    def get_by_assistant(self, assistant_id: str, user_id: Optional[str] = None, skip: int = 0, limit: int = 20) -> List[Conversation]:
        """获取助手的所有对话，可按用户过滤"""
        query = self.db.query(Conversation).filter(Conversation.assistant_id == assistant_id)
        
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
            
        return query.order_by(desc(Conversation.last_activity)).offset(skip).limit(limit).all()
    
    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> List[Conversation]:
        """获取用户的所有对话"""
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(desc(Conversation.last_activity)).offset(skip).limit(limit).all()
    
    def update_last_activity(self, conversation_id: str) -> Optional[Conversation]:
        """更新对话最后活动时间"""
        from datetime import datetime
        return self.update(conversation_id, {"last_activity": datetime.now()})


class MessageRepository(BaseRepository[Message]):
    """消息仓库"""
    
    def __init__(self, db: Session):
        super().__init__(Message, db)
    
    def get_by_conversation(self, conversation_id: str, skip: int = 0, limit: int = 100) -> List[Message]:
        """获取对话的所有消息"""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).offset(skip).limit(limit).all()
    
    def get_last_messages(self, conversation_id: str, limit: int = 10) -> List[Message]:
        """获取对话的最近消息"""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
    
    def count_by_conversation(self, conversation_id: str) -> int:
        """计算对话的消息数量"""
        return self.db.query(Message).filter(Message.conversation_id == conversation_id).count()
    
    def create_system_message(self, conversation_id: str, content: str) -> Message:
        """创建系统消息"""
        return self.create({
            "conversation_id": conversation_id,
            "role": "system",
            "content": content
        })
    
    def create_user_message(self, conversation_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """创建用户消息"""
        return self.create({
            "conversation_id": conversation_id,
            "role": "user",
            "content": content,
            "metadata": metadata or {}
        })
    
    def create_assistant_message(self, conversation_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """创建助手消息"""
        return self.create({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": content,
            "metadata": metadata or {}
        })
