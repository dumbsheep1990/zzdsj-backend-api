"""
对话服务模块: 提供对话和消息相关的业务逻辑处理
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.assistant import AssistantRepository
from app.models.assistant import Conversation, Message
from app.config import settings

logger = logging.getLogger(__name__)

class ConversationService:
    """对话服务类"""
    
    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.assistant_repo = AssistantRepository(db)
    
    async def create_conversation(self, assistant_id: str, user_id: str, 
                                title: Optional[str] = None) -> Conversation:
        """
        创建新对话
        
        参数:
            assistant_id: 助手ID
            user_id: 用户ID
            title: 对话标题
            
        返回:
            新建的对话
        """
        try:
            # 验证助手是否存在
            assistant = self.assistant_repo.get_by_id(assistant_id)
            if not assistant:
                raise ValueError(f"助手不存在: {assistant_id}")
            
            # 准备对话数据
            now = datetime.now()
            conversation_data = {
                "id": str(uuid.uuid4()),
                "assistant_id": assistant_id,
                "user_id": user_id,
                "title": title or f"与 {assistant.name} 的对话",
                "last_activity": now,
                "created_at": now,
                "updated_at": now
            }
            
            # 创建对话
            conversation = self.conversation_repo.create(conversation_data)
            logger.info(f"已创建对话: {conversation.id} (用户: {user_id}, 助手: {assistant_id})")
            
            # 添加系统消息（如果助手有系统提示）
            if assistant.settings and "system_prompt" in assistant.settings:
                await self.add_system_message(conversation.id, assistant.settings["system_prompt"])
            
            return conversation
            
        except Exception as e:
            logger.error(f"创建对话时出错: {str(e)}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        return self.conversation_repo.get_by_id(conversation_id)
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话及其所有消息"""
        return self.conversation_repo.get_with_messages(conversation_id)
    
    async def update_conversation(self, conversation_id: str, 
                                data: Dict[str, Any]) -> Optional[Conversation]:
        """更新对话信息"""
        return self.conversation_repo.update(conversation_id, data)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        return self.conversation_repo.delete(conversation_id)
    
    async def get_user_conversations(self, user_id: str, skip: int = 0, 
                                   limit: int = 20) -> List[Conversation]:
        """获取用户的所有对话"""
        return self.conversation_repo.get_by_user(user_id, skip=skip, limit=limit)
    
    async def get_assistant_conversations(self, assistant_id: str, user_id: Optional[str] = None, 
                                        skip: int = 0, limit: int = 20) -> List[Conversation]:
        """获取助手的所有对话，可按用户过滤"""
        return self.conversation_repo.get_by_assistant(assistant_id, user_id=user_id, skip=skip, limit=limit)
    
    async def add_system_message(self, conversation_id: str, content: str) -> Message:
        """添加系统消息"""
        try:
            # 验证对话是否存在
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"对话不存在: {conversation_id}")
            
            # 创建系统消息
            message = self.message_repo.create_system_message(conversation_id, content)
            
            # 更新对话最后活动时间
            await self.update_conversation_activity(conversation_id)
            
            return message
            
        except Exception as e:
            logger.error(f"添加系统消息时出错: {str(e)}")
            raise
    
    async def add_user_message(self, conversation_id: str, content: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加用户消息"""
        try:
            # 验证对话是否存在
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"对话不存在: {conversation_id}")
            
            # 创建用户消息
            message = self.message_repo.create_user_message(conversation_id, content, metadata)
            
            # 更新对话最后活动时间
            await self.update_conversation_activity(conversation_id)
            
            return message
            
        except Exception as e:
            logger.error(f"添加用户消息时出错: {str(e)}")
            raise
    
    async def add_assistant_message(self, conversation_id: str, content: str, 
                                  metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加助手消息"""
        try:
            # 验证对话是否存在
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"对话不存在: {conversation_id}")
            
            # 创建助手消息
            message = self.message_repo.create_assistant_message(conversation_id, content, metadata)
            
            # 更新对话最后活动时间
            await self.update_conversation_activity(conversation_id)
            
            return message
            
        except Exception as e:
            logger.error(f"添加助手消息时出错: {str(e)}")
            raise
    
    async def get_messages(self, conversation_id: str, skip: int = 0, 
                         limit: int = 100) -> List[Message]:
        """获取对话的所有消息"""
        return self.message_repo.get_by_conversation(conversation_id, skip=skip, limit=limit)
    
    async def get_conversation_history(self, conversation_id: str, 
                                     limit: int = None) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        参数:
            conversation_id: 对话ID
            limit: 最大消息数量（None表示无限制）
            
        返回:
            对话历史列表，格式为 [{"role": "user"/"assistant"/"system", "content": "..."}]
        """
        try:
            # 获取消息
            if limit:
                messages = self.message_repo.get_by_conversation(conversation_id, limit=limit)
            else:
                messages = self.message_repo.get_by_conversation(conversation_id)
            
            # 格式化为对话历史
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取对话历史时出错: {str(e)}")
            raise
    
    async def update_conversation_activity(self, conversation_id: str) -> Optional[Conversation]:
        """更新对话最后活动时间"""
        return self.conversation_repo.update_last_activity(conversation_id)
