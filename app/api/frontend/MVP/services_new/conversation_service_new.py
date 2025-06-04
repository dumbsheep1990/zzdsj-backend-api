"""
对话服务层
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.services.base import BaseService
from app.models.chat import Conversation, Message
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
    ConversationWithMessages
)
from app.core.exceptions import NotFoundError, PermissionError


class ConversationService(BaseService[Conversation]):
    """对话服务"""

    async def create(self, data: ConversationCreate, user_id: int) -> Conversation:
        """创建对话"""
        try:
            # 添加用户ID到元数据
            metadata = data.metadata or {}
            metadata['user_id'] = user_id

            conversation = Conversation(
                assistant_id=data.assistant_id,
                title=data.title,
                metadata=metadata,
                created_at=datetime.utcnow()
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            self.logger.info(f"创建对话成功: id={conversation.id}, user_id={user_id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"创建对话失败: {str(e)}")
            raise

    async def get(self, id: int, user_id: Optional[int] = None) -> Optional[Conversation]:
        """获取对话"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == id
        ).first()

        if not conversation:
            return None

        # 检查用户权限
        if user_id and not self._check_user_permission(conversation, user_id):
            raise PermissionError("无权访问该对话")

        return conversation

    async def update(self, id: int, data: ConversationUpdate, user_id: int) -> Optional[Conversation]:
        """更新对话"""
        conversation = await self.get(id, user_id)
        if not conversation:
            return None

        # 更新字段
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)

        conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    async def delete(self, id: int, user_id: int) -> bool:
        """删除对话"""
        conversation = await self.get(id, user_id)
        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()

        return True

    async def list_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            search: Optional[str] = None,
            skip: int = 0,
            limit: int = 20,
            order_by: str = "updated_at",
            order_desc: bool = True
    ) -> List[Conversation]:
        """获取对话列表"""
        query = self.db.query(Conversation)

        # 用户筛选
        query = query.filter(
            Conversation.metadata.op('->>')('user_id') == str(user_id)
        )

        # 助手筛选
        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)

        # 搜索
        if search:
            query = query.filter(
                Conversation.title.ilike(f"%{search}%")
            )

        # 排序
        order_column = getattr(Conversation, order_by, Conversation.updated_at)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        # 分页
        conversations = query.offset(skip).limit(limit).all()

        return conversations

    async def get_with_messages(
            self,
            id: int,
            user_id: int,
            message_limit: int = 50
    ) -> Optional[ConversationWithMessages]:
        """获取对话及其消息"""
        conversation = await self.get(id, user_id)
        if not conversation:
            return None

        # 获取消息
        messages = self.db.query(Message).filter(
            Message.conversation_id == id
        ).order_by(Message.created_at.desc()).limit(message_limit).all()

        # 反转消息顺序（从旧到新）
        messages.reverse()

        return ConversationWithMessages(
            **conversation.__dict__,
            messages=messages,
            message_count=len(messages)
        )

    def _check_user_permission(self, conversation: Conversation, user_id: int) -> bool:
        """检查用户权限"""
        if not conversation.metadata:
            return True

        conversation_user_id = conversation.metadata.get('user_id')
        return not conversation_user_id or int(conversation_user_id) == user_id