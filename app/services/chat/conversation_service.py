"""
对话服务模块: 提供对话和消息相关的业务逻辑处理
已重构为使用核心业务逻辑层，遵循分层架构原则
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

# 导入核心业务逻辑层
from app.core.chat.conversation_manager import ConversationManager

# 导入数据模型（用于兼容性）
from app.models.assistant import Conversation, Message
from app.config import settings

logger = logging.getLogger(__name__)

class ConversationService:
    """对话服务类 - 已重构为使用核心业务逻辑层"""
    
    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db
        
        # 使用核心业务逻辑层
        self.conversation_manager = ConversationManager(db)
    
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
            # 使用核心层创建对话
            result = await self.conversation_manager.create_conversation(
                assistant_id, user_id, title
            )
            
            if not result["success"]:
                if result.get("error_code") == "ASSISTANT_NOT_FOUND":
                    raise ValueError(f"助手不存在: {assistant_id}")
                else:
                    raise ValueError(result["error"])
            
            # 转换为旧的数据模型格式（兼容性）
            conversation_data = result["data"]
            conversation = Conversation(
                id=conversation_data["id"],
                assistant_id=conversation_data["assistant_id"],
                user_id=conversation_data["user_id"],
                title=conversation_data["title"],
                metadata=conversation_data.get("metadata", {}),
                last_activity=conversation_data["last_activity"],
                created_at=conversation_data["created_at"],
                updated_at=conversation_data["updated_at"]
            )
            
            logger.info(f"已创建对话: {conversation.id} (用户: {user_id}, 助手: {assistant_id})")
            return conversation
            
        except Exception as e:
            logger.error(f"创建对话时出错: {str(e)}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        try:
            result = await self.conversation_manager.get_conversation(conversation_id)
            
            if not result["success"]:
                return None
            
            # 转换为旧的数据模型格式（兼容性）
            conversation_data = result["data"]
            conversation = Conversation(
                id=conversation_data["id"],
                assistant_id=conversation_data["assistant_id"],
                user_id=conversation_data["user_id"],
                title=conversation_data["title"],
                metadata=conversation_data.get("metadata", {}),
                last_activity=conversation_data["last_activity"],
                created_at=conversation_data["created_at"],
                updated_at=conversation_data["updated_at"]
            )
            
            return conversation
            
        except Exception as e:
            logger.error(f"获取对话时出错: {str(e)}")
            return None
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话及其所有消息"""
        try:
            result = await self.conversation_manager.get_conversation_with_messages(conversation_id)
            
            if not result["success"]:
                return None
            
            # 转换为旧的数据模型格式（兼容性）
            data = result["data"]
            conversation_data = data["conversation"]
            messages_data = data["messages"]
            
            conversation = Conversation(
                id=conversation_data["id"],
                assistant_id=conversation_data["assistant_id"],
                user_id=conversation_data["user_id"],
                title=conversation_data["title"],
                metadata=conversation_data.get("metadata", {}),
                last_activity=conversation_data["last_activity"],
                created_at=conversation_data["created_at"],
                updated_at=conversation_data["updated_at"]
            )
            
            # 添加消息
            messages = []
            for msg_data in messages_data:
                message = Message(
                    id=msg_data["id"],
                    conversation_id=msg_data["conversation_id"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    metadata=msg_data.get("metadata", {}),
                    created_at=msg_data["created_at"],
                    updated_at=msg_data["updated_at"]
                )
                messages.append(message)
            
            # 设置消息关系
            conversation.messages = messages
            
            return conversation
            
        except Exception as e:
            logger.error(f"获取对话和消息时出错: {str(e)}")
            return None
    
    async def update_conversation(self, conversation_id: str, 
                                data: Dict[str, Any]) -> Optional[Conversation]:
        """更新对话信息"""
        try:
            result = await self.conversation_manager.update_conversation(conversation_id, data)
            
            if not result["success"]:
                return None
            
            # 转换为旧的数据模型格式（兼容性）
            conversation_data = result["data"]
            conversation = Conversation(
                id=conversation_data["id"],
                assistant_id=conversation_data["assistant_id"],
                user_id=conversation_data["user_id"],
                title=conversation_data["title"],
                metadata=conversation_data.get("metadata", {}),
                last_activity=conversation_data["last_activity"],
                created_at=conversation_data["created_at"],
                updated_at=conversation_data["updated_at"]
            )
            
            return conversation
            
        except Exception as e:
            logger.error(f"更新对话时出错: {str(e)}")
            return None
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        try:
            result = await self.conversation_manager.delete_conversation(conversation_id)
            return result["success"]
            
        except Exception as e:
            logger.error(f"删除对话时出错: {str(e)}")
            return False
    
    async def get_user_conversations(self, user_id: str, skip: int = 0, 
                                   limit: int = 20) -> List[Conversation]:
        """获取用户的所有对话"""
        try:
            result = await self.conversation_manager.list_user_conversations(user_id, skip, limit)
            
            if not result["success"]:
                return []
            
            # 转换为旧的数据模型格式（兼容性）
            conversations = []
            for conv_data in result["data"]["conversations"]:
                conversation = Conversation(
                    id=conv_data["id"],
                    assistant_id=conv_data["assistant_id"],
                    user_id=conv_data["user_id"],
                    title=conv_data["title"],
                    metadata=conv_data.get("metadata", {}),
                    last_activity=conv_data["last_activity"],
                    created_at=conv_data["created_at"],
                    updated_at=conv_data["updated_at"]
                )
                conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            logger.error(f"获取用户对话列表时出错: {str(e)}")
            return []
    
    async def get_assistant_conversations(self, assistant_id: str, user_id: Optional[str] = None, 
                                        skip: int = 0, limit: int = 20) -> List[Conversation]:
        """获取助手的所有对话，可按用户过滤"""
        try:
            result = await self.conversation_manager.list_assistant_conversations(
                assistant_id, user_id, skip, limit
            )
            
            if not result["success"]:
                return []
            
            # 转换为旧的数据模型格式（兼容性）
            conversations = []
            for conv_data in result["data"]["conversations"]:
                conversation = Conversation(
                    id=conv_data["id"],
                    assistant_id=conv_data["assistant_id"],
                    user_id=conv_data["user_id"],
                    title=conv_data["title"],
                    metadata=conv_data.get("metadata", {}),
                    last_activity=conv_data["last_activity"],
                    created_at=conv_data["created_at"],
                    updated_at=conv_data["updated_at"]
                )
                conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            logger.error(f"获取助手对话列表时出错: {str(e)}")
            return []
    
    async def add_system_message(self, conversation_id: str, content: str) -> Message:
        """添加系统消息"""
        try:
            result = await self.conversation_manager.add_message(
                conversation_id, "system", content
            )
            
            if not result["success"]:
                if result.get("error_code") == "CONVERSATION_NOT_FOUND":
                    raise ValueError(f"对话不存在: {conversation_id}")
                else:
                    raise ValueError(result["error"])
            
            # 转换为旧的数据模型格式（兼容性）
            message_data = result["data"]
            message = Message(
                id=message_data["id"],
                conversation_id=message_data["conversation_id"],
                role=message_data["role"],
                content=message_data["content"],
                metadata=message_data.get("metadata", {}),
                created_at=message_data["created_at"],
                updated_at=message_data["updated_at"]
            )
            
            return message
            
        except Exception as e:
            logger.error(f"添加系统消息时出错: {str(e)}")
            raise
    
    async def add_user_message(self, conversation_id: str, content: str, 
                             metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加用户消息"""
        try:
            result = await self.conversation_manager.add_message(
                conversation_id, "user", content, metadata
            )
            
            if not result["success"]:
                if result.get("error_code") == "CONVERSATION_NOT_FOUND":
                    raise ValueError(f"对话不存在: {conversation_id}")
                else:
                    raise ValueError(result["error"])
            
            # 转换为旧的数据模型格式（兼容性）
            message_data = result["data"]
            message = Message(
                id=message_data["id"],
                conversation_id=message_data["conversation_id"],
                role=message_data["role"],
                content=message_data["content"],
                metadata=message_data.get("metadata", {}),
                created_at=message_data["created_at"],
                updated_at=message_data["updated_at"]
            )
            
            return message
            
        except Exception as e:
            logger.error(f"添加用户消息时出错: {str(e)}")
            raise
    
    async def add_assistant_message(self, conversation_id: str, content: str, 
                                  metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加助手消息"""
        try:
            result = await self.conversation_manager.add_message(
                conversation_id, "assistant", content, metadata
            )
            
            if not result["success"]:
                if result.get("error_code") == "CONVERSATION_NOT_FOUND":
                    raise ValueError(f"对话不存在: {conversation_id}")
                else:
                    raise ValueError(result["error"])
            
            # 转换为旧的数据模型格式（兼容性）
            message_data = result["data"]
            message = Message(
                id=message_data["id"],
                conversation_id=message_data["conversation_id"],
                role=message_data["role"],
                content=message_data["content"],
                metadata=message_data.get("metadata", {}),
                created_at=message_data["created_at"],
                updated_at=message_data["updated_at"]
            )
            
            return message
            
        except Exception as e:
            logger.error(f"添加助手消息时出错: {str(e)}")
            raise
    
    async def get_messages(self, conversation_id: str, skip: int = 0, 
                         limit: int = 100) -> List[Message]:
        """获取对话的所有消息"""
        try:
            result = await self.conversation_manager.get_messages(conversation_id, skip, limit)
            
            if not result["success"]:
                return []
            
            # 转换为旧的数据模型格式（兼容性）
            messages = []
            for msg_data in result["data"]["messages"]:
                message = Message(
                    id=msg_data["id"],
                    conversation_id=msg_data["conversation_id"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    metadata=msg_data.get("metadata", {}),
                    created_at=msg_data["created_at"],
                    updated_at=msg_data["updated_at"]
                )
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"获取消息列表时出错: {str(e)}")
            return []
    
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
            result = await self.conversation_manager.get_conversation_history(conversation_id, limit)
            
            if not result["success"]:
                if result.get("error_code") == "CONVERSATION_NOT_FOUND":
                    raise ValueError(f"对话不存在: {conversation_id}")
                else:
                    raise ValueError(result["error"])
            
            return result["data"]["history"]
            
        except Exception as e:
            logger.error(f"获取对话历史时出错: {str(e)}")
            raise
    
    async def update_conversation_activity(self, conversation_id: str) -> Optional[Conversation]:
        """更新对话最后活动时间"""
        try:
            result = await self.conversation_manager.update_conversation_activity(conversation_id)
            
            if not result["success"]:
                return None
            
            # 获取更新后的对话
            return await self.get_conversation(conversation_id)
            
        except Exception as e:
            logger.error(f"更新对话活动时间时出错: {str(e)}")
            return None
