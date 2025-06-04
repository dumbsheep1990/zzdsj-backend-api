"""
对话仓储实现
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import and_, desc
from app.repositories.assistants.base import BaseRepository
from app.models.assistants.conversation import Conversation, Message


class ConversationRepository(BaseRepository[Conversation]):
    """对话仓储"""

    def __init__(self, db):
        super().__init__(db, Conversation)

    async def get_user_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Conversation]:
        """获取用户的对话列表"""
        query = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        )

        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)

        return query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit).all()

    async def get_by_id_and_user(self, id: int, user_id: int) -> Optional[Conversation]:
        """获取用户的指定对话"""
        return self.db.query(Conversation).filter(
            Conversation.id == id,
            Conversation.user_id == user_id
        ).first()

    async def update_last_activity(self, id: int) -> None:
        """更新最后活动时间"""
        await self.update(id, updated_at=datetime.utcnow())


class MessageRepository(BaseRepository[Message]):
    """消息仓储"""

    def __init__(self, db):
        super().__init__(db, Message)

    async def get_conversation_messages(
            self,
            conversation_id: int,
            skip: int = 0,
            limit: int = 50
    ) -> List[Message]:
        """获取对话的消息列表"""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).offset(skip).limit(limit).all()

    async def get_latest_messages(
            self,
            conversation_id: int,
            limit: int = 10
    ) -> List[Message]:
        """获取最新的消息"""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit).all()

        # 反转顺序，使其按时间正序
        messages.reverse()
        return messages

    async def count_conversation_messages(self, conversation_id: int) -> int:
        """统计对话消息数"""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).count()