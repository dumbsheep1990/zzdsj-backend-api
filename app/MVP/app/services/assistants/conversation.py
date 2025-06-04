"""
对话服务实现
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.services.assistants.base import BaseService
from app.repositories.assistants.conversation import ConversationRepository, MessageRepository
from app.repositories.assistants.assistant import AssistantRepository
from app.core.assistants.interfaces import IConversationService
from app.core.assistants.exceptions import (
    ConversationNotFoundError,
    AssistantNotFoundError,
    PermissionDeniedError,
    ValidationError
)
from app.core.assistants.validators import ConversationValidator
from app.schemas.assistants.conversation import (
    ConversationCreateRequest,
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse
)


class ConversationService(BaseService, IConversationService):
    """对话服务"""

    def __init__(self, db):
        super().__init__(db)
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.assistant_repo = AssistantRepository(db)
        self.validator = ConversationValidator()

    async def create_conversation(
            self,
            assistant_id: int,
            user_id: int,
            title: Optional[str] = None
    ) -> ConversationResponse:
        """创建对话"""
        # 验证助手存在且用户有权限访问
        assistant = await self.assistant_repo.get_by_id(assistant_id)
        if not assistant or not assistant.is_active:
            raise AssistantNotFoundError(assistant_id)

        if not assistant.is_public and assistant.owner_id != user_id:
            raise PermissionDeniedError("助手")

        # 验证标题
        if title:
            self.validator.validate_title(title)
        else:
            title = f"对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # 创建对话
        conversation = await self.conversation_repo.create(
            assistant_id=assistant_id,
            user_id=user_id,
            title=title,
            metadata={}
        )

        self.logger.info(f"Created conversation {conversation.id} for user {user_id}")

        return ConversationResponse.from_orm(conversation)

    async def send_message(
            self,
            conversation_id: int,
            content: str,
            user_id: int
    ) -> MessageResponse:
        """发送消息"""
        # 验证对话存在且属于用户
        conversation = await self.conversation_repo.get_by_id_and_user(conversation_id, user_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        # 验证消息内容
        self.validator.validate_message_content(content)

        # 创建用户消息
        user_message = await self.message_repo.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
            metadata={}
        )

        # 获取助手信息
        assistant = await self.assistant_repo.get_by_id(conversation.assistant_id)

        # TODO: 调用AI服务生成回复
        ai_response = await self._generate_ai_response(
            assistant=assistant,
            conversation_id=conversation_id,
            user_message=content
        )

        # 创建助手回复消息
        assistant_message = await self.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response,
            metadata={}
        )

        # 更新对话最后活动时间
        await self.conversation_repo.update_last_activity(conversation_id)

        self.logger.info(f"Sent message in conversation {conversation_id}")

        return MessageResponse.from_orm(assistant_message)

    async def get_messages(
            self,
            conversation_id: int,
            user_id: int,
            limit: int = 50
    ) -> List[MessageResponse]:
        """获取消息历史"""
        # 验证对话存在且属于用户
        conversation = await self.conversation_repo.get_by_id_and_user(conversation_id, user_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        # 获取消息
        messages = await self.message_repo.get_latest_messages(conversation_id, limit)

        return [MessageResponse.from_orm(msg) for msg in messages]

    async def get_user_conversations(
            self,
            user_id: int,
            assistant_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 20
    ) -> List[ConversationResponse]:
        """获取用户的对话列表"""
        conversations = await self.conversation_repo.get_user_conversations(
            user_id=user_id,
            assistant_id=assistant_id,
            skip=skip,
            limit=limit
        )

        return [ConversationResponse.from_orm(conv) for conv in conversations]

    async def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话"""
        # 验证对话存在且属于用户
        conversation = await self.conversation_repo.get_by_id_and_user(conversation_id, user_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        # 删除对话（会级联删除消息）
        success = await self.conversation_repo.delete(conversation_id)

        if success:
            self.logger.info(f"Deleted conversation {conversation_id}")

        return success

    async def _generate_ai_response(
            self,
            assistant: Any,
            conversation_id: int,
            user_message: str
    ) -> str:
        """生成AI回复"""
        # TODO: 实现实际的AI调用逻辑
        # 1. 获取对话上下文
        # 2. 调用配置的AI模型
        # 3. 处理知识库查询
        # 4. 返回生成的回复

        return f"这是对 '{user_message}' 的模拟回复"