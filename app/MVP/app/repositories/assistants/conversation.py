"""
对话仓储实现
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncBaseRepository
from app.models.assistants.conversation import Conversation, Message


class AsyncConversationRepository(AsyncBaseRepository[Conversation]):
    """异步对话仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Conversation)

    async def get_user_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Conversation]:
        """获取用户的对话列表"""
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        
        if assistant_id:
            stmt = stmt.where(Conversation.assistant_id == assistant_id)
        
        stmt = stmt.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id_and_user(self, id: int, user_id: int) -> Optional[Conversation]:
        """获取用户的指定对话"""
        stmt = select(Conversation).where(
            and_(
                Conversation.id == id,
                Conversation.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_activity(self, id: int) -> None:
        """更新最后活动时间"""
        await self.update(id, updated_at=datetime.now(UTC))


class AsyncMessageRepository(AsyncBaseRepository[Message]):
    """异步消息仓储"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Message)

    async def get_conversation_messages(
            self,
            conversation_id: int,
            skip: int = 0,
            limit: int = 50
    ) -> List[Message]:
        """获取对话的消息列表"""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_latest_messages(
            self,
            conversation_id: int,
            limit: int = 10
    ) -> List[Message]:
        """获取最新的消息"""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit)
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        # 反转顺序，使其按时间正序
        return list(reversed(messages))

    async def count_conversation_messages(self, conversation_id: int) -> int:
        """统计对话消息数"""
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        result = await self.db.execute(stmt)
        return result.scalar()