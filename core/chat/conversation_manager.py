"""
对话管理器
处理对话和消息的核心业务逻辑
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime

from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.assistant import AssistantRepository

logger = logging.getLogger(__name__)


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, db: Session):
        """初始化对话管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.conversation_repository = ConversationRepository(db)
        self.message_repository = MessageRepository(db)
        self.assistant_repository = AssistantRepository(db)
    
    async def create_conversation(self, 
                                 assistant_id: str, 
                                 user_id: str, 
                                 title: Optional[str] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建新对话
        
        Args:
            assistant_id: 助手ID
            user_id: 用户ID
            title: 对话标题
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证助手是否存在
            assistant = self.assistant_repository.get_by_id(assistant_id)
            if not assistant:
                return {
                    "success": False,
                    "error": f"助手不存在: {assistant_id}",
                    "error_code": "ASSISTANT_NOT_FOUND"
                }
            
            # 准备对话数据
            now = datetime.now()
            conversation_data = {
                "id": str(uuid.uuid4()),
                "assistant_id": assistant_id,
                "user_id": user_id,
                "title": title or f"与 {assistant.name} 的对话",
                "metadata": metadata or {},
                "last_activity": now,
                "created_at": now,
                "updated_at": now
            }
            
            # 创建对话
            conversation = self.conversation_repository.create(conversation_data)
            
            # 添加系统消息（如果助手有系统提示）
            if assistant.settings and "system_prompt" in assistant.settings:
                system_message_result = await self.add_message(
                    conversation.id,
                    "system",
                    assistant.settings["system_prompt"]
                )
                if not system_message_result["success"]:
                    logger.warning(f"添加系统消息失败: {system_message_result['error']}")
            
            logger.info(f"已创建对话: {conversation.id} (用户: {user_id}, 助手: {assistant_id})")
            
            return {
                "success": True,
                "data": {
                    "id": conversation.id,
                    "assistant_id": conversation.assistant_id,
                    "user_id": conversation.user_id,
                    "title": conversation.title,
                    "metadata": conversation.metadata,
                    "last_activity": conversation.last_activity,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"创建对话时出错: {str(e)}")
            return {
                "success": False,
                "error": f"创建对话失败: {str(e)}",
                "error_code": "CONVERSATION_CREATION_FAILED"
            }
    
    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            conversation = self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            return {
                "success": True,
                "data": {
                    "id": conversation.id,
                    "assistant_id": conversation.assistant_id,
                    "user_id": conversation.user_id,
                    "title": conversation.title,
                    "metadata": conversation.metadata,
                    "last_activity": conversation.last_activity,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"获取对话时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取对话失败: {str(e)}",
                "error_code": "GET_CONVERSATION_FAILED"
            }
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话及其所有消息
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            conversation = self.conversation_repository.get_with_messages(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            # 格式化消息
            messages = []
            if hasattr(conversation, 'messages') and conversation.messages:
                for msg in conversation.messages:
                    messages.append({
                        "id": msg.id,
                        "conversation_id": msg.conversation_id,
                        "role": msg.role,
                        "content": msg.content,
                        "metadata": msg.metadata,
                        "created_at": msg.created_at,
                        "updated_at": msg.updated_at
                    })
            
            return {
                "success": True,
                "data": {
                    "conversation": {
                        "id": conversation.id,
                        "assistant_id": conversation.assistant_id,
                        "user_id": conversation.user_id,
                        "title": conversation.title,
                        "metadata": conversation.metadata,
                        "last_activity": conversation.last_activity,
                        "created_at": conversation.created_at,
                        "updated_at": conversation.updated_at
                    },
                    "messages": messages
                }
            }
            
        except Exception as e:
            logger.error(f"获取对话和消息时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取对话和消息失败: {str(e)}",
                "error_code": "GET_CONVERSATION_WITH_MESSAGES_FAILED"
            }
    
    async def update_conversation(self, 
                                 conversation_id: str, 
                                 update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新对话信息
        
        Args:
            conversation_id: 对话ID
            update_data: 更新数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查对话是否存在
            conversation = self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            # 添加更新时间
            update_data["updated_at"] = datetime.now()
            
            # 更新对话
            updated_conversation = self.conversation_repository.update(conversation_id, update_data)
            if not updated_conversation:
                return {
                    "success": False,
                    "error": "更新对话失败",
                    "error_code": "CONVERSATION_UPDATE_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "id": updated_conversation.id,
                    "assistant_id": updated_conversation.assistant_id,
                    "user_id": updated_conversation.user_id,
                    "title": updated_conversation.title,
                    "metadata": updated_conversation.metadata,
                    "last_activity": updated_conversation.last_activity,
                    "created_at": updated_conversation.created_at,
                    "updated_at": updated_conversation.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"更新对话时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新对话失败: {str(e)}",
                "error_code": "UPDATE_CONVERSATION_FAILED"
            }
    
    async def delete_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """删除对话
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 检查对话是否存在
            conversation = self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            # 删除对话
            success = self.conversation_repository.delete(conversation_id)
            if not success:
                return {
                    "success": False,
                    "error": "删除对话失败",
                    "error_code": "CONVERSATION_DELETE_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "message": "对话已成功删除",
                    "conversation_id": conversation_id
                }
            }
            
        except Exception as e:
            logger.error(f"删除对话时出错: {str(e)}")
            return {
                "success": False,
                "error": f"删除对话失败: {str(e)}",
                "error_code": "DELETE_CONVERSATION_FAILED"
            }
    
    async def list_user_conversations(self, 
                                     user_id: str, 
                                     skip: int = 0, 
                                     limit: int = 20) -> Dict[str, Any]:
        """获取用户的所有对话
        
        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            conversations = self.conversation_repository.get_by_user(user_id, skip=skip, limit=limit)
            
            # 格式化对话列表
            conversation_list = []
            for conv in conversations:
                conversation_list.append({
                    "id": conv.id,
                    "assistant_id": conv.assistant_id,
                    "user_id": conv.user_id,
                    "title": conv.title,
                    "metadata": conv.metadata,
                    "last_activity": conv.last_activity,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at
                })
            
            return {
                "success": True,
                "data": {
                    "conversations": conversation_list,
                    "total": len(conversation_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户对话列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取用户对话列表失败: {str(e)}",
                "error_code": "LIST_USER_CONVERSATIONS_FAILED"
            }
    
    async def list_assistant_conversations(self, 
                                          assistant_id: str, 
                                          user_id: Optional[str] = None,
                                          skip: int = 0, 
                                          limit: int = 20) -> Dict[str, Any]:
        """获取助手的所有对话，可按用户过滤
        
        Args:
            assistant_id: 助手ID
            user_id: 用户ID（可选，用于过滤）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            conversations = self.conversation_repository.get_by_assistant(
                assistant_id, user_id=user_id, skip=skip, limit=limit
            )
            
            # 格式化对话列表
            conversation_list = []
            for conv in conversations:
                conversation_list.append({
                    "id": conv.id,
                    "assistant_id": conv.assistant_id,
                    "user_id": conv.user_id,
                    "title": conv.title,
                    "metadata": conv.metadata,
                    "last_activity": conv.last_activity,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at
                })
            
            return {
                "success": True,
                "data": {
                    "conversations": conversation_list,
                    "total": len(conversation_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取助手对话列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取助手对话列表失败: {str(e)}",
                "error_code": "LIST_ASSISTANT_CONVERSATIONS_FAILED"
            }
    
    async def add_message(self, 
                         conversation_id: str, 
                         role: str, 
                         content: str,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """添加消息到对话
        
        Args:
            conversation_id: 对话ID
            role: 消息角色 (user, assistant, system)
            content: 消息内容
            metadata: 元数据
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证对话是否存在
            conversation = self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            # 根据角色创建消息
            if role == "system":
                message = self.message_repository.create_system_message(conversation_id, content)
            elif role == "user":
                message = self.message_repository.create_user_message(conversation_id, content, metadata)
            elif role == "assistant":
                message = self.message_repository.create_assistant_message(conversation_id, content, metadata)
            else:
                return {
                    "success": False,
                    "error": f"不支持的消息角色: {role}",
                    "error_code": "INVALID_MESSAGE_ROLE"
                }
            
            # 更新对话最后活动时间
            await self.update_conversation_activity(conversation_id)
            
            return {
                "success": True,
                "data": {
                    "id": message.id,
                    "conversation_id": message.conversation_id,
                    "role": message.role,
                    "content": message.content,
                    "metadata": message.metadata,
                    "created_at": message.created_at,
                    "updated_at": message.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"添加消息时出错: {str(e)}")
            return {
                "success": False,
                "error": f"添加消息失败: {str(e)}",
                "error_code": "ADD_MESSAGE_FAILED"
            }
    
    async def get_messages(self, 
                          conversation_id: str, 
                          skip: int = 0, 
                          limit: int = 100) -> Dict[str, Any]:
        """获取对话的所有消息
        
        Args:
            conversation_id: 对话ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证对话是否存在
            conversation = self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            # 获取消息
            messages = self.message_repository.get_by_conversation(conversation_id, skip=skip, limit=limit)
            
            # 格式化消息列表
            message_list = []
            for msg in messages:
                message_list.append({
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "created_at": msg.created_at,
                    "updated_at": msg.updated_at
                })
            
            return {
                "success": True,
                "data": {
                    "messages": message_list,
                    "total": len(message_list),
                    "skip": skip,
                    "limit": limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取消息列表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取消息列表失败: {str(e)}",
                "error_code": "GET_MESSAGES_FAILED"
            }
    
    async def get_conversation_history(self, 
                                      conversation_id: str, 
                                      limit: Optional[int] = None) -> Dict[str, Any]:
        """获取对话历史
        
        Args:
            conversation_id: 对话ID
            limit: 最大消息数量（None表示无限制）
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            # 验证对话是否存在
            conversation = self.conversation_repository.get_by_id(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                    "error_code": "CONVERSATION_NOT_FOUND"
                }
            
            # 获取消息
            if limit:
                messages = self.message_repository.get_by_conversation(conversation_id, limit=limit)
            else:
                messages = self.message_repository.get_by_conversation(conversation_id)
            
            # 格式化为对话历史
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return {
                "success": True,
                "data": {
                    "conversation_id": conversation_id,
                    "history": history,
                    "total_messages": len(history)
                }
            }
            
        except Exception as e:
            logger.error(f"获取对话历史时出错: {str(e)}")
            return {
                "success": False,
                "error": f"获取对话历史失败: {str(e)}",
                "error_code": "GET_CONVERSATION_HISTORY_FAILED"
            }
    
    async def update_conversation_activity(self, conversation_id: str) -> Dict[str, Any]:
        """更新对话最后活动时间
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        try:
            conversation = self.conversation_repository.update_last_activity(conversation_id)
            if not conversation:
                return {
                    "success": False,
                    "error": "更新对话活动时间失败",
                    "error_code": "UPDATE_ACTIVITY_FAILED"
                }
            
            return {
                "success": True,
                "data": {
                    "conversation_id": conversation_id,
                    "last_activity": conversation.last_activity
                }
            }
            
        except Exception as e:
            logger.error(f"更新对话活动时间时出错: {str(e)}")
            return {
                "success": False,
                "error": f"更新对话活动时间失败: {str(e)}",
                "error_code": "UPDATE_CONVERSATION_ACTIVITY_FAILED"
            } 